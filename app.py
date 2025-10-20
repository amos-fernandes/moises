# rnn/app.py

"""
API principal para o sistema de trading algorítmico ATCoin Neural Agents.
Fornece endpoints para iniciar ciclos de investimento, verificar status e um dashboard.
A lógica principal é executada em background para não bloquear as requisições.
"""

# --- 1. IMPORTS E CONFIGURAÇÃO INICIAL ---
import sys
import os
import uuid
import hmac
import hashlib
import json
import asyncio
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

# Adiciona a raiz ao path para garantir que os imports de 'src' funcionem
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports de bibliotecas de terceiros
import uvicorn
import httpx
import pandas as pd
import numpy as np
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

# Imports dos módulos locais (corrigidos e organizados)
from src.utils.logger import get_logger

# RNNModelPredictor imports TensorFlow and other heavy libs. Allow
# skipping that import at process start (useful for lightweight tests)
# by setting the environment variable SKIP_RNN_IMPORT=1.
RNNModelPredictor = None
if not os.environ.get("SKIP_RNN_IMPORT"):
    try:
        from src.model.rnn_predictor import RNNModelPredictor
    except Exception as _e:
        # Avoid failing import-time; log later after logger is available
        print(f"Warning: RNNModelPredictor import skipped due to: {_e}")

### <<< CORREÇÃO CRÍTICA NOS IMPORTS >>> ###
# Cada função é importada de seu respectivo módulo.
# Allow skipping heavy external imports (yfinance, ccxt, market utils) during lightweight tests
SKIP_HEAVY_IMPORTS = bool(os.environ.get('SKIP_HEAVY_IMPORTS'))

if not SKIP_HEAVY_IMPORTS:
    import yfinance as yf
    from src.utils.ccxt_utils import get_ccxt_exchange, fetch_crypto_data
    from src.utils.market_data_utils import fetch_btc_dominance, get_market_sentiment
    from src.utils.technical_analysis_utils import calculate_rsi
else:
    # Lightweight stubs used in test mode to avoid importing heavy libraries
    yf = None

    async def get_ccxt_exchange(logger_instance=None):
        return None

    async def fetch_crypto_data(exchange, crypto_pairs, logger_instance=None):
        # return empty data structure matching the expected shape
        return {}, [], []

    async def fetch_btc_dominance():
        return None

    async def get_market_sentiment():
        return {}

    def calculate_rsi(series, period=14):
        return None
### <<< FIM DA CORREÇÃO >>> ###

from contextlib import asynccontextmanager
# Inicializa o logger
logger = get_logger()

# --- 2. CONFIGURAÇÃO DE AMBIENTE E SECRETS ---
AIBANK_API_KEY = os.environ.get("AIBANK_API_KEY")
AIBANK_CALLBACK_URL = os.environ.get("AIBANK_CALLBACK_URL")
CALLBACK_SHARED_SECRET = os.environ.get("CALLBACK_SHARED_SECRET")

# --- 3. EVENTOS DE LIFESPAN (Substitui o startup_event) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que roda ANTES da aplicação iniciar
    logger.info("Iniciando ciclo de vida da aplicação...")
    try:
        MODEL_DIR = "src/model/"
        MODEL_FILENAME = "model.h5"
        PV_SCALER_FILENAME = "price_volume_atr_norm_scaler.joblib"
        IND_SCALER_FILENAME = "other_indicators_scaler.joblib"

        predictor = RNNModelPredictor(
            model_dir=MODEL_DIR,
            model_filename=MODEL_FILENAME,
            pv_scaler_filename=PV_SCALER_FILENAME,
            ind_scaler_filename=IND_SCALER_FILENAME,
            logger_instance=logger
        )
        await predictor.load_model()
        app.state.rnn_predictor = predictor # 'app' aqui é o objeto FastAPI passado como argumento
        logger.info("✅ Modelo RNN e scalers carregados com sucesso no estado da aplicação.")
    except Exception as e:
        logger.error(f"❌ FALHA CRÍTICA ao carregar modelo RNN na inicialização: {e}", exc_info=True)
        app.state.rnn_predictor = None
    
    yield
    
    # Código que roda DEPOIS da aplicação finalizar
    logger.info("Finalizando ciclo de vida da aplicação.")


# --- 4. INICIALIZAÇÃO DO APP FASTAPI ---
fastapi_app = FastAPI(
    title="ATCoin Neural Agents - Investment API",
    lifespan=lifespan # Usa o novo gerenciador de ciclo de vida
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta arquivos estáticos e templates CORRETAMENTE em 'fastapi_app'
try:
    fastapi_app.mount("/static", StaticFiles(directory="./static"), name="static")
    env = Environment(loader=FileSystemLoader("./templates"))
    template = env.get_template("dashboard.html")
    logger.info("✅ Templates e arquivos estáticos carregados.")
except Exception as e:
    logger.error(f"❌ Falha ao carregar templates/estáticos: {e}")
    template = None


# Simulação de Banco de Dados de Transações
transactions_db: Dict[str, Dict[str, Any]] = {}

# --- 4. MODELOS PYDANTIC ---
class InvestmentRequest(BaseModel):
    client_id: str
    amount: float
    aibank_transaction_token: str

class InvestmentResponse(BaseModel):
    status: str
    message: str
    rnn_transaction_id: str

class InvestmentResultPayload(BaseModel):
    rnn_transaction_id: str
    aibank_transaction_token: str
    client_id: str
    initial_amount: float
    final_amount: float
    profit_loss: float
    status: str
    timestamp: datetime
    details: str = ""

# --- 5. LÓGICA DE NEGÓCIO EM BACKGROUND (REATORADA) ---

### <<< ESTRUTURA REATORADA: Funções auxiliares para clareza >>> ###

async def _collect_market_data(rnn_tx_id: str, exchange: Optional[Any]) -> Dict[str, Any]:
    """Coleta todos os dados de mercado necessários de várias fontes."""
    logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando coleta de dados de mercado.")
    
    # Única inicialização da estrutura de dados
    market_data = {"crypto": {}, "stocks": {}, "other": {}}
    
    # 1. Dados de Cripto (via CCXT)
    if exchange:
        crypto_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT"]
        market_data["crypto"], _, _ = await fetch_crypto_data(exchange, crypto_pairs, logger)
    else:
        logger.warning(f"BG TASK [{rnn_tx_id}]: Exchange não disponível. Pulando coleta de dados cripto.")

    # 2. Dados de Ações (via yfinance)
    try:
        stock_symbols = ["AAPL", "TSLA", "NVDA", "MSFT"]
        for symbol in stock_symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo", interval="1d")
            if not hist.empty:
                market_data["stocks"][symbol] = {"history": hist.to_dict('records'), "info": ticker.info}
    except Exception as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Falha ao buscar dados de ações via yfinance: {e}")

    # 3. Outros Dados (APIs externas)
    market_data["other"]["btc_dominance"] = await fetch_btc_dominance()
    market_data["other"]["market_risk_sentiment"] = await get_market_sentiment()
    
    logger.info(f"BG TASK [{rnn_tx_id}]: Coleta de dados de mercado concluída.")
    return market_data

async def _run_rnn_analysis(rnn_tx_id: str, market_data: Dict, amount: float) -> List[Dict]:
    """Executa a análise da RNN e gera decisões de investimento."""
    logger.info(f"BG TASK [{rnn_tx_id}]: Executando análise da RNN.")
    
    predictor = getattr(fastapi_app.state, 'rnn_predictor', None)
    if not predictor or not predictor.model:
        logger.error(f"BG TASK [{rnn_tx_id}]: Modelo RNN não carregado. Abortando análise.")
        return []

    # Lógica de decisão e gerenciamento de risco consolidada
    # (Pode ser ajustada conforme necessário)
    investment_decisions = []
    # ... (Sua lógica de gerenciamento de risco e loop sobre os ativos para predição) ...
    # Exemplo simplificado:
    crypto_data = market_data.get("crypto", {})
    for asset, data in crypto_data.items():
        if "error" not in data:
             # signal, confidence = await predictor.predict_for_asset(...)
             # if signal == 1:
             #     decisions.append({...})
             pass # Implementar lógica de predição aqui
    
    logger.info(f"BG TASK [{rnn_tx_id}]: Análise da RNN concluída. {len(investment_decisions)} decisões geradas.")
    return investment_decisions

async def _execute_trades(rnn_tx_id: str, decisions: List, exchange: Any) -> tuple[list, float, float]:
    """Executa as ordens de compra/venda na exchange."""
    if not exchange:
        logger.error(f"BG TASK [{rnn_tx_id}]: Não é possível executar trades, exchange não disponível.")
        return [], 0.0, 0.0

    logger.info(f"BG TASK [{rnn_tx_id}]: Executando {len(decisions)} trades.")
    executed_trades = []
    portfolio_cost = 0.0
    # ... (Sua lógica para iterar sobre as 'decisions' e criar ordens com `exchange.create_market_buy_order`) ...
    
    cash_spent = portfolio_cost
    return executed_trades, portfolio_cost, cash_spent

async def _simulate_eod_valuation(portfolio_cost: float, executed_trades: List) -> float:
    """Simula o valor do portfólio no final do dia."""
    if portfolio_cost == 0:
        return 0.0
        
    # Simulação de retorno diário
    simulated_return = random.uniform(-0.03, 0.05) 
    final_portfolio_value = portfolio_cost * (1 + simulated_return)
    return final_portfolio_value

async def _send_callback_to_aibank(payload_data: InvestmentResultPayload):
    """Envia o resultado final para o AIBank com assinatura HMAC."""
    if not AIBANK_CALLBACK_URL or not CALLBACK_SHARED_SECRET:
        logger.error("Configuração de callback ausente. Não é possível notificar o AIBank.")
        return

    payload_json_str = payload_data.model_dump_json()
    signature = hmac.new(CALLBACK_SHARED_SECRET.encode('utf-8'), payload_json_str.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-RNN-Signature': signature}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(AIBANK_CALLBACK_URL, content=payload_json_str, headers=headers)
            response.raise_for_status()
            logger.info(f"Callback para AIBank enviado com sucesso. Resposta: {response.status_code}")
    except Exception as e:
        logger.error(f"Falha CRÍTICA ao enviar callback para AIBank: {e}")


async def execute_investment_strategy_background(rnn_tx_id: str, client_id: str, amount: float, aibank_tx_token: str):
    """
    Função orquestradora que executa o ciclo de investimento em background.
    """
    logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando orquestração do ciclo de investimento.")
    transactions_db[rnn_tx_id]["status"] = "processing"

    exchange = None
    final_status = "completed"
    error_details = ""

    try:
        # Fast local test mode: immediately send callback without running the full pipeline.
        if os.environ.get('FAST_TEST_CALLBACK') == '1':
            logger.info(f"BG TASK [{rnn_tx_id}]: FAST_TEST_CALLBACK active - sending immediate simulated callback.")
            callback_payload = InvestmentResultPayload(
                rnn_transaction_id=rnn_tx_id,
                aibank_transaction_token=aibank_tx_token,
                client_id=client_id,
                initial_amount=amount,
                final_amount=round(amount, 2),
                profit_loss=0.0,
                status='completed',
                timestamp=datetime.utcnow(),
                details='fast-test-simulated'
            )
            await _send_callback_to_aibank(callback_payload)
            transactions_db[rnn_tx_id]["status"] = 'completed'
            transactions_db[rnn_tx_id]["callback_status"] = 'sent'
            return
        # Etapa 1: Conectar à Exchange
        exchange = await get_ccxt_exchange(logger_instance=logger)
        if not exchange:
            raise ConnectionError("Falha ao inicializar a conexão com a exchange.")

        # Etapa 2: Coletar Dados
        market_data = await _collect_market_data(rnn_tx_id, exchange)
        transactions_db[rnn_tx_id]["market_data_collected"] = market_data

        # Etapa 3: Análise da RNN
        decisions = await _run_rnn_analysis(rnn_tx_id, market_data, amount)
        transactions_db[rnn_tx_id]["rnn_decisions"] = decisions

        # Etapa 4: Executar Trades
        executed_trades, portfolio_cost, cash_spent = await _execute_trades(rnn_tx_id, decisions, exchange)
        transactions_db[rnn_tx_id]["executed_trades"] = executed_trades
        cash_remaining = amount - cash_spent

        # Etapa 5: Simular Valorização EOD (End of Day)
        final_portfolio_value = await _simulate_eod_valuation(portfolio_cost, executed_trades)

        # Etapa 6: Calcular Resultado Final
        final_amount = cash_remaining + final_portfolio_value

    except Exception as e:
        logger.critical(f"BG TASK [{rnn_tx_id}]: Erro crítico no ciclo de investimento: {e}", exc_info=True)
        final_status = "failed"
        error_details = str(e)
        final_amount = amount # Em caso de falha, retorna o valor inicial

    finally:
        # Etapa 7: Limpeza (sempre executa)
        if exchange:
            logger.info(f"BG TASK [{rnn_tx_id}]: Fechando conexão com a exchange.")
            await exchange.close()

    # Etapa 8: Enviar Callback para AIBank
    callback_payload = InvestmentResultPayload(
        rnn_transaction_id=rnn_tx_id,
        aibank_transaction_token=aibank_tx_token,
        client_id=client_id,
        initial_amount=amount,
        final_amount=round(final_amount, 2),
        profit_loss=round(final_amount - amount, 2),
        status=final_status,
        timestamp=datetime.utcnow(),
        details=error_details or "Investment cycle processed."
    )
    await _send_callback_to_aibank(callback_payload)
    transactions_db[rnn_tx_id]["status"] = final_status
    transactions_db[rnn_tx_id]["callback_status"] = "sent"

# --- 6. EVENTOS DE STARTUP E DEPENDÊNCIAS ---
# Removed duplicate startup_event: model is loaded in the lifespan manager above

async def verify_aibank_key(authorization: str = Header(None)):
    """Dependência para verificar a chave de API do AIBank."""
    # ... (sua lógica de verificação de chave, que parece correta) ...
    return True




# --- 7. DEPENDÊNCIAS E ENDPOINTS DA API ---
async def verify_aibank_key(authorization: str = Header(None)):
    if not AIBANK_API_KEY:
        logger.warning("AIBANK_API_KEY não configurada. Permitindo acesso.")
        return True
    if authorization != f"Bearer {AIBANK_API_KEY}":
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True

@fastapi_app.post("/api/invest", response_model=InvestmentResponse, dependencies=[Depends(verify_aibank_key)])
async def initiate_investment(request_data: InvestmentRequest, background_tasks: BackgroundTasks):
    logger.info(f"Requisição de investimento recebida para cliente: {request_data.client_id}")
    rnn_tx_id = str(uuid.uuid4())
    transactions_db[rnn_tx_id] = {"status": "pending", "received_at": datetime.utcnow().isoformat()}
    background_tasks.add_task(
        execute_investment_strategy_background,
        rnn_tx_id,
        request_data.client_id,
        request_data.amount,
        request_data.aibank_transaction_token
    )
    return InvestmentResponse(status="pending", message="Investment request received and is being processed.", rnn_transaction_id=rnn_tx_id)


# @fastapi_app.post("/api/invest", dependencies=[Depends(verify_aibank_key)])
# # Remova 'response_model' por enquanto para facilitar o debug, ou aponte para o modelo de resposta correto
# async def initiate_investment_sync(request_data: InvestmentRequest): # Removido: background_tasks
    
#     logger.info(f"Requisição de investimento SÍNCRONA recebida para cliente: {request_data.client_id}")
    
#     # --- LÓGICA ANTIGA REMOVIDA ---
#     # rnn_tx_id = str(uuid.uuid4())
#     # transactions_db[rnn_tx_id] = {"status": "pending", ...}
#     # background_tasks.add_task(...)
#     # return InvestmentResponse(status="pending", ...)
    
#     # --- NOVA LÓGICA SÍNCRONA ---
#     try:
#         # Chame a sua função de cálculo DIRETAMENTE
#         # A função de background provavelmente não retorna nada, então teremos que pegar o resultado do DB.
#         # Vamos assumir que a função de background precisa de um ID para salvar o resultado.
        
#         rnn_tx_id = str(uuid.uuid4()) # Ainda precisamos de um ID para a função de estratégia

#         # Chame a função e ESPERE ela terminar.
#         # O 'await' é crucial se a função for 'async'. Se não for, remova-o.
#         await execute_investment_strategy_background(
#             rnn_tx_id,
#             request_data.client_id,
#             request_data.amount,
#             request_data.aibank_transaction_token
#         )

#         # Agora que a função terminou, o resultado deve estar no seu banco de dados em memória.
#         # Vamos buscá-lo.
#         final_result = transactions_db.get(rnn_tx_id)

#         if not final_result:
#             raise HTTPException(status_code=500, detail="Strategy execution finished but result not found in DB.")

#         # Verifique se o resultado contém a alocação
#         if final_result.get("status") == "complete" and "recommended_allocation" in final_result:
#             # Retorne o resultado completo, que o robô vai conseguir processar
#             logger.info(f"Estratégia concluída. Retornando alocação: {final_result}")
#             return final_result
#         else:
#             # Se a estratégia falhou, retorne o erro.
#             logger.error(f"Estratégia falhou. Detalhes: {final_result}")
#             raise HTTPException(status_code=500, detail=final_result.get("error", "Unknown error during strategy execution."))

#     except Exception as e:
#         logger.exception(f"Erro crítico durante a execução da estratégia síncrona: {e}")
#         raise HTTPException(status_code=500, detail=str(e))




@fastapi_app.get("/api/transaction_status/{rnn_tx_id}", response_class=JSONResponse)
async def get_transaction_status(rnn_tx_id: str):
    transaction = transactions_db.get(rnn_tx_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@fastapi_app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not template:
        return HTMLResponse("<h1>Dashboard Indisponível - Template não encontrado</h1>", status_code=500)
    return HTMLResponse(template.render(request=request))

@fastapi_app.get("/health")
async def health_check():
    # CORRIGIDO: Usa 'fastapi_app.state'
    model_loaded = fastapi_app.state.rnn_predictor is not None
    return {"status": "healthy", "model_loaded": model_loaded}




# Adicione este endpoint no seu app.py
@fastapi_app.get("/api/transactions/recent", response_class=JSONResponse)
async def get_recent_transactions():
    """Retorna as últimas transações para o dashboard."""
    # Pega os últimos 10 itens do dicionário (de forma segura)
    recent_keys = list(transactions_db.keys())[-10:]
    recent_transactions = [transactions_db[key] for key in recent_keys]
    return {"transactions": recent_transactions}

# # --- 8. MONTAGEM DA APLICAÇÃO FINAL (GRADIO + FASTAPI) ---
# with gr.Blocks(title="ATCoin Dashboard") as gradio_interface:
#     gr.Markdown("# ATCoin Neural Agents - Dashboard")
#     gr.Markdown("Acompanhe o status e a saúde do serviço de investimento.")
    
#     with gr.Row():
#         health_btn = gr.Button("Verificar Saúde do Serviço")
#         health_output = gr.JSON()
    
#     health_btn.click(fn=health_check, inputs=None, outputs=health_output)

# # A linha mais importante: Cria a aplicação final combinada.
# # Esta variável 'app' é a que o Hugging Face vai servir.
# app = gr.mount_gradio_app(fastapi_app, gradio_interface, path="/gradio")

# # O path="/gradio" significa que:
# # - Sua API FastAPI estará na raiz: /api/invest, /health, etc.
# # - Sua UI Gradio estará em /gradio
# # Se quiser a UI na raiz, mude para path="/" e ajuste a rota do seu dashboard FastAPI para algo como /dashboard_html.



if __name__ == "__main__": # Para teste local
    # logger = DummyLogger() # se não tiver get_logger()
    # Configuração das variáveis de ambiente para teste local
    os.environ["AIBANK_API_KEY"] = "test_aibank_key_from_rnn_server"
    os.environ["AIBANK_CALLBACK_URL"] = "http://localhost:8001/api/rnn_investment_result_callback" # URL do aibank simulado
    os.environ["CALLBACK_SHARED_SECRET"] = "super_secret_for_callback_signing"
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)