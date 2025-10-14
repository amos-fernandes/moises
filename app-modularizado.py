# rnn/app.py

import os
import uuid
import time
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from rnn.app.ccxt_utils import get_ccxt_exchange, fetch_crypto_data

import httpx # Para fazer chamadas HTTP assíncronas (para o callback)
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from rnn.app.utils.logger import get_logger 



logger = get_logger()

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

# --- Simulação de Banco de Dados de Transações DEV ---
# Em produção  MongoDB
transactions_db: Dict[str, Dict[str, Any]] = {}

# --- Modelos Pydantic ---
class InvestmentRequest(BaseModel):
    client_id: str
    amount: float = Field(..., gt=0) # Garante que o montante seja positivo
    aibank_transaction_token: str # Token único gerado pelo aibank para rastreamento

class InvestmentResponse(BaseModel):
    status: str
    message: str
    rnn_transaction_id: str # ID da transação this.API

class InvestmentResultPayload(BaseModel): # Payload para o callback para o aibank
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


# --- Lógica de Negócio Principal (Simulada e em Background) ---


async def execute_investment_strategy_background(
    rnn_tx_id: str,
    client_id: str,
    amount: float,
    aibank_tx_token: str
):
    logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando estratégia de investimento para cliente {client_id}, valor {amount}.")
    transactions_db[rnn_tx_id]["status"] = "processing"
    transactions_db[rnn_tx_id]["status_details"] = "Initializing investment cycle"
    
    final_status = "completed"
    error_details = "" # Acumula mensagens de erro de várias etapas
    calculated_final_amount = amount 

    # Inicializa a exchange ccxt usando o utilitário
    # O logger do app.py é passado para ccxt_utils para que os logs apareçam no mesmo stream
    exchange = await get_ccxt_exchange(logger_instance=logger) # MODIFICADO

    if not exchange:
        # get_ccxt_exchange já loga o erro. Se a exchange é crucial, podemos falhar aqui.
        logger.warning(f"BG TASK [{rnn_tx_id}]: Falha ao inicializar a exchange. A estratégia pode não funcionar como esperado para cripto.")
        # Se as chaves CCXT foram fornecidas no ambiente mas a exchange falhou, considere isso um erro de config.
        if os.environ.get("CCXT_API_KEY") and os.environ.get("CCXT_API_SECRET"):
            error_details += "Failed to initialize CCXT exchange despite API keys being present; "
            final_status = "failed_config" 
            # (PULAR PARA CALLBACK - veja a seção de tratamento de erro crítico abaixo)
    
    # =========================================================================
    # 1. COLETAR DADOS DE MERCADO
    # =========================================================================
    logger.info(f"BG TASK [{rnn_tx_id}]: Coletando dados de mercado...")
    transactions_db[rnn_tx_id]["status_details"] = "Fetching market data"
    market_data_results = {"crypto": {}, "stocks": {}, "other": {}}
    critical_data_fetch_failed = False # Flag para falha crítica na coleta de dados

    # --- Coleta de dados de Cripto via ccxt_utils ---
    if exchange:
        crypto_pairs_to_fetch = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] # Mantenha configurável
        
        crypto_data, crypto_fetch_ok, crypto_err_msg = await fetch_crypto_data(
            exchange, 
            crypto_pairs_to_fetch, 
            logger_instance=logger
        )
        market_data_results["crypto"] = crypto_data
        if not crypto_fetch_ok:
            error_details += f"Crypto data fetch issues: {crypto_err_msg}; "
            # Decida se a falha na coleta de cripto é crítica
            # Se for, defina critical_data_fetch_failed = True
            if os.environ.get("CCXT_API_KEY"): # Se esperávamos dados de cripto
                critical_data_fetch_failed = True 
                logger.error(f"BG TASK [{rnn_tx_id}]: Falha crítica na coleta de dados de cripto.")
    else:
        logger.info(f"BG TASK [{rnn_tx_id}]: Instância da exchange ccxt não disponível. Pulando coleta de dados de cripto.")
        if os.environ.get("CCXT_API_KEY"): # Se esperávamos dados de cripto mas a exchange não inicializou
            error_details += "CCXT exchange not initialized, crypto data skipped; "
            critical_data_fetch_failed = True


    # --- Coleta de dados para outros tipos de ativos (ex: Ações com yfinance) ---
    # (Sua lógica yfinance aqui, se aplicável, similarmente atualizando market_data_results["stocks"])
    # try:
    #     import yfinance as yf # Mova para o topo do app.py se for usar
    #     # ... lógica yfinance ...
    # except Exception as e_yf:
    #     logger.warning(f"BG TASK [{rnn_tx_id}]: Falha ao buscar dados de ações com yfinance: {e_yf}")
    #     error_details += f"YFinance data fetch failed: {str(e_yf)}; "
    #     # Decida se isso é crítico: critical_data_fetch_failed = True

    market_data_results["other"]['simulated_index_level'] = random.uniform(10000, 15000) # Mantém simulação
    
    transactions_db[rnn_tx_id]["market_data_collected"] = market_data_results
    
    # --- PONTO DE CHECAGEM PARA FALHA CRÍTICA NA COLETA DE DADOS ---
    if critical_data_fetch_failed:
        final_status = "failed_market_data"
        logger.error(f"BG TASK [{rnn_tx_id}]: Coleta de dados de mercado falhou criticamente. {error_details}")
        # Pular para a seção de callback
        # (A lógica de envio do callback precisa ser alcançada)
    else:
        logger.info(f"BG TASK [{rnn_tx_id}]: Coleta de dados de mercado concluída.")
        transactions_db[rnn_tx_id]["status_details"] = "Processing RNN analysis"


    # =========================================================================
    # 2. ANÁLISE PELA RNN E TOMADA DE DECISÃO (Só executa se a coleta de dados não falhou criticamente)
    # =========================================================================
    investment_decisions: List[Dict[str, Any]] = [] 
    total_usd_allocated_by_rnn = 0.0

    if final_status == "completed": # Prossiga apenas se não houve erro crítico anterior
        logger.info(f"BG TASK [{rnn_tx_id}]: Executando análise RNN...")
        transactions_db[rnn_tx_id]["status_details"] = "Running RNN model"
        rnn_analysis_success = True
        try:
            # Placeholder para a LÓGICA REAL DA RNN (RNN_LOGIC_PLACEHOLDER)
            # Esta seção precisa ser preenchida com:
            # 1. Carregamento do seu modelo RNN treinado (ex: TensorFlow, PyTorch, scikit-learn).
            #    O modelo pode ser carregado uma vez quando a API inicia, ou sob demanda.
            #    Se for grande, carregue na inicialização da API.
            #    Ex: from rnn.models.my_rnn_predictor import MyRNNModel
            #        if 'rnn_model_instance' not in app.state: # Carregar uma vez
            #            app.state.rnn_model_instance = MyRNNModel(path_to_model_weights)
            #        predictor = app.state.rnn_model_instance
            #
            # 2. Pré-processamento dos `market_data_results` para o formato que sua RNN espera.
            #    Ex: features = preprocess_market_data_for_rnn(market_data_results)
            #
            # 3. Inferência/Predição com a RNN.
            #    Ex: raw_rnn_output = await predictor.predict_async(features, client_profile_if_any)
            #
            # 4. Pós-processamento do output da RNN para gerar `investment_decisions` no formato:
            #    [{ "asset_id": "BTC/USDT", "type": "CRYPTO", "action": "BUY", 
            #       "target_usd_amount": 5000.00, "confidence_score": 0.85, 
            #       "stop_loss_price": 60000, "take_profit_price": 75000, 
            #       "reasoning": "RNN output details..." }, ...]
            
            # Simulação atual:
            await asyncio.sleep(random.uniform(5, 10)) # Simula processamento da RNN
            if market_data_results.get("crypto"):
                if random.random() > 0.2: # 80% chance
                    num_crypto_to_invest = min(random.randint(1, 2), len(market_data_results["crypto"]))
                    available_crypto_keys = [k for k,v in market_data_results["crypto"].items() if not v.get("error")]
                    if available_crypto_keys:
                        chosen_pairs_keys = random.sample(available_crypto_keys, k=min(num_crypto_to_invest, len(available_crypto_keys)))
                        
                        base_allocation_per_asset = amount / len(chosen_pairs_keys) if chosen_pairs_keys else 0

                        for crypto_key in chosen_pairs_keys:
                            asset_symbol = crypto_key.replace("_", "/")
                            # Alocação mais realista: não necessariamente usar todo o 'amount'
                            # E a RNN pode dar pesos diferentes
                            asset_specific_allocation_factor = random.uniform(0.3, 0.7) / len(chosen_pairs_keys)
                            allocated_amount = amount * asset_specific_allocation_factor
                            
                            # Evitar alocar mais do que o 'amount' total disponível
                            if total_usd_allocated_by_rnn + allocated_amount > amount * 0.95: # Deixa uma margem
                                allocated_amount = max(0, (amount * 0.95) - total_usd_allocated_by_rnn)
                            
                            if allocated_amount > 10: # Investimento mínimo de $10 (exemplo)
                                investment_decisions.append({
                                    "asset_id": asset_symbol, "type": "CRYPTO", "action": "BUY",
                                    "target_usd_amount": round(allocated_amount, 2),
                                    "reasoning": f"Simulated RNN signal for {asset_symbol}"
                                })
                                total_usd_allocated_by_rnn += round(allocated_amount, 2)
            
            if not investment_decisions:
                logger.info(f"BG TASK [{rnn_tx_id}]: RNN não gerou decisões de COMPRA.")
            else:
                logger.info(f"BG TASK [{rnn_tx_id}]: RNN gerou {len(investment_decisions)} decisões de compra: {investment_decisions}")

        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro durante análise RNN: {str(e)}", exc_info=True)
            rnn_analysis_success = False
            error_details += f"RNN analysis failed: {str(e)}; "
        
        if not rnn_analysis_success:
            final_status = "failed_rnn_analysis"
        
        transactions_db[rnn_tx_id]["rnn_decisions"] = investment_decisions
    
    # Atualiza o total_usd_allocated_by_rnn com base nas decisões finais
    total_usd_allocated_by_rnn = sum(d['target_usd_amount'] for d in investment_decisions if d['action'] == 'BUY')
    transactions_db[rnn_tx_id]["status_details"] = "Preparing to execute orders"


    # =========================================================================
    # 3. EXECUÇÃO DE ORDENS (Só executa se a RNN não falhou e gerou ordens)
    # =========================================================================
    executed_trades_info: List[Dict[str, Any]] = []
    current_portfolio_value = 0.0 # Valor dos ativos comprados, baseado no custo
    cash_remaining_after_execution = amount # Começa com todo o montante
    
    if final_status == "completed" and investment_decisions and exchange:
        logger.info(f"BG TASK [{rnn_tx_id}]: Executando {len(investment_decisions)} ordens...")
        transactions_db[rnn_tx_id]["status_details"] = "Executing investment orders"
        order_execution_overall_success = True

        # Placeholder para LÓGICA REAL DE EXECUÇÃO DE ORDENS (CREATE_ORDER_PLACEHOLDER)
        # Esta seção precisa ser preenchida com:
        # 1. Iterar sobre `investment_decisions`.
        # 2. Para cada decisão de "BUY":
        #    a. Determinar o símbolo correto na exchange (ex: "BTC/USDT").
        #    b. Obter o preço atual (ticker) para calcular a quantidade de ativo a comprar.
        #       `amount_of_asset = target_usd_amount / current_price_of_asset`
        #    c. Considerar saldo disponível na exchange (se estiver gerenciando isso).
        #    d. Criar a ordem via `await exchange.create_market_buy_order(symbol, amount_of_asset)`
        #       ou `create_limit_buy_order(symbol, amount_of_asset, limit_price)`.
        #       Para ordens limite, a RNN precisaria fornecer o `limit_price`.
        #    e. Tratar respostas da exchange (sucesso, falha, ID da ordem).
        #       `ccxt.InsufficientFunds`, `ccxt.InvalidOrder`, etc.
        #    f. Armazenar detalhes da ordem em `executed_trades_info`:
        #       { "asset_id": ..., "order_id_exchange": ..., "type": "market/limit", "side": "buy",
        #         "requested_usd_amount": ..., "asset_quantity_ordered": ..., 
        #         "status_from_exchange": ..., "filled_quantity": ..., "average_fill_price": ...,
        #         "cost_in_usd": ..., "fees_paid": ..., "timestamp": ... }
        #    g. Atualizar `current_portfolio_value` com o `cost_in_usd` da ordem preenchida.
        #    h. Deduzir `cost_in_usd` de `cash_remaining_after_execution`.
        # 3. Para decisões de "SELL" (se sua RNN gerar):
        #    a. Verificar se você possui o ativo (requer gerenciamento de portfólio).
        #    b. Criar ordem de venda.
        #    c. Atualizar `current_portfolio_value` e `cash_remaining_after_execution`.

        # Simulação atual:
        for decision in investment_decisions:
            if decision.get("action") == "BUY" and decision.get("type") == "CRYPTO":
                asset_symbol = decision["asset_id"]
                usd_to_spend = decision["target_usd_amount"]
                
                # Simular pequena chance de falha na ordem
                if random.random() < 0.05:
                    logger.warning(f"BG TASK [{rnn_tx_id}]: Falha simulada ao executar ordem para {asset_symbol}.")
                    executed_trades_info.append({
                        "asset_id": asset_symbol, "status": "failed_simulated", 
                        "requested_usd_amount": usd_to_spend, "error": "Simulated exchange rejection"
                    })
                    order_execution_overall_success = False # Marca que pelo menos uma falhou
                    continue # Pula para a próxima decisão

                # Simular slippage e custo
                simulated_cost = usd_to_spend * random.uniform(0.995, 1.005) # +/- 0.5% slippage
                
                # Garantir que não estamos gastando mais do que o caixa restante
                if simulated_cost > cash_remaining_after_execution:
                    simulated_cost = cash_remaining_after_execution # Gasta apenas o que tem
                    if simulated_cost < 1: # Se não há quase nada, não faz a ordem
                        logger.info(f"BG TASK [{rnn_tx_id}]: Saldo insuficiente ({cash_remaining_after_execution:.2f}) para ordem de {asset_symbol}, pulando.")
                        continue


                if simulated_cost > 0:
                    current_portfolio_value += simulated_cost
                    cash_remaining_after_execution -= simulated_cost
                    executed_trades_info.append({
                        "asset_id": asset_symbol, "order_id_exchange": f"sim_ord_{uuid.uuid4()}",
                        "type": "market", "side": "buy",
                        "requested_usd_amount": usd_to_spend,
                        "status_from_exchange": "filled", "cost_in_usd": round(simulated_cost, 2),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    logger.info(f"BG TASK [{rnn_tx_id}]: Ordem simulada para {asset_symbol} (custo: {simulated_cost:.2f} USD) preenchida.")
        
        await asyncio.sleep(random.uniform(1, 2) * len(investment_decisions) if investment_decisions else 1)

        if not order_execution_overall_success:
            error_details += "One or more orders failed during execution; "
            # Decida se isso torna o status final 'failed_order_execution' ou se 'completed_with_partial_failure'
            # final_status = "completed_with_partial_failure" # Exemplo de um novo status
    
    elif not exchange and investment_decisions:
        logger.warning(f"BG TASK [{rnn_tx_id}]: Decisões de investimento geradas, mas a exchange não está disponível para execução.")
        error_details += "Exchange not available for order execution; "
        final_status = "failed_order_execution" # Se a execução é crítica
        cash_remaining_after_execution = amount # Nada foi gasto
    
    transactions_db[rnn_tx_id]["executed_trades"] = executed_trades_info
    transactions_db[rnn_tx_id]["cash_after_execution"] = round(cash_remaining_after_execution, 2)
    transactions_db[rnn_tx_id]["portfolio_value_after_execution"] = round(current_portfolio_value, 2)
    

    # =========================================================================
    # 4. SIMULAÇÃO DO PERÍODO DE INVESTIMENTO E CÁLCULO DE LUCRO/PERDA (Só se não houve falha crítica antes)
    # =========================================================================
    value_of_investments_at_eod = current_portfolio_value # Começa com o valor de custo

    if final_status == "completed": # Ou "completed_with_partial_failure"
        transactions_db[rnn_tx_id]["status_details"] = "Simulating EOD valuation"
        logger.info(f"BG TASK [{rnn_tx_id}]: Simulando valorização do portfólio no final do dia...")
        await asyncio.sleep(random.uniform(3, 7)) 

        if current_portfolio_value > 0:
            # Simular mudança de valor do portfólio. A meta de 4.2% é sobre o capital INVESTIDO.
            # O lucro/perda é aplicado ao `current_portfolio_value` (o que foi efetivamente comprado).
            daily_return_factor = 0.042 # A meta
            simulated_performance_factor = random.uniform(0.7, 1.3) # Variação em torno da meta (pode ser prejuízo)
            # Para ser mais realista, o fator de performance deveria ser algo como:
            # random.uniform(-0.05, 0.08) -> -5% a +8% de retorno diário sobre o investido (ainda alto)
            # E não diretamente ligado à meta de 4.2%
            
            # Ajuste para uma simulação de retorno mais plausível (ainda agressiva)
            # Suponha que o retorno diário real possa variar de -3% a +5% sobre o investido
            actual_daily_return_on_portfolio = random.uniform(-0.03, 0.05) 
            
            profit_or_loss_on_portfolio = current_portfolio_value * actual_daily_return_on_portfolio
            value_of_investments_at_eod = current_portfolio_value + profit_or_loss_on_portfolio
            logger.info(f"BG TASK [{rnn_tx_id}]: Portfólio inicial: {current_portfolio_value:.2f}, Retorno simulado: {actual_daily_return_on_portfolio*100:.2f}%, "
                        f"Lucro/Prejuízo no portfólio: {profit_or_loss_on_portfolio:.2f}, Valor EOD do portfólio: {value_of_investments_at_eod:.2f}")
        else: 
            logger.info(f"BG TASK [{rnn_tx_id}]: Nenhum portfólio para valorizar no EOD (nada foi comprado).")
            value_of_investments_at_eod = 0.0
        
        # O calculated_final_amount é o valor dos investimentos liquidados + o caixa que não foi usado
        calculated_final_amount = value_of_investments_at_eod + cash_remaining_after_execution
    
    else: # Se houve falha antes, o valor final é o que sobrou após a falha
        calculated_final_amount = cash_remaining_after_execution + current_portfolio_value # current_portfolio_value pode ser 0 ou parcial
        logger.warning(f"BG TASK [{rnn_tx_id}]: Ciclo de investimento não concluído normalmente ({final_status}). Valor final baseado no estado atual.")

    transactions_db[rnn_tx_id]["eod_portfolio_value_simulated"] = round(value_of_investments_at_eod, 2)
    transactions_db[rnn_tx_id]["final_calculated_amount"] = round(calculated_final_amount, 2)


    # =========================================================================
    # 5. TOKENIZAÇÃO / REGISTRO DA OPERAÇÃO (Só se não houve falha crítica antes)
    # =========================================================================
    if final_status not in ["failed_config", "failed_market_data", "failed_rnn_analysis"]: # Prossegue se ao menos tentou executar
        transactions_db[rnn_tx_id]["status_details"] = "Finalizing transaction log (tokenization)"
        logger.info(f"BG TASK [{rnn_tx_id}]: Registrando (tokenizando) operação detalhadamente...")
        # Placeholder para LÓGICA REAL DE TOKENIZAÇÃO (TOKENIZATION_PLACEHOLDER)
        # 1. Coletar todos os dados relevantes da transação de `transactions_db[rnn_tx_id]`
        #    (market_data_collected, rnn_decisions, executed_trades, eod_portfolio_value_simulated, etc.)
        # 2. Se for usar blockchain:
        #    a. Preparar os dados para um contrato inteligente.
        #    b. Interagir com o contrato (ex: web3.py para Ethereum).
        #    c. Armazenar o hash da transação da blockchain.
        # 3. Se for um registro interno avançado:
        #    a. Assinar digitalmente os dados da transação.
        #    b. Armazenar em um sistema de log imutável ou banco de dados com auditoria.
        
        # Simulação atual (hash dos dados da transação):
        transaction_data_for_hash = {
            "rnn_tx_id": rnn_tx_id, "client_id": client_id, "initial_amount": amount,
            "final_amount_calculated": calculated_final_amount,
            # Incluir resumos ou hashes dos dados coletados para não tornar o hash gigante
            "market_data_summary_keys": list(transactions_db[rnn_tx_id].get("market_data_collected", {}).keys()),
            "rnn_decisions_count": len(transactions_db[rnn_tx_id].get("rnn_decisions", [])),
            "executed_trades_count": len(transactions_db[rnn_tx_id].get("executed_trades", [])),
            "eod_portfolio_value": transactions_db[rnn_tx_id].get("eod_portfolio_value_simulated"),
            "timestamp": datetime.utcnow().isoformat()
        }
        ordered_tx_data_str = json.dumps(transaction_data_for_hash, sort_keys=True)
        proof_token_hash = hashlib.sha256(ordered_tx_data_str.encode('utf-8')).hexdigest()
        
        transactions_db[rnn_tx_id]["proof_of_operation_token"] = proof_token_hash
        transactions_db[rnn_tx_id]["tokenization_method"] = "internal_summary_hash_proof"
        await asyncio.sleep(0.5) # Simula tempo de escrita/hash
        logger.info(f"BG TASK [{rnn_tx_id}]: Operação registrada. Prova (hash): {proof_token_hash[:10]}...")


    # =========================================================================
    # 6. PREPARAR E ENVIAR CALLBACK PARA AIBANK
    # =========================================================================
    if exchange and hasattr(exchange, 'close'):
        try:
            await exchange.close()
            logger.info(f"BG TASK [{rnn_tx_id}]: Conexão ccxt fechada.")
        except Exception as e_close: # Especificar o tipo de exceção se souber
            logger.warning(f"BG TASK [{rnn_tx_id}]: Erro ao fechar conexão ccxt: {str(e_close)}")

    if not AIBANK_CALLBACK_URL or not CALLBACK_SHARED_SECRET:
        logger.error(f"BG TASK [{rnn_tx_id}]: Configuração de callback ausente. Não é possível notificar o AIBank.")
        transactions_db[rnn_tx_id]["callback_status"] = "config_missing_critical"
        return 

    # Certifique-se que `final_status` reflete o estado real da operação
    # Se `error_details` não estiver vazio e `final_status` ainda for "completed", ajuste-o
    if error_details and final_status == "completed":
        final_status = "completed_with_warnings" # Ou um status mais apropriado

    callback_payload_data = InvestmentResultPayload(
        rnn_transaction_id=rnn_tx_id, aibank_transaction_token=aibank_tx_token, client_id=client_id,
        initial_amount=amount, final_amount=round(calculated_final_amount, 2), # Arredonda para 2 casas decimais
        profit_loss=round(calculated_final_amount - amount, 2),
        status=final_status, timestamp=datetime.utcnow(),
        details=error_details if error_details else "Investment cycle processed."
    )
    payload_json_str = callback_payload_data.model_dump_json() # Garante que está usando a string serializada
    
    signature = hmac.new(CALLBACK_SHARED_SECRET.encode('utf-8'), payload_json_str.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-RNN-Signature': signature}

    logger.info(f"BG TASK [{rnn_tx_id}]: Enviando callback para AIBank ({AIBANK_CALLBACK_URL}) com status final '{final_status}'. Payload: {payload_json_str}")
    transactions_db[rnn_tx_id]["callback_status"] = "sending"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client: # Timeout global para o cliente
            response = await client.post(AIBANK_CALLBACK_URL, content=payload_json_str, headers=headers)
            response.raise_for_status()
            logger.info(f"BG TASK [{rnn_tx_id}]: Callback para AIBank enviado com sucesso. Resposta: {response.status_code}")
            transactions_db[rnn_tx_id]["callback_status"] = f"sent_success_{response.status_code}"
    except httpx.RequestError as e_req:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro de REDE ao enviar callback para AIBank: {e_req}")
        transactions_db[rnn_tx_id]["callback_status"] = "sent_failed_network_error"
    except httpx.HTTPStatusError as e_http:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro HTTP do AIBank ao receber callback: {e_http.response.status_code} - {e_http.response.text[:200]}")
        transactions_db[rnn_tx_id]["callback_status"] = f"sent_failed_http_error_{e_http.response.status_code}"
    except Exception as e_cb_final:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro INESPERADO ao enviar callback: {e_cb_final}", exc_info=True)
        transactions_db[rnn_tx_id]["callback_status"] = "sent_failed_unknown_error"


import asyncio 
import random  

    

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

# Função de logger dummy s
# class DummyLogger:
#     def info(self, msg, *args, **kwargs): print(f"INFO: {msg}")
#     def warning(self, msg, *args, **kwargs): print(f"WARNING: {msg}")
#     def error(self, msg, *args, **kwargs): print(f"ERROR: {msg}", kwargs.get('exc_info'))

# if __name__ == "__main__": # Para teste local
#     # logger = DummyLogger() # se não tiver get_logger()
#     # Configuração das variáveis de ambiente para teste local
#     os.environ["AIBANK_API_KEY"] = "test_aibank_key_from_rnn_server"
#     os.environ["AIBANK_CALLBACK_URL"] = "http://localhost:8001/api/rnn_investment_result_callback" # URL do aibank simulado
#     os.environ["CALLBACK_SHARED_SECRET"] = "super_secret_for_callback_signing"
#     # import uvicorn
#     # uvicorn.run(app, host="0.0.0.0", port=8000)