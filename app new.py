# rnn/app.py


import os
import uuid
import hmac
import hashlib
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import httpx
import uvicorn
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


from src.config import *
from src.utils.logger import get_logger
from agents.data_handler_multi_asset import get_multi_asset_data_for_rl
from agents.portfolio_environment import PortfolioEnv
from agents.custom_policies import CustomPortfolioPolicy
from src.utils.ccxt_utils import get_ccxt_exchange_live, execute_portfolio_rebalance, get_current_portfolio

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

logger = get_logger()

# --- Carregar Modelo e Wrappers na Inicialização ---
app_state = {}

def load_rl_agent_and_dependencies():
    """Carrega o agente PPO, o ambiente VecNormalize e a instância da exchange."""
    logger.info("Carregando dependências de produção na inicialização...")
    
    # Carregar Modelo e Normalizador
    model_path = os.path.join(MODEL_SAVE_DIR, f"{RL_AGENT_MODEL_NAME}.zip")
    stats_path = os.path.join(MODEL_SAVE_DIR, VEC_NORMALIZE_STATS_FILENAME)

    if not os.path.exists(model_path) or not os.path.exists(stats_path):
        logger.critical(f"Arquivo de modelo ou de estatísticas não encontrado. A API não pode operar.")
        return None, None
    
    asset_keys_list = list(MULTI_ASSET_SYMBOLS.keys())
    dummy_df = pd.DataFrame(columns=[f"{prefix}_{col}" for prefix in asset_keys_list for col in BASE_FEATURES_PER_ASSET_INPUT])
    dummy_env_creator = lambda: PortfolioEnv(df_multi_asset_features=dummy_df, asset_symbols_list=asset_keys_list, window_size=WINDOW_SIZE)
    vec_env = DummyVecEnv([dummy_env_creator])
    
    normalized_env = VecNormalize.load(stats_path, vec_env)
    normalized_env.training = False
    normalized_env.norm_reward = False
    logger.info("Ambiente VecNormalize carregado em modo de avaliação.")

    try:
        custom_objects = {"policy_class": CustomPortfolioPolicy}
        model = PPO.load(model_path, env=normalized_env, custom_objects=custom_objects)
        logger.info("Modelo PPO com política customizada carregado com sucesso.")
        return model, normalized_env
    except Exception as e:
        logger.critical(f"ERRO CRÍTICO ao carregar o modelo PPO: {e}", exc_info=True)
        return None, None



# --- Configuração Inicial e Variáveis de Ambiente (Secrets do Hugging Face) ---
AIBANK_API_KEY = os.environ.get("AIBANK_API_KEY") # Chave que o aibank usa para chamar esta API RNN
AIBANK_CALLBACK_URL = os.environ.get("AIBANK_CALLBACK_URL") # URL no aibank para onde esta API RNN enviará o resultado
CALLBACK_SHARED_SECRET = os.environ.get("CALLBACK_SHARED_SECRET") # Segredo para assinar/verificar o payload do callback

# Chaves para serviços externos 
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY")
EXCHANGE_API_SECRET = os.environ.get("EXCHANGE_API_SECRET")

if not AIBANK_API_KEY:
    logger.warning("AIBANK_API_KEY não configurada. A autenticação para /api/invest falhou.")
if not AIBANK_CALLBACK_URL:
    logger.warning("AIBANK_CALLBACK_URL não configurada. O callback para o aibank falhou.")
if not CALLBACK_SHARED_SECRET:
    logger.warning("CALLBACK_SHARED_SECRET não configurado. A segurança do callback está comprometida.")


app = FastAPI(title="ATCoin Neural Agents - Investment API")


@app.on_event("startup")
async def startup_event():
    app_state["rl_model"], app_state["normalized_env"] = load_rl_agent_and_dependencies()
    if app_state["rl_model"] is None:
        logger.error("A APLICAÇÃO ESTÁ INICIANDO SEM UM MODELO DE RL FUNCIONAL!")
    
    # Manter uma instância da exchange reutilizável (opcional, pode ser criada por requisição)
    app_state["exchange"] = await get_ccxt_exchange_live(logger)






# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # URL desenvolvimento local
        "http://aibank.app.br",   # URL de produção 
        "https://*.aibank.app.br", # subdomínios
        "https://*.hf.space"      # HF Space
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Em produção  MongoDB
transactions_db: Dict[str, Dict[str, Any]] = {}

# --- Modelos Pydantic ---
class InvestmentRequest(BaseModel):
    client_id: str
    amount: float = Field(..., gt=0) # Garante que o montante seja positivo
    aibank_transaction_token: str # Token único gerado pelo BIA para rastreamento

class InvestmentResponse(BaseModel):
    status: str
    message: str
    rnn_transaction_id: str # ID da transação this.API

class InvestmentResultPayload(BaseModel): # Payload para o callback para o BIA
    rnn_transaction_id: str
    aibank_transaction_token: str
    client_id: str
    initial_amount: float
    final_amount: float
    profit_loss: float
    status: str #  "completed", "failed"
    timestamp: datetime
    details: str = ""


# --- Dependência de Autenticação ---
async def verify_aibank_key(authorization: str = Header(None)):
    if not AIBANK_API_KEY: # Checagem se a chave do servidor está configurada
        logger.error("CRITICAL: AIBANK_API_KEY (server-side) não está configurada nos Secrets.")
        raise HTTPException(status_code=500, detail="Internal Server Configuration Error: Missing server API Key.")

    if authorization is None:
        logger.warning("Authorization header ausente na chamada do AIBank.")
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        logger.warning(f"Formato inválido do Authorization header: {authorization}")
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")

    token_from_aibank = parts[1]
    if not hmac.compare_digest(token_from_aibank, AIBANK_API_KEY):
        logger.warning(f"Chave de API inválida fornecida pelo AIBank. Token: {token_from_aibank[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API Key provided by AIBank.")
    logger.info("API Key do AIBank verificada com sucesso.")
    return True



# --- Lógica de Negócio de Produção (em Background) ---
async def execute_investment_strategy_live(
    rnn_tx_id: str,
    client_id: str,
    amount: float,
    aibank_tx_token: str
):
    logger.info(f"LIVE TASK [{rnn_tx_id}]: Iniciando ciclo de investimento para cliente {client_id}, valor {amount:.2f}.")
    transactions_db[rnn_tx_id] = {"status": "processing", "received_at": datetime.now(timezone.utc).isoformat()}
    
    model = app_state.get("rl_model")
    normalized_env = app_state.get("normalized_env")
    exchange = app_state.get("exchange")

    error_details = ""
    final_status = "pending"
    final_portfolio_value = amount # Valor inicial para fallback
    
    if not all([model, normalized_env, exchange]):
        error_details = "Dependências críticas (modelo, env ou exchange) não estão carregadas."
        final_status = "failed_config"
        logger.critical(f"LIVE TASK [{rnn_tx_id}]: {error_details}")
    else:
        try:
            # 1. Obter a Observação Mais Recente do Mercado
            transactions_db[rnn_tx_id]["status_details"] = "Fetching latest market data"
            logger.info(f"LIVE TASK [{rnn_tx_id}]: Buscando dados de mercado...")
            
            candles_needed = WINDOW_SIZE + 100 # Buscar um pouco mais para garantir que os indicadores sejam calculados
            live_market_data_df = await get_multi_asset_data_for_rl(
                asset_symbols_map=MULTI_ASSET_SYMBOLS,
                timeframe_yf=TIMEFRAME,
                days_to_fetch=int(candles_needed / 24) + 2, # Converter candles para dias e adicionar margem
                logger_instance=logger
            )

            if live_market_data_df is None or len(live_market_data_df) < WINDOW_SIZE:
                raise ValueError(f"Dados de mercado insuficientes. Necessário >= {WINDOW_SIZE}, obtido: {len(live_market_data_df) if live_market_data_df is not None else 0}")
            
            observation_df = live_market_data_df.tail(WINDOW_SIZE)
            observation_np = np.expand_dims(observation_df.values.astype(np.float32), axis=0)

            # 2. Obter a Ação do Agente RL
            transactions_db[rnn_tx_id]["status_details"] = "Getting RL agent action"
            logger.info(f"LIVE TASK [{rnn_tx_id}]: Obtendo alocação de portfólio da IA...")
            
            normalized_observation = normalized_env.normalize_obs(observation_np)
            action_logits, _ = model.predict(normalized_observation, deterministic=True)
            
            exp_logits = np.exp(action_logits[0] - np.max(action_logits[0]))
            target_weights = exp_logits / np.sum(exp_logits)
            
            target_weights_dict = {asset: weight for asset, weight in zip(MULTI_ASSET_SYMBOLS.keys(), target_weights)}
            logger.info(f"LIVE TASK [{rnn_tx_id}]: Alocação alvo da IA: {target_weights_dict}")
            transactions_db[rnn_tx_id]["target_weights"] = target_weights_dict

            # 3. Executar o Rebalanceamento do Portfólio na Exchange
            transactions_db[rnn_tx_id]["status_details"] = "Executing portfolio rebalance"
            logger.info(f"LIVE TASK [{rnn_tx_id}]: Executando ordens de rebalanceamento...")
            
            # ATENÇÃO: a função `execute_portfolio_rebalance` agora pega o valor do portfólio
            # diretamente da exchange, ignorando o 'amount' do AIBank por segurança.
            # O 'amount' do AIBank serviria como um limite ou referência.
            execution_results = await execute_portfolio_rebalance(exchange, target_weights_dict, logger)
            
            transactions_db[rnn_tx_id]["execution_details"] = execution_results
            if execution_results.get('status') != 'completed':
                error_details += json.dumps(execution_results.get('errors', []))
            logger.info(f"LIVE TASK [{rnn_tx_id}]: Rebalanceamento concluído.")
            
            # 4. Obter o valor final do portfólio
            final_portfolio_state = await get_current_portfolio(exchange, logger)
            if final_portfolio_state:
                final_portfolio_value = final_portfolio_state['total_value_usd']
                transactions_db[rnn_tx_id]["final_portfolio_state"] = final_portfolio_state
            
            final_status = "completed_with_errors" if error_details else "completed"
            
        except Exception as e:
            logger.error(f"LIVE TASK [{rnn_tx_id}]: ERRO durante o ciclo de investimento: {e}", exc_info=True)
            final_status = "failed_execution"
            error_details = str(e)
            # Tentar obter o valor do portfólio mesmo em caso de erro
            try:
                final_portfolio_state_on_error = await get_current_portfolio(exchange, logger)
                if final_portfolio_state_on_error:
                    final_portfolio_value = final_portfolio_state_on_error['total_value_usd']
            except:
                final_portfolio_value = amount # Fallback para o valor inicial

    # 5. Enviar o callback para o AIBank
    transactions_db[rnn_tx_id]["status"] = final_status
    transactions_db[rnn_tx_id]["final_value"] = final_portfolio_value


    

# --- Endpoints da API ---


@app.post("/api/invest",
          response_model=InvestmentResponse,
          dependencies=[Depends(verify_aibank_key)])
async def initiate_investment(
    request_data: InvestmentRequest,
    background_tasks: BackgroundTasks
):
    """
    Endpoint para o AIBank iniciar um ciclo de investimento.
    Responde rapidamente e executa a lógica pesada em background.
    """
    logger.info(f"Requisição de investimento recebida para client_id: {request_data.client_id}, "
                f"amount: {request_data.amount}, aibank_tx_token: {request_data.aibank_transaction_token}")

    rnn_tx_id = str(uuid.uuid4())

    # Armazena informações iniciais da transação DB real para ser mais robusto
    transactions_db[rnn_tx_id] = {
        "rnn_transaction_id": rnn_tx_id,
        "aibank_transaction_token": request_data.aibank_transaction_token,
        "client_id": request_data.client_id,
        "initial_amount": request_data.amount,
        "status": "pending_background_processing",
        "received_at": datetime.utcnow().isoformat(),
        "callback_status": "not_sent_yet"
    }

    # Adiciona a tarefa de longa duração ao background
    background_tasks.add_task(
        execute_investment_strategy_background,
        rnn_tx_id,
        request_data.client_id,
        request_data.amount,
        request_data.aibank_transaction_token
    )

    logger.info(f"Estratégia de investimento para rnn_tx_id: {rnn_tx_id} agendada para execução em background.")
    return InvestmentResponse(
        status="pending",
        message="Investment request received and is being processed in the background. Await callback for results.",
        rnn_transaction_id=rnn_tx_id
    )

@app.get("/api/transaction_status/{rnn_tx_id}", response_class=JSONResponse)
async def get_transaction_status(rnn_tx_id: str):
    """ Endpoint para verificar o status de uma transação (para debug/admin) """
    transaction = transactions_db.get(rnn_tx_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


# --- Dashboard (Existente, adaptado) ---
# Setup para arquivos estáticos e templates

try:
    app.mount("/static", StaticFiles(directory="rnn/static"), name="static")
    templates = Environment(loader=FileSystemLoader("rnn/templates"))
except RuntimeError as e:
    logger.warning(f"Não foi possível montar /static ou carregar templates: {e}. O dashboard pode não funcionar.")
    templates = None # Para evitar erros se o loader falhar

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not templates:
        return HTMLResponse("<html><body><h1>Dashboard indisponível</h1><p>Configuração de templates/estáticos falhou.</p></body></html>")
    
    agora = datetime.now()
    agentes_simulados = [
        # dados de agentes ...
    ]
    template = templates.get_template("index.html")
    # Adicionar transações recentes ao contexto do template
    recent_txs = list(transactions_db.values())[-5:] # Últimas 5 transações
    return HTMLResponse(template.render(request=request, agentes=agentes_simulados, transactions=recent_txs))

# --- Imports para Background Task ---
import asyncio
import random

if __name__ == "__main__":
    # Para rodar localmente para teste
    # Certifique-se que as variáveis de ambiente (AIBANK_API_KEY, CCXT_API_KEY, etc.) estão definidas
    uvicorn.run(app, host="0.0.0.0", port=8000)