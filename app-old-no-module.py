

import os
import uuid
import time
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import ccxt.async_support as ccxt 

import httpx # Para fazer chamadas HTTP assíncronas (para o callback)
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from app. utils.logger import get_logger 

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



#CHAVES PARA CCXT (para Binance)
# configuradas como vriaveis no Hugging Face Space

CCXT_EXCHANGE_ID = os.environ.get("CCXT_EXCHANGE_ID", "binance") 
CCXT_API_KEY = os.environ.get("CCXT_API_KEY")
CCXT_API_SECRET = os.environ.get("CCXT_API_SECRET")
CCXT_API_PASSWORD = os.environ.get("CCXT_API_PASSWORD") # Opcional

# Binance Testnet
CCXT_SANDBOX_MODE = os.environ.get("CCXT_SANDBOX_MODE", "false").lower() == "true"





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
    """
    Esta função roda em background. Simula a coleta de dados, RNN, execução e tokenização.
    No final, chama o callback para o aibank.
    """
    logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando estratégia de investimento para cliente {client_id}, valor {amount}.")
    transactions_db[rnn_tx_id]["status"] = "processing" # Status geral inicial
    transactions_db[rnn_tx_id]["status_details"] = "Initializing investment cycle"
    
    final_status = "completed" # Status final presumido
    error_details = ""
    calculated_final_amount = amount # Valor inicial, será modificado

    # Inicializa o objeto da exchange ccxt
    exchange = None
    if CCXT_API_KEY and CCXT_API_SECRET: #nicializa se as chaves básicas estiverem presentes
        try:
            exchange_class = getattr(ccxt, CCXT_EXCHANGE_ID)
            config = {
                'apiKey': CCXT_API_KEY,
                'secret': CCXT_API_SECRET,
                'enableRateLimit': True, #  evitar bans da API
                # 'verbose': True, # Para debug detalhado das chamadas ccxt
            }
            if CCXT_API_PASSWORD:
                config['password'] = CCXT_API_PASSWORD
            
            exchange = exchange_class(config)

            if CCXT_SANDBOX_MODE:
                if hasattr(exchange, 'set_sandbox_mode'): # Nem todas as exchanges suportam isso diretamente em ccxt
                    exchange.set_sandbox_mode(True)
                    logger.info(f"BG TASK [{rnn_tx_id}]: CCXT configurado para modo SANDBOX para {CCXT_EXCHANGE_ID}.")
                elif 'test' in exchange.urls: # usar testnet another.way
                    exchange.urls['api'] = exchange.urls['test']
                    logger.info(f"BG TASK [{rnn_tx_id}]: CCXT URLs alteradas para TESTNET para {CCXT_EXCHANGE_ID}.")
                else:
                    logger.warning(f"BG TASK [{rnn_tx_id}]: Modo SANDBOX solicitado mas não explicitamente suportado por ccxt para {CCXT_EXCHANGE_ID} ou URL de teste não encontrada.")
            
            # Carregar mercados para validar símbolos, demorado.
            # await exchange.load_markets() 
            # logger.info(f"BG TASK [{rnn_tx_id}]: Mercados carregados para {CCXT_EXCHANGE_ID}.")

        except AttributeError:
            logger.error(f"BG TASK [{rnn_tx_id}]: Exchange ID '{CCXT_EXCHANGE_ID}' inválida ou não suportada pelo ccxt.")
            error_details += f"Invalid CCXT_EXCHANGE_ID: {CCXT_EXCHANGE_ID}; "
            final_status = "failed_config" # Um novo status para falha de configuração
            # (Pular para o callback aqui)
        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro ao inicializar ccxt para {CCXT_EXCHANGE_ID}: {str(e)}", exc_info=True)
            error_details += f"CCXT initialization error: {str(e)}; "
            final_status = "failed_config"
            # (Pular para o callback aqui)
    else:
        logger.warning(f"BG TASK [{rnn_tx_id}]: CCXT_API_KEY ou CCXT_API_SECRET não configurados. A coleta de dados de cripto e execução de ordens via ccxt serão puladas.")
        #Decidir se é uma falha fatal ou se a estratégia pode prosseguir sem dados de cripto.
        # Precisa lidar com dados ausentes.


    # =========================================================================
    # 1. COLETAR DADOS DE MERCADO (com ccxt integrado)
    # =========================================================================
    logger.info(f"BG TASK [{rnn_tx_id}]: Coletando dados de mercado...")
    transactions_db[rnn_tx_id]["status_details"] = "Fetching market data"
    market_data_results = {
        "crypto": {}, # Dados específicos de cripto
        "stocks": {}, # Dados de ações (integrar yfinance ou outro)
        "other": {}   # Outros dados
    }
    market_data_fetch_success = True

    # --- Defina os pares de cripto ---
    # Estes poderiam vir de uma configuração, ou serem dinâmicos.
    crypto_pairs_to_fetch = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] 

    if exchange: # Buscar se a exchange foi inicializada corretamente
        try:
            for pair in crypto_pairs_to_fetch:
                pair_data = {}
                if exchange.has['fetchTicker']:
                    ticker = await exchange.fetch_ticker(pair)
                    pair_data['ticker'] = {
                        'last': ticker.get('last'),
                        'bid': ticker.get('bid'),
                        'ask': ticker.get('ask'),
                        'volume': ticker.get('baseVolume'), # Ou 'quoteVolume'
                        'timestamp': ticker.get('timestamp')
                    }
                    logger.info(f"BG TASK [{rnn_tx_id}]: Ticker {pair}: Preço {ticker.get('last')}")
                
                if exchange.has['fetchOHLCV']:
                    # timeframe: '1m', '5m', '15m', '1h', '4h', '1d', '1w', '1M'
                    # limit: número de candles
                    ohlcv = await exchange.fetch_ohlcv(pair, timeframe='1h', limit=72) # Últimas 72 horas
                    # Formato OHLCV: [timestamp, open, high, low, close, volume]
                    pair_data['ohlcv_1h'] = ohlcv
                    logger.info(f"BG TASK [{rnn_tx_id}]: Coletado {len(ohlcv)} candles OHLCV para {pair} (1h).")

                # Outros dados que ccxt:
                # if exchange.has['fetchOrderBook']:
                #     order_book = await exchange.fetch_order_book(pair, limit=5) # Top 5 bids/asks
                #     pair_data['order_book_L1'] = { # Exemplo de Level 1
                #         'bids': order_book['bids'][0] if order_book['bids'] else None,
                #         'asks': order_book['asks'][0] if order_book['asks'] else None,
                #     }
                # if exchange.has['fetchTrades']: # Últimas negociações públicas
                #     trades = await exchange.fetch_trades(pair, limit=10)
                #     pair_data['recent_trades'] = trades

                market_data_results["crypto"][pair.replace("/", "_")] = pair_data # Usar _ para chaves de dict seguras

            logger.info(f"BG TASK [{rnn_tx_id}]: Dados de cripto via ccxt coletados.")

        except ccxt.NetworkError as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro de rede ccxt ao coletar dados de mercado: {str(e)}", exc_info=True)
            market_data_fetch_success = False
            error_details += f"CCXT NetworkError: {str(e)}; "
        except ccxt.ExchangeError as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro da exchange ccxt ao coletar dados de mercado: {str(e)}", exc_info=True)
            market_data_fetch_success = False
            error_details += f"CCXT ExchangeError: {str(e)}; "
        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro geral ao coletar dados de cripto via ccxt: {str(e)}", exc_info=True)
            market_data_fetch_success = False
            error_details += f"General CCXT data collection error: {str(e)}; "
    else:
        logger.info(f"BG TASK [{rnn_tx_id}]: Instância da exchange ccxt não disponível. Pulando coleta de dados de cripto.")
        # Se não há 'exchange', a coleta de dados de cripto não pode ocorrerá.
        # Erro, dependendo se as chaves Not.ok.
        if CCXT_API_KEY and CCXT_API_SECRET: # Chaves dadas mas a 'exchange' falhou na init
             market_data_fetch_success = False # Falha se a config estava lá
             error_details += "CCXT exchange object not initialized despite API keys being present; "


    # --- Coleta de dados para outros tipos de ativos (Ações com yfinance) ---
    # try:
    #     import yfinance as yf
    #     aapl = yf.Ticker("AAPL")
    #     hist_aapl = aapl.history(period="5d", interval="1h") # Últimos 5 dias, candles de 1h
    #     if not hist_aapl.empty:
    #         market_data_results["stocks"]["AAPL"] = {
    #             "ohlcv_1h": [[ts.timestamp() * 1000] + list(row) for ts, row in hist_aapl[['Open', 'High', 'Low', 'Close', 'Volume']].iterrows()]
    #         }
    #         logger.info(f"BG TASK [{rnn_tx_id}]: Coletado {len(hist_aapl)} candles para AAPL via yfinance.")
    # except Exception as e:
    #     logger.warning(f"BG TASK [{rnn_tx_id}]: Falha ao buscar dados de ações com yfinance: {e}")
    #   
    

    # --- Simulação para outros dados, se necessário ---
    market_data_results["other"]['simulated_index_level'] = random.uniform(10000, 15000)
    market_data_results["other"]['simulated_crypto_sentiment'] = random.uniform(-1, 1)
    
    if not market_data_fetch_success and (CCXT_API_KEY and CCXT_API_SECRET): # Se as chaves de cripto foram dadas e a coleta falhou
        final_status = "failed_market_data"
        logger.error(f"BG TASK [{rnn_tx_id}]: Coleta de dados de mercado falhou criticamente. {error_details}")
        # (Pular para o callback aqui, pois a RNN pode não ter dados suficientes)
        # 'return' ou lógica de pular precisa ser implementada se a falha for fatal
        # Registrar e permitir que a lógica da RNN tente lidar com dados ausentes/parciais
        pass 
    
    transactions_db[rnn_tx_id]["market_data_collected"] = market_data_results # Armazena para auditoria/debug
    transactions_db[rnn_tx_id]["status_details"] = "Processing RNN analysis"
    logger.info(f"BG TASK [{rnn_tx_id}]: Coleta de dados de mercado concluída (sucesso: {market_data_fetch_success}).")

    # =========================================================================
    # 2. ANÁLISE PELA RNN E TOMADA DE DECISÃO 
    # =========================================================================
    # (alimentada por market_data_results)
    # ...
    logger.info(f"BG TASK [{rnn_tx_id}]: Executando análise RNN com os dados coletados...")
    transactions_db[rnn_tx_id]["status_details"] = "Running RNN model"
    investment_decisions = [] 
    rnn_analysis_success = True

    try:
        
        # A RNN precisará ser capaz de lidar com a estrutura de market_data_results,
        # incluindo a possibilidade de alguns dados estarem ausentes se a coleta falhar.
       
        # investment_decisions = await rnn_model.predict_async(market_data_results, amount_to_invest=amount)
        
        # Simulação para prosseguir:
        await asyncio.sleep(random.uniform(8, 15)) 
        if market_data_results["crypto"]: # Com dados de cripto
            if random.random() > 0.1: 
                num_crypto_assets_to_invest = random.randint(1, len(crypto_pairs_to_fetch))
                chosen_pairs = random.sample(list(market_data_results["crypto"].keys()), k=num_crypto_assets_to_invest)
                
                for crypto_key in chosen_pairs: # crypto_key  "BTC_USDT"
                    asset_symbol = crypto_key.replace("_", "/") # Converte de volta para "BTC/USDT"
                    allocated_amount = (amount / num_crypto_assets_to_invest) * random.uniform(0.7, 0.9) # Aloca uma parte do total
                    investment_decisions.append({
                        "asset_id": asset_symbol, # Usa o símbolo da exchange
                        "type": "CRYPTO",
                        "action": "BUY",
                        "target_usd_amount": round(allocated_amount, 2),
                        "reasoning": f"RNN signal for {asset_symbol} based on simulated data and ticker {market_data_results['crypto'][crypto_key].get('ticker', {}).get('last', 'N/A')}"
                    })
        else:
            logger.info(f"BG TASK [{rnn_tx_id}]: Sem dados de cripto para a RNN processar.")

        if not investment_decisions:
            logger.info(f"BG TASK [{rnn_tx_id}]: RNN não gerou nenhuma decisão de investimento.")
        else:
            logger.info(f"BG TASK [{rnn_tx_id}]: RNN gerou {len(investment_decisions)} decisões: {investment_decisions}")

    except Exception as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro durante análise RNN: {str(e)}", exc_info=True)
        rnn_analysis_success = False
        error_details += f"RNN analysis failed: {str(e)}; "
    
    if not rnn_analysis_success:
        final_status = "failed_rnn_analysis"
        # (Pular para o callback)
        pass

    transactions_db[rnn_tx_id]["rnn_decisions"] = investment_decisions
    transactions_db[rnn_tx_id]["status_details"] = "Preparing to execute orders"
    total_usd_allocated_by_rnn = sum(d['target_usd_amount'] for d in investment_decisions if d['action'] == 'BUY')


    # =========================================================================
    # 3. EXECUÇÃO DE ORDENS (Será detalhado no próximo passo)
    # =========================================================================
    # ... (execução de ordens aqui, usando `exchange` ccxt e `investment_decisions`)
    # ... (Incluindo cálculo de `current_portfolio_value` e `cash_remaining_after_allocation`)
    logger.info(f"BG TASK [{rnn_tx_id}]: Executando ordens baseadas nas decisões da RNN...")
    transactions_db[rnn_tx_id]["status_details"] = "Executing investment orders"
    executed_trades_info = []
    order_execution_success = True
    cash_remaining_after_allocation = amount - total_usd_allocated_by_rnn
    current_portfolio_value = 0 # Valor dos ativos comprados

    # Placeholder para execução
    if investment_decisions:
        for decision in investment_decisions:
            if decision.get("action") == "BUY":
                usd_amount_to_spend = decision.get("target_usd_amount")
                simulated_cost = usd_amount_to_spend * random.uniform(0.99, 1.0)
                executed_trades_info.append({
                    "asset": decision.get("asset_id"), "order_id": f"sim_ord_{uuid.uuid4()}", 
                    "status": "filled", "cost_usd": simulated_cost
                })
                current_portfolio_value += simulated_cost
        await asyncio.sleep(random.uniform(1,3) * len(investment_decisions)) # Simula tempo de execução
    else:
        cash_remaining_after_allocation = amount

    transactions_db[rnn_tx_id]["executed_trades"] = executed_trades_info
    transactions_db[rnn_tx_id]["status_details"] = "Simulating holding period and profit/loss"


    # =========================================================================
    # 4. SIMULAÇÃO DO PERÍODO DE INVESTIMENTO E CÁLCULO DE LUCRO/PERDA
    # =========================================================================
    # ... (Inserir lógia )
    logger.info(f"BG TASK [{rnn_tx_id}]: Simulando período de investimento e fechamento de posições...")
    await asyncio.sleep(random.uniform(5, 10)) 

    if current_portfolio_value > 0:
        profit_on_invested_part = current_portfolio_value * (0.042 * random.uniform(0.8, 1.2)) 
        value_of_investments_at_eod = current_portfolio_value + profit_on_invested_part
    else: 
        value_of_investments_at_eod = 0
        profit_on_invested_part = 0
    
    calculated_final_amount = value_of_investments_at_eod + cash_remaining_after_allocation
    
    logger.info(f"BG TASK [{rnn_tx_id}]: Valor inicial total: {amount:.2f}. "
                f"Valor alocado para investimento: {total_usd_allocated_by_rnn:.2f}. "
                f"Valor dos investimentos no EOD: {value_of_investments_at_eod:.2f}. "
                f"Caixa não alocado: {cash_remaining_after_allocation:.2f}. "
                f"Valor final total: {calculated_final_amount:.2f}")

    transactions_db[rnn_tx_id]["eod_portfolio_value_simulated"] = value_of_investments_at_eod

    # =========================================================================
    # 5. TOKENIZAÇÃO / REGISTRO DA OPERAÇÃO
    # =========================================================================
    # ... (Inserir)
    logger.info(f"BG TASK [{rnn_tx_id}]: Registrando (tokenizando) operação detalhadamente...")
    # ... (código do hash proof)
    await asyncio.sleep(1)

    # =========================================================================
    # 6. PREPARAR E ENVIAR CALLBACK PARA AIBANK
    # =========================================================================
    # (Fechamento da conexão ccxt antes do callback, se a conexão foi aberta e bem sucedida)
    if exchange and hasattr(exchange, 'close'):
        try:
            await exchange.close()
            logger.info(f"BG TASK [{rnn_tx_id}]: Conexão ccxt com {CCXT_EXCHANGE_ID} fechada.")
        except Exception as e:
            logger.warning(f"BG TASK [{rnn_tx_id}]: Erro ao fechar conexão ccxt: {str(e)}")

    # (callback , usando `final_status`, `error_details`, `calculated_final_amount`)
    # ...
    if not AIBANK_CALLBACK_URL or not CALLBACK_SHARED_SECRET:
        logger.error(f"BG TASK [{rnn_tx_id}]: AIBANK_CALLBACK_URL ou CALLBACK_SHARED_SECRET não configurado. Não é possível enviar callback.")
        transactions_db[rnn_tx_id]["callback_status"] = "config_missing"
        return # Não pode prosseguir sem config de callback

    callback_payload_data = InvestmentResultPayload(
        rnn_transaction_id=rnn_tx_id,
        aibank_transaction_token=aibank_tx_token,
        client_id=client_id,
        initial_amount=amount,
        final_amount=calculated_final_amount,
        profit_loss=calculated_final_amount - amount,
        status=final_status, # O status final da operação
        timestamp=datetime.utcnow(),
        details=error_details if final_status != "completed" else "Investment cycle completed successfully."
    )
    payload_json = callback_payload_data.model_dump_json()
    signature = hmac.new(CALLBACK_SHARED_SECRET.encode('utf-8'), payload_json.encode('utf-8'), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json', 'X-RNN-Signature': signature}

    logger.info(f"BG TASK [{rnn_tx_id}]: Enviando callback para AIBank: {AIBANK_CALLBACK_URL} com status final '{final_status}'")
    transactions_db[rnn_tx_id]["callback_status"] = "sending"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(AIBANK_CALLBACK_URL, content=payload_json, headers=headers, timeout=30.0)
            response.raise_for_status()
            logger.info(f"BG TASK [{rnn_tx_id}]: Callback enviado com sucesso para AIBank. Status da resposta: {response.status_code}")
            transactions_db[rnn_tx_id]["callback_status"] = f"sent_success_{response.status_code}"
    except Exception as e: # Captura mais genérica para erros de callback
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro ao enviar callback para AIBank: {str(e)}", exc_info=True)
        # Classificar o erro para o log
        if isinstance(e, httpx.RequestError):
            transactions_db[rnn_tx_id]["callback_status"] = f"sent_failed_request_error"
        elif isinstance(e, httpx.HTTPStatusError):
            transactions_db[rnn_tx_id]["callback_status"] = f"sent_failed_http_error_{e.response.status_code}"
        else:
            transactions_db[rnn_tx_id]["callback_status"] = "sent_failed_unknown_error"



# --- 
""" async def execute_investment_strategy_background(
    rnn_tx_id: str,
    client_id: str,
    amount: float,
    aibank_tx_token: str
):
    
    logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando estratégia de investimento para cliente {client_id}, valor {amount}.")
    transactions_db[rnn_tx_id]["status"] = "processing_market_data"
    
    final_status = "completed"
    error_details = ""
    calculated_final_amount = amount # Valor inicial

    try:
        # 1. COLETAR DADOS DE MERCADO (Placeholder)
                
        logger.info(f"BG TASK [{rnn_tx_id}]: Coletando dados de mercado...")
        transactions_db[rnn_tx_id]["status_details"] = "Fetching market data"
        market_data_results = {}
        market_data_fetch_success = True

        # Exemplo para Cripto com ccxt (requer 'pip install ccxt')
        # import ccxt.async_support as ccxt # Coloque no topo do app.py
        # exchange_id = 'binance' # Exemplo
        # exchange_class = getattr(ccxt, exchange_id)
        # exchange = exchange_class({
        #     'apiKey': EXCHANGE_API_KEY, # Do os.environ
        #     'secret': EXCHANGE_API_SECRET, # Do os.environ
        #     'enableRateLimit': True, # Importante
        # })

        try:
            # --- Exemplo para buscar dados de BTC/USDT ---
            # if exchange.has['fetchTicker']:
            #     ticker_btc = await exchange.fetch_ticker('BTC/USDT')
            #     market_data_results['BTC_USDT_ticker'] = ticker_btc
            #     logger.info(f"BG TASK [{rnn_tx_id}]: Ticker BTC/USDT: {ticker_btc['last']}")
            # if exchange.has['fetchOHLCV']:
            #     ohlcv_btc = await exchange.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=100) # Últimas 100 horas
            #     market_data_results['BTC_USDT_ohlcv_1h'] = ohlcv_btc
            #     logger.info(f"BG TASK [{rnn_tx_id}]: Coletado {len(ohlcv_btc)} candles OHLCV para BTC/USDT 1h.")
            
            # --- Exemplo para Ações com yfinance (requer 'pip install yfinance') ---
            # import yfinance as yf # Coloque no topo do app.py
            # aapl = yf.Ticker("AAPL")
            # hist_aapl = aapl.history(period="1mo") # Dados do último mês
            # market_data_results['AAPL_history_1mo'] = hist_aapl.to_dict() # Pode ser grande, serialize com cuidado
            # current_price_aapl = hist_aapl['Close'].iloc[-1] if not hist_aapl.empty else None
            # market_data_results['AAPL_current_price'] = current_price_aapl
            # logger.info(f"BG TASK [{rnn_tx_id}]: Preço atual AAPL (yfinance): {current_price_aapl}")

            # --- Placeholder para sua lógica real de coleta ---
            # Você precisará definir QUAIS ativos e QUAIS dados são necessários para sua RNN.
            # Este é um ponto crucial para sua estratégia.
            # Simulação para prosseguir:
            await asyncio.sleep(random.uniform(3, 7)) # Simula demora da coleta real
            market_data_results['simulated_index_level'] = random.uniform(10000, 15000)
            market_data_results['simulated_crypto_sentiment'] = random.uniform(-1, 1)
            logger.info(f"BG TASK [{rnn_tx_id}]: Dados de mercado (simulados/reais) coletados.")

        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro ao coletar dados de mercado: {str(e)}", exc_info=True)
            market_data_fetch_success = False
            error_details += f"Market data collection failed: {str(e)}; "
            # Decida se a falha aqui é crítica e impede de continuar.
            # Se sim, atualize final_status e pule para o callback.

        # finally: # Importante para fechar conexões de exchange em ccxt
        #    if 'exchange' in locals() and hasattr(exchange, 'close'):
        #        await exchange.close()

        if not market_data_fetch_success:
            # Lógica para lidar com falha na coleta de dados (ex: não prosseguir)
            final_status = "failed_market_data"
            # ... (atualize transactions_db e pule para a seção de callback) ...
            # (Este 'return' ou lógica de pular precisa ser implementada se a falha for fatal)
            pass # Por ora, deixamos prosseguir com dados possivelmente incompletos ou apenas simulados

        transactions_db[rnn_tx_id]["market_data_collected"] = market_data_results # Armazene para auditoria/debug
        transactions_db[rnn_tx_id]["status_details"] = "Processing RNN analysis"


        # 2. ANÁLISE PELA RNN E TOMADA DE DECISÃO (Placeholder)
        l

        logger.info(f"BG TASK [{rnn_tx_id}]: Executando análise RNN com os dados coletados...")
        transactions_db[rnn_tx_id]["status_details"] = "Running RNN model"
        investment_decisions = [] # Lista de decisões: {'asset': 'BTC/USDT', 'action': 'BUY', 'amount_usd': 5000, 'price_target': 70000}
        rnn_analysis_success = True

        try:
            # --- SUBSTITUA PELA CHAMADA AO SEU MODELO RNN ---
            # Exemplo: Supondo que você tenha uma classe ou função rnn_predictor
            # from rnn.models.predictor import rnn_predictor # Exemplo de import
            
            # Supondo que seu predictor precise dos dados de mercado e do montante a investir
            # investment_decisions = await rnn_predictor.generate_signals_async(
            #     market_data_results, 
            #     amount_to_invest=amount # O montante total disponível para este ciclo
            # )
            
            # Simulação para prosseguir:
            await asyncio.sleep(random.uniform(8, 15)) # Simula processamento da RNN
            if random.random() > 0.1: # 90% de chance de "decidir" investir
                num_assets_to_invest = random.randint(1, 3)
                for i in range(num_assets_to_invest):
                    asset_name = random.choice(["SIMULATED_CRYPTO_X", "SIMULATED_STOCK_Y", "SIMULATED_BOND_Z"])
                    action = random.choice(["BUY", "HOLD"]) # Simplificado, sem SELL por enquanto
                    if action == "BUY":
                        # Alocar uma porção do 'amount' total para este ativo
                        allocated_amount = (amount / num_assets_to_invest) * random.uniform(0.8, 1.0) 
                        investment_decisions.append({
                            "asset_id": f"{asset_name}_{i}",
                            "type": "CRYPTO" if "CRYPTO" in asset_name else "STOCK", # Exemplo
                            "action": action,
                            "target_usd_amount": round(allocated_amount, 2),
                            "reasoning": "RNN signal strong based on simulated data" # Adicione o output real da RNN
                        })
            
            if not investment_decisions:
                logger.info(f"BG TASK [{rnn_tx_id}]: RNN não gerou nenhuma decisão de investimento (ou decidiu não investir).")
                # Isso pode ser um resultado válido.
            else:
                logger.info(f"BG TASK [{rnn_tx_id}]: RNN gerou {len(investment_decisions)} decisões: {investment_decisions}")

        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Erro durante análise RNN: {str(e)}", exc_info=True)
            rnn_analysis_success = False
            error_details += f"RNN analysis failed: {str(e)}; "

        if not rnn_analysis_success:
            final_status = "failed_rnn_analysis"
            # ... (atualize transactions_db e pule para a seção de callback) ...
            pass

        transactions_db[rnn_tx_id]["rnn_decisions"] = investment_decisions
        transactions_db[rnn_tx_id]["status_details"] = "Preparing to execute orders"

        # Antes de executar ordens, vamos calcular o valor que REALMENTE foi investido
        # e o que pode ter sobrado, já que a RNN pode não usar todo o 'amount'.
        total_usd_allocated_by_rnn = sum(d['target_usd_amount'] for d in investment_decisions if d['action'] == 'BUY')
        # calculated_final_amount = amount # Inicializa com o montante original
        # Esta variável será atualizada após a execução das ordens e cálculo do lucro/perda

    
        # 3. EXECUÇÃO DE ORDENS (Placeholder)
              
        # Dentro de execute_investment_strategy_background, substituindo a seção de execução de ordens:

        logger.info(f"BG TASK [{rnn_tx_id}]: Executando ordens baseadas nas decisões da RNN...")
        transactions_db[rnn_tx_id]["status_details"] = "Executing investment orders"
        executed_trades_info = []
        order_execution_success = True

        # O calculated_final_amount começa como o 'amount' inicial.
        # Vamos deduzir o que foi efetivamente usado para compras
        # e depois adicionar os lucros/perdas.
        # Por enquanto, vamos assumir que o investimento visa usar o 'total_usd_allocated_by_rnn'.
        # E o restante do 'amount' não alocado fica como "cash".
        cash_remaining_after_allocation = amount - total_usd_allocated_by_rnn
        current_portfolio_value = 0 # Valor dos ativos comprados

        # --- Exemplo de lógica de execução para decisões de COMPRA (BUY) ---
        if investment_decisions: # Apenas se houver decisões
            # exchange_exec = ccxt.binance({'apiKey': EXCHANGE_API_KEY, 'secret': EXCHANGE_API_SECRET}) # Exemplo
            try:
                for decision in investment_decisions:
                    if decision.get("action") == "BUY":
                        asset_id_to_buy = decision.get("asset_id") # Ex: "BTC/USDT" ou um ID interno que mapeia para um símbolo
                        usd_amount_to_spend = decision.get("target_usd_amount")
                        
                        logger.info(f"BG TASK [{rnn_tx_id}]: Tentando comprar {usd_amount_to_spend} USD de {asset_id_to_buy}")
                        
                        # --- SUBSTITUA PELA LÓGICA REAL DE EXECUÇÃO NA EXCHANGE ---
                        # Exemplo com ccxt (precisa de mais detalhes como símbolo de mercado correto):
                        # symbol_on_exchange = convert_asset_id_to_exchange_symbol(asset_id_to_buy, exchange_exec.id)
                        # current_price = (await exchange_exec.fetch_ticker(symbol_on_exchange))['last']
                        # amount_of_asset_to_buy = usd_amount_to_spend / current_price
                        
                        # order = await exchange_exec.create_market_buy_order(symbol_on_exchange, amount_of_asset_to_buy)
                        # logger.info(f"BG TASK [{rnn_tx_id}]: Ordem de compra para {asset_id_to_buy} enviada: {order['id']}")
                        # executed_trades_info.append({
                        #     "asset": asset_id_to_buy,
                        #     "order_id": order['id'],
                        #     "status": order.get('status', 'unknown'),
                        #     "amount_filled": order.get('filled', 0),
                        #     "avg_price": order.get('average', current_price),
                        #     "cost_usd": order.get('cost', usd_amount_to_spend), # Custo real da ordem
                        #     "fees": order.get('fee', {}),
                        # })
                        # current_portfolio_value += order.get('cost', usd_amount_to_spend) # Adiciona o valor do ativo comprado
                        
                        # Simulação para prosseguir:
                        await asyncio.sleep(random.uniform(1, 3)) # Simula envio de ordem
                        simulated_order_id = f"sim_ord_{uuid.uuid4()}"
                        simulated_cost = usd_amount_to_spend * random.uniform(0.99, 1.0) # Slippage simulado
                        executed_trades_info.append({
                            "asset": asset_id_to_buy,
                            "order_id": simulated_order_id,
                            "status": "filled",
                            "amount_filled": simulated_cost / random.uniform(100, 200), # Qtd de ativo simulada
                            "avg_price": random.uniform(100, 200), # Preço simulado
                            "cost_usd": simulated_cost,
                            "fees": {"currency": "USD", "cost": simulated_cost * 0.001} # Taxa simulada
                        })
                        current_portfolio_value += simulated_cost
                        logger.info(f"BG TASK [{rnn_tx_id}]: Ordem simulada {simulated_order_id} para {asset_id_to_buy} preenchida, custo {simulated_cost:.2f} USD.")
                    else:
                        logger.info(f"BG TASK [{rnn_tx_id}]: Decisão '{decision.get('action')}' para {decision.get('asset_id')} não é uma compra, pulando execução por enquanto.")
            
            except Exception as e:
                logger.error(f"BG TASK [{rnn_tx_id}]: Erro durante execução de ordens: {str(e)}", exc_info=True)
                order_execution_success = False
                error_details += f"Order execution failed: {str(e)}; "
            # finally:
            #     if 'exchange_exec' in locals() and hasattr(exchange_exec, 'close'):
            #         await exchange_exec.close()
        else:
            logger.info(f"BG TASK [{rnn_tx_id}]: Nenhuma decisão de investimento para executar.")
            # Se não há decisões, o current_portfolio_value é 0 e o cash_remaining é todo o 'amount'
            cash_remaining_after_allocation = amount 

        if not order_execution_success:
            final_status = "failed_order_execution"
            # ... (atualize transactions_db e pule para a seção de callback) ...
            # O valor do portfólio aqui pode ser parcial se algumas ordens falharam
            pass

        transactions_db[rnn_tx_id]["executed_trades"] = executed_trades_info
        transactions_db[rnn_tx_id]["status_details"] = "Simulating holding period and profit/loss"

        # --- SIMULAÇÃO DO PERÍODO DE INVESTIMENTO E CÁLCULO DE LUCRO/PERDA DIÁRIO ---
        # Em um sistema real, você monitoraria as posições e as fecharia no final do dia.
        # Ou, se for um investimento de mais longo prazo, apenas calcularia o valor atual do portfólio.
        # Para o objetivo de 4.2% ao dia, é implícito que as posições são fechadas diariamente.

        logger.info(f"BG TASK [{rnn_tx_id}]: Simulando período de investimento e fechamento de posições...")
        await asyncio.sleep(random.uniform(5, 10)) # Simula o dia passando

        # Supondo que todas as posições são vendidas no final do "dia"
        # E o current_portfolio_value muda com base no mercado.
        # Para simular o objetivo de 4.2% sobre o VALOR INVESTIDO (current_portfolio_value no momento da compra):
        if current_portfolio_value > 0: # Se algo foi investido
            profit_on_invested_part = current_portfolio_value * (0.042 * random.uniform(0.8, 1.2)) # Simula variação no lucro
            value_of_investments_at_eod = current_portfolio_value + profit_on_invested_part
        else: # Nada foi investido
            value_of_investments_at_eod = 0
            profit_on_invested_part = 0

        # O calculated_final_amount é o valor dos investimentos no fim do dia + o caixa que não foi alocado
        calculated_final_amount = value_of_investments_at_eod + cash_remaining_after_allocation

        logger.info(f"BG TASK [{rnn_tx_id}]: Valor inicial total: {amount:.2f}. "
                    f"Valor alocado para investimento: {total_usd_allocated_by_rnn:.2f}. "
                    f"Valor dos investimentos no EOD: {value_of_investments_at_eod:.2f}. "
                    f"Caixa não alocado: {cash_remaining_after_allocation:.2f}. "
                    f"Valor final total: {calculated_final_amount:.2f}")

        transactions_db[rnn_tx_id]["eod_portfolio_value_simulated"] = value_of_investments_at_eod

    

        # 4. TOKENIZAÇÃO / REGISTRO DA OPERAÇÃO (Placeholder)
        logger.info(f"BG TASK [{rnn_tx_id}]: Registrando (tokenizando) operação...")
        # Aqui você implementaria sua lógica de tokenização.
        # Poderia ser salvar em uma blockchain, ou um registro detalhado e imutável no seu DB.
        # Ex: await tokenize_operation_async(rnn_tx_id, client_id, investment_decisions, execution_results)
        await asyncio.sleep(2)
        transactions_db[rnn_tx_id]["tokenization_status"] = "completed"
        logger.info(f"BG TASK [{rnn_tx_id}]: Operação registrada/tokenizada.")

        transactions_db[rnn_tx_id]["status"] = "completed"
        transactions_db[rnn_tx_id]["final_amount"] = calculated_final_amount
        transactions_db[rnn_tx_id]["profit_loss"] = calculated_final_amount - amount

    except Exception as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro durante execução da estratégia: {str(e)}", exc_info=True)
        final_status = "failed"
        error_details = str(e)
        transactions_db[rnn_tx_id]["status"] = "failed"
        transactions_db[rnn_tx_id]["error"] = error_details
        # Em caso de falha, o final_amount pode ser o inicial ou o que foi possível recuperar
        calculated_final_amount = amount # Ou o valor parcial se algumas ordens falharam

    # 5. PREPARAR E ENVIAR CALLBACK PARA AIBANK
    if not AIBANK_CALLBACK_URL or not CALLBACK_SHARED_SECRET:
        logger.error(f"BG TASK [{rnn_tx_id}]: AIBANK_CALLBACK_URL ou CALLBACK_SHARED_SECRET não configurado. Não é possível enviar callback.")
        transactions_db[rnn_tx_id]["callback_status"] = "config_missing"
        return

    callback_payload = InvestmentResultPayload(
        rnn_transaction_id=rnn_tx_id,
        aibank_transaction_token=aibank_tx_token,
        client_id=client_id,
        initial_amount=amount,
        final_amount=calculated_final_amount,
        profit_loss=calculated_final_amount - amount,
        status=final_status,
        timestamp=datetime.utcnow(),
        details=error_details if final_status == "failed" else "Investment cycle completed."
    )

    payload_json = callback_payload.model_dump_json()
    
    # Criar assinatura HMAC para segurança do callback
    signature = hmac.new(
        CALLBACK_SHARED_SECRET.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-RNN-Signature': signature # Assinatura para o aibank verificar
    }

    logger.info(f"BG TASK [{rnn_tx_id}]: Enviando callback para AIBank: {AIBANK_CALLBACK_URL}")
    transactions_db[rnn_tx_id]["callback_status"] = "sending"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(AIBANK_CALLBACK_URL, content=payload_json, headers=headers, timeout=30.0)
            response.raise_for_status() # Lança exceção para erros HTTP 4xx/5xx
            logger.info(f"BG TASK [{rnn_tx_id}]: Callback enviado com sucesso para AIBank. Status: {response.status_code}")
            transactions_db[rnn_tx_id]["callback_status"] = f"sent_success_{response.status_code}"
    except httpx.RequestError as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro ao enviar callback para AIBank (RequestError): {str(e)}")
        transactions_db[rnn_tx_id]["callback_status"] = f"sent_failed_request_error"
    except httpx.HTTPStatusError as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro HTTP ao enviar callback para AIBank (HTTPStatusError): {e.response.status_code} - {e.response.text}")
        transactions_db[rnn_tx_id]["callback_status"] = f"sent_failed_http_error_{e.response.status_code}"
    except Exception as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Erro inesperado ao enviar callback: {str(e)}", exc_info=True)
        transactions_db[rnn_tx_id]["callback_status"] = "sent_failed_unknown_error"

 """
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