# rnn/app.py


import sys
import os
sys.path.insert(0, os.path.dirname(__file__))  # Adiciona a raiz ao path
import uuid
import time
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.utils.ccxt_utils import get_ccxt_exchange 
from src.utils.market_data_utils import fetch_btc_dominance,get_market_sentiment
from src.utils.technical_analysis_utils import fetch_crypto_data, calculate_rsi
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager


import uvicorn

import httpx # Para fazer chamadas HTTP assíncronas (para o callback)
from fastapi import FastAPI, Request, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from src.model.rnn_predictor import RNNModelPredictor
from src.utils.logger import get_logger 



logger = get_logger()

# --- Configuração Inicial e Variáveis de Ambiente (Secrets do Hugging Face) ---
AIBANK_API_KEY = os.environ.get("AIBANK_API_KEY") # Chave que o aibank usa para chamar esta API RNN
AIBANK_CALLBACK_URL = os.environ.get("AIBANK_CALLBACK_URL") # URL no aibank para onde esta API RNN enviará o resultado
CALLBACK_SHARED_SECRET = os.environ.get("CALLBACK_SHARED_SECRET") # Segredo para assinar/verificar o payload do callback

# Chaves para serviços externos 
MARKET_DATA_API_KEY = os.environ.get("MARKET_DATA_API_KEY")
EXCHANGE_API_KEY = os.environ.get("EXCHANGE_API_KEY")
EXCHANGE_API_SECRET = os.environ.get("EXCHANGE_API_SECRET")



async def verify_aibank_key(authorization: str = Header(None)):
    if not authorization:
        logger.warning("Authorization header ausente.")
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        logger.warning(f"Formato inválido do Authorization header: {authorization}")
        raise HTTPException(status_code=401, detail="Authorization header must be 'Bearer <token>'")

    token_from_aibank = parts[1]
    logger.info(f"Chave recebida: {token_from_aibank}")  # 🔍 Log da chave recebida
    logger.info(f"Chave esperada (AIBANK_API_KEY): {AIBANK_API_KEY}")  # 🔍 Log da chave configurada

    if not hmac.compare_digest(token_from_aibank, AIBANK_API_KEY):
        logger.warning(f"Chave inválida: '{token_from_aibank}' ≠ '{AIBANK_API_KEY}'")
        raise HTTPException(status_code=403, detail="Invalid API Key provided by AIBank.")

    logger.info("✅ API Key verificada com sucesso.")
    return True



if not AIBANK_API_KEY:
    logger.warning("AIBANK_API_KEY não configurada. A autenticação para /api/invest falhou.")
if not AIBANK_CALLBACK_URL:
    logger.warning("AIBANK_CALLBACK_URL não configurada. O callback para o aibank falhou.")
if not CALLBACK_SHARED_SECRET:
    logger.warning("CALLBACK_SHARED_SECRET não configurado. A segurança do callback está comprometida.")

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
# --- Simulação de Banco de Dados de Transações DEV ---
# Em produção  MongoDB
transactions_db: Dict[str, Dict[str, Any]] = {}

# --- Modelos Pydantic ---
class InvestmentRequest(BaseModel):
    client_id: str
    amount: float # = Field(..., gt=1) # Garante que o montante seja positivo
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

# --- Lógica de Negócio Principal (Real e em Background) ---

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
    error_details = ""
    calculated_final_amount = amount
    market_data_results = {"crypto": {}, "stocks": {}, "other": {}}

    # Verifica se o modelo RNN está carregado
    exchange = None  # Importante inicializar como None
    logger.info("Iniciando tarefa de investimento em background...")

    try:
    # Inicializa a exchange ccxt
        exchange = await get_ccxt_exchange(logger_instance=logger)
        if not exchange:
            logger.warning(f"BG TASK [{rnn_tx_id}]: Falha ao inicializar a exchange.")
            if os.environ.get("CCXT_API_KEY") and os.environ.get("CCXT_API_SECRET"):
                error_details += "Failed to initialize CCXT exchange despite API keys being present; "
                final_status = "failed_config"
            # Continua para callback

        # =========================================================================
        # 1. COLETAR DADOS DE MERCADO (REAL)
        # =========================================================================
        logger.info(f"BG TASK [{rnn_tx_id}]: Coletando dados de mercado...")
        transactions_db[rnn_tx_id]["status_details"] = "Fetching market data"
        #market_data_results = {"crypto": {}, "stocks": {}, "other": {}}
        critical_data_fetch_failed = False

        # --- 1.1 CRIPTO: Binance via CCXT ---
        if exchange:
            crypto_pairs_to_fetch = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "DOGE/USDT"]
            for pair in crypto_pairs_to_fetch:
                try:
                    # OHLCV (1h)
                    ohlcv = await exchange.fetch_ohlcv(pair, timeframe='1h', limit=168)  # 168h = 1 semana
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    # Ticker atual
                    ticker = await exchange.fetch_ticker(pair)
                    last_price = ticker['last']
                    
                    # Indicadores técnicos simples
                    df['sma_20'] = df['close'].rolling(20).mean()
                    df['rsi'] = calculate_rsi(df['close'], window=14)
                    current_rsi = df['rsi'].iloc[-1]
                    
                    market_data_results["crypto"][pair] = {
                        "ohlcv_1h": ohlcv,
                        "ticker": ticker,
                        "current_price": last_price,
                        "technical_indicators": {
                            "sma_20": float(df['sma_20'].iloc[-1]),
                            "rsi": float(current_rsi),
                            "volatility_24h": float(df['close'].pct_change().std() * np.sqrt(24))
                        }
                    }
                    logger.info(f"BG TASK [{rnn_tx_id}]: Dados coletados para {pair}")
                except Exception as e:
                    logger.error(f"BG TASK [{rnn_tx_id}]: Falha ao coletar dados para {pair}: {str(e)}")
                    market_data_results["crypto"][pair] = {"error": str(e)}
                    if pair == "BTC/USDT":
                        critical_data_fetch_failed = True  # BTC é crítico
        else:
            logger.warning(f"BG TASK [{rnn_tx_id}]: Exchange não disponível para coleta de cripto.")
            if os.environ.get("CCXT_API_KEY"):
                error_details += "CCXT exchange not initialized; "
                critical_data_fetch_failed = True

    except Exception as e:
        # Captura qualquer erro inesperado durante a execução
        logger.critical(f"Erro crítico na tarefa de background: {e}", exc_info=True)
        # O exc_info=True é vital para logar o traceback completo como você viu

    finally:
        # --- 4. LIMPEZA DE RECURSOS ---
        # Este bloco SEMPRE será executado, não importa o que aconteça no 'try'.
        if exchange:
            logger.info("Fechando conexão com a exchange para liberar recursos...")
            await exchange.close()
            logger.info("Conexão com a exchange fechada.")
        else:
            logger.info("Nenhuma conexão com a exchange para fechar.")

    # --- 1.2 AÇÕES: Yahoo Finance ---
    market_data_results = {
            "crypto": {},
            "stocks": {}, 
            "other": {}
        }
    try:
        import yfinance as yf
        stock_symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
        for symbol in stock_symbols:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo", interval="1d")
            if not hist.empty:
                # Calcula RSI e SMA
                hist['rsi'] = calculate_rsi(hist['Close'], window=14)
                hist['sma_20'] = hist['Close'].rolling(20).mean()
                market_data_results["stocks"][symbol] = {
                    "history": hist.to_dict('records'),
                    "info": ticker.info,
                    "current_price": hist['Close'].iloc[-1],
                    "technical_indicators": {
                        "rsi": float(hist['rsi'].iloc[-1]),
                        "sma_20": float(hist['sma_20'].iloc[-1])
                    }
                }
                logger.info(f"BG TASK [{rnn_tx_id}]: Dados coletados para ação {symbol}")
            else:
                market_data_results["stocks"][symbol] = {"error": "No data returned"}
    except Exception as e:
        logger.error(f"BG TASK [{rnn_tx_id}]: Falha ao coletar dados de ações: {str(e)}")
        error_details += f"YFinance fetch failed: {str(e)}; "
        # Não é crítico se o foco é cripto

    # --- 1.3 OUTROS DADOS ---
    market_data_results["other"]["btc_dominance"] = await fetch_btc_dominance()
    market_data_results["other"]["market_risk_sentiment"] = await get_market_sentiment() 
   
    
    transactions_db[rnn_tx_id]["market_data_collected"] = market_data_results

    if critical_data_fetch_failed:
        final_status = "failed_market_data"
        logger.error(f"BG TASK [{rnn_tx_id}]: Coleta de dados falhou criticamente. {error_details}")
    else:
        logger.info(f"BG TASK [{rnn_tx_id}]: Coleta de dados concluída.")
        transactions_db[rnn_tx_id]["status_details"] = "Processing RNN analysis"



    # =========================================================================
    # 2. ANÁLISE PELA RNN E TOMADA DE DECISÃO
    # =========================================================================
    investment_decisions: List[Dict[str, Any]] = [] 
    total_usd_allocated_by_rnn = 0.0
    loop = asyncio.get_running_loop() 

    if final_status == "completed": 
        logger.info(f"BG TASK [{rnn_tx_id}]: Executando análise RNN...")
        transactions_db[rnn_tx_id]["status_details"] = "Running RNN model"
        rnn_analysis_success = True
        
        # CORRIGIDO: Acessando app.state.rnn_predictor
        predictor: Optional[RNNModelPredictor] = getattr(app.state, 'rnn_predictor', None)

        try:
                crypto_data_for_rnn = market_data_results.get("crypto", {})
                candidate_assets = [
                    asset_key for asset_key, data in crypto_data_for_rnn.items() 
                    if data and not data.get("error") and data.get("ohlcv_1h") # Apenas com dados válidos
                ]
                
                # --- Parâmetros de Gerenciamento de Risco e Alocação (AJUSTE FINO É CRUCIAL) ---
                # Risco total do portfólio para este ciclo (ex: não usar mais que 50% do capital total em novas posições)
                MAX_CAPITAL_DEPLOYMENT_PCT_THIS_CYCLE = 0.75 # Usar até 75% do 'amount'
                
                # Risco por ativo individual (percentual do 'amount' TOTAL)
                MAX_ALLOCATION_PER_ASSET_PCT_OF_TOTAL = 0.15 # Ex: máx 15% do capital total em UM ativo
                MIN_ALLOCATION_PER_ASSET_PCT_OF_TOTAL = 0.02 # Ex: mín 2% do capital total para valer a pena

                MIN_USD_PER_ORDER = 25.00     # Mínimo de USD por ordem
                MAX_CONCURRENT_POSITIONS = 4  # Máximo de posições abertas simultaneamente
                
                # Limiares de Confiança da RNN
                CONFIDENCE_STRONG_BUY = 0.80 # Confiança para considerar uma alocação maior
                CONFIDENCE_MODERATE_BUY = 0.65 # Confiança mínima para considerar uma alocação base
                CONFIDENCE_WEAK_BUY = 0.55    # Confiança para uma alocação muito pequena ou nenhuma

                allocated_capital_this_cycle = 0.0
                
                # Para diversificação, podemos querer limitar a avaliação ou dar pesos
                # random.shuffle(candidate_assets) 

                for asset_key in candidate_assets:
                    if len(investment_decisions) >= MAX_CONCURRENT_POSITIONS:
                        logger.info(f"BG TASK [{rnn_tx_id}]: Limite de {MAX_CONCURRENT_POSITIONS} posições concorrentes atingido.")
                        break
                    
                    # Verifica se já usamos o capital máximo para o ciclo
                    if allocated_capital_this_cycle >= amount * MAX_CAPITAL_DEPLOYMENT_PCT_THIS_CYCLE:
                        logger.info(f"BG TASK [{rnn_tx_id}]: Limite de capital para o ciclo ({MAX_CAPITAL_DEPLOYMENT_PCT_THIS_CYCLE*100}%) atingido.")
                        break

                    asset_symbol = asset_key.replace("_", "/")
                    logger.info(f"BG TASK [{rnn_tx_id}]: RNN avaliando ativo: {asset_symbol}")
                    
                    signal, confidence_prob = await predictor.predict_for_asset(
                        crypto_data_for_rnn[asset_key], 
                        loop=loop
                    )

                    if signal == 1 and confidence_prob is not None: # Sinal de COMPRA e confiança válida
                        target_usd_allocation = 0.0

                        if confidence_prob >= CONFIDENCE_STRONG_BUY:
                            # Alocação maior para sinais fortes
                            # Ex: entre 60% e 100% da alocação máxima permitida por ativo
                            alloc_factor = 0.6 + 0.4 * ((confidence_prob - CONFIDENCE_STRONG_BUY) / (1.0 - CONFIDENCE_STRONG_BUY + 1e-6))
                            target_usd_allocation = (amount * MAX_ALLOCATION_PER_ASSET_PCT_OF_TOTAL) * alloc_factor
                            reason = f"RNN STRONG BUY signal (Conf: {confidence_prob:.3f})"
                        elif confidence_prob >= CONFIDENCE_MODERATE_BUY:
                            # Alocação base para sinais moderados
                            # Ex: entre 30% e 60% da alocação máxima permitida por ativo
                            alloc_factor = 0.3 + 0.3 * ((confidence_prob - CONFIDENCE_MODERATE_BUY) / (CONFIDENCE_STRONG_BUY - CONFIDENCE_MODERATE_BUY + 1e-6))
                            target_usd_allocation = (amount * MAX_ALLOCATION_PER_ASSET_PCT_OF_TOTAL) * alloc_factor
                            reason = f"RNN MODERATE BUY signal (Conf: {confidence_prob:.3f})"
                        elif confidence_prob >= CONFIDENCE_WEAK_BUY:
                             # Alocação pequena para sinais fracos (ou nenhuma)
                            alloc_factor = 0.1 + 0.2 * ((confidence_prob - CONFIDENCE_WEAK_BUY) / (CONFIDENCE_MODERATE_BUY - CONFIDENCE_WEAK_BUY + 1e-6))
                            target_usd_allocation = (amount * MAX_ALLOCATION_PER_ASSET_PCT_OF_TOTAL) * alloc_factor
                            reason = f"RNN WEAK BUY signal (Conf: {confidence_prob:.3f})"
                        else:
                            logger.info(f"BG TASK [{rnn_tx_id}]: Sinal COMPRA para {asset_symbol} mas confiança ({confidence_prob:.3f}) abaixo do limiar WEAK_BUY ({CONFIDENCE_WEAK_BUY}). Pulando.")
                            continue
                        
                        # Garantir que a alocação não seja menor que a mínima permitida (percentual do total)
                        target_usd_allocation = max(target_usd_allocation, amount * MIN_ALLOCATION_PER_ASSET_PCT_OF_TOTAL)

                        # Garantir que não exceda o capital restante disponível neste CICLO
                        capital_left_for_this_cycle = (amount * MAX_CAPITAL_DEPLOYMENT_PCT_THIS_CYCLE) - allocated_capital_this_cycle
                        actual_usd_allocation = min(target_usd_allocation, capital_left_for_this_cycle)
                        
                        # Garantir que a ordem mínima em USD seja respeitada
                        if actual_usd_allocation < MIN_USD_PER_ORDER:
                            logger.info(f"BG TASK [{rnn_tx_id}]: Alocação final ({actual_usd_allocation:.2f}) para {asset_symbol} abaixo do mínimo de ordem ({MIN_USD_PER_ORDER}). Pulando.")
                            continue
                        
                        # Adicionar à lista de decisões
                        investment_decisions.append({
                            "asset_id": asset_symbol, "type": "CRYPTO", "action": "BUY",
                            "target_usd_amount": round(actual_usd_allocation, 2),
                            "rnn_confidence": round(confidence_prob, 4),
                            "reasoning": reason
                        })
                        allocated_capital_this_cycle += round(actual_usd_allocation, 2)
                        logger.info(f"BG TASK [{rnn_tx_id}]: Decisão: COMPRAR {actual_usd_allocation:.2f} USD de {asset_symbol}. {reason}")
                    
                    # ... (restante da lógica para signal 0 ou None) ...
        except Exception as e: # Captura exceções da lógica da RNN
                logger.error(f"BG TASK [{rnn_tx_id}]: Erro CRÍTICO durante análise/predição RNN: {str(e)}", exc_info=True)
                rnn_analysis_success = False # Marca que a análise RNN falhou
                error_details += f"Critical RNN analysis/prediction error: {str(e)}; "


        total_usd_allocated_by_rnn = allocated_capital_this_cycle 
      
      
        

        if not predictor or not predictor.model: # Verifica se o preditor e o modelo interno existem
            logger.warning(f"BG TASK [{rnn_tx_id}]: Instância do preditor RNN não disponível ou modelo interno não carregado. Pulando análise RNN.")
            rnn_analysis_success = False 
            error_details += "RNN model/predictor not available for prediction; "
        else:
            try:
                # ... (lógica de iteração sobre `candidate_assets` e chamada a `predictor.predict_for_asset` como na resposta anterior)
                # ... (lógica de alocação de capital como na resposta anterior)
                # Garantir que toda essa lógica está dentro deste bloco 'else'
                crypto_data_for_rnn = market_data_results.get("crypto", {})
                candidate_assets = [
                    asset_key for asset_key, data in crypto_data_for_rnn.items() 
                    if data and not data.get("error") and data.get("ohlcv_1h")
                ]
                
                MAX_RISK_PER_ASSET_PCT = 0.05 
                MIN_USD_PER_ORDER = 20.00    
                MAX_CONCURRENT_POSITIONS = 5 
                CONFIDENCE_THRESHOLD_FOR_MAX_ALLOC = 0.85 
                CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC = 0.60 
                BASE_ALLOCATION_PCT_OF_TOTAL_CAPITAL = 0.10 

                allocated_capital_this_cycle = 0.0
                
                for asset_key in candidate_assets:
                    if len(investment_decisions) >= MAX_CONCURRENT_POSITIONS:
                        logger.info(f"BG TASK [{rnn_tx_id}]: Limite de posições concorrentes ({MAX_CONCURRENT_POSITIONS}) atingido.")
                        break
                    if allocated_capital_this_cycle >= amount * 0.90:
                        logger.info(f"BG TASK [{rnn_tx_id}]: Limite de capital do ciclo atingido.")
                        break

                    asset_symbol = asset_key.replace("_", "/")
                    logger.info(f"BG TASK [{rnn_tx_id}]: RNN avaliando ativo: {asset_symbol}")
                    
                    signal, confidence_prob = await predictor.predict_for_asset(
                        crypto_data_for_rnn[asset_key], 
                        loop=loop
                        # window_size e expected_features serão os defaults de rnn_predictor.py
                        # ou podem ser passados explicitamente se você quiser variar por ativo
                    )

                    if signal == 1: 
                        if confidence_prob is None or confidence_prob < CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC:
                            logger.info(f"BG TASK [{rnn_tx_id}]: Sinal COMPRA para {asset_symbol} mas confiança ({confidence_prob}) abaixo do mínimo {CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC}. Pulando.")
                            continue

                        confidence_factor = 0.5 
                        if confidence_prob >= CONFIDENCE_THRESHOLD_FOR_MAX_ALLOC:
                            confidence_factor = 1.0
                        elif confidence_prob > CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC: 
                            confidence_factor = 0.5 + 0.5 * (
                                (confidence_prob - CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC) /
                                (CONFIDENCE_THRESHOLD_FOR_MAX_ALLOC - CONFIDENCE_THRESHOLD_FOR_MIN_ALLOC)
                            )
                        
                        potential_usd_allocation = amount * BASE_ALLOCATION_PCT_OF_TOTAL_CAPITAL * confidence_factor
                        potential_usd_allocation = min(potential_usd_allocation, amount * MAX_RISK_PER_ASSET_PCT)
                        remaining_capital_for_cycle = amount - allocated_capital_this_cycle # Recalcula a cada iteração
                        actual_usd_allocation = min(potential_usd_allocation, remaining_capital_for_cycle)

                        if actual_usd_allocation < MIN_USD_PER_ORDER:
                            logger.info(f"BG TASK [{rnn_tx_id}]: Alocação calculada ({actual_usd_allocation:.2f}) para {asset_symbol} abaixo do mínimo ({MIN_USD_PER_ORDER}). Pulando.")
                            continue
                        
                        investment_decisions.append({
                            "asset_id": asset_symbol, "type": "CRYPTO", "action": "BUY",
                            "target_usd_amount": round(actual_usd_allocation, 2),
                            "rnn_confidence": round(confidence_prob, 4) if confidence_prob is not None else None,
                            "reasoning": f"RNN signal BUY for {asset_symbol} with confidence {confidence_prob:.2f}"
                        })
                        allocated_capital_this_cycle += round(actual_usd_allocation, 2)
                        logger.info(f"BG TASK [{rnn_tx_id}]: Decisão: COMPRAR {actual_usd_allocation:.2f} USD de {asset_symbol} (Conf: {confidence_prob:.2f})")
                    
                    elif signal == 0: 
                        logger.info(f"BG TASK [{rnn_tx_id}]: RNN sinal NÃO COMPRAR para {asset_symbol} (Conf: {confidence_prob:.2f if confidence_prob is not None else 'N/A'})")
                    else: 
                        logger.warning(f"BG TASK [{rnn_tx_id}]: RNN não gerou sinal para {asset_symbol}.")
                
                if not investment_decisions:
                    logger.info(f"BG TASK [{rnn_tx_id}]: RNN não gerou decisões de COMPRA válidas após avaliação e alocação.")
            
            except Exception as e: # Captura exceções da lógica da RNN
                logger.error(f"BG TASK [{rnn_tx_id}]: Erro CRÍTICO durante análise/predição RNN: {str(e)}", exc_info=True)
                rnn_analysis_success = False # Marca que a análise RNN falhou
                error_details += f"Critical RNN analysis/prediction error: {str(e)}; "
        
        if not rnn_analysis_success: # Se a flag foi setada para False
            final_status = "failed_rnn_analysis" 
        
        transactions_db[rnn_tx_id]["rnn_decisions"] = investment_decisions
    
    total_usd_allocated_by_rnn = allocated_capital_this_cycle 
    transactions_db[rnn_tx_id]["status_details"] = "Preparing to execute orders"

   
   

        # =========================================================================
    # 3. EXECUÇÃO DE ORDENS (Só executa se a RNN não falhou e gerou ordens)
    # =========================================================================
    executed_trades_info: List[Dict[str, Any]] = []
    current_portfolio_value = 0.0  # Valor dos ativos comprados, baseado no custo
    cash_remaining_after_execution = amount  # Começa com todo o montante
    if final_status == "completed" and investment_decisions and exchange:
        logger.info(f"BG TASK [{rnn_tx_id}]: Executando {len(investment_decisions)} ordens...")
        transactions_db[rnn_tx_id]["status_details"] = "Executing investment orders"
        order_execution_overall_success = True

        for decision in investment_decisions:
            if decision.get("action") == "BUY" and decision.get("type") == "CRYPTO":
                asset_symbol = decision["asset_id"]
                usd_to_spend = decision["target_usd_amount"]

                try:
                    # 1. Obter preço atual (ticker)
                    ticker = await exchange.fetch_ticker(asset_symbol)
                    current_price = ticker["last"] or ticker["close"]
                    if not current_price:
                        raise ValueError("Preço atual não disponível")

                    # 2. Calcular quantidade de ativo
                    amount_of_asset = usd_to_spend / current_price

                    # 3. Verificar precisão e quantidade mínima da exchange
                    market = exchange.market(asset_symbol)
                    precision_amount = market["precision"]["amount"]
                    limits = market["limits"]
                    min_order = limits["amount"]["min"]

                    if amount_of_asset < min_order:
                        logger.warning(
                            f"BG TASK [{rnn_tx_id}]: Ordem para {asset_symbol} abaixo do mínimo ({min_order}). Pulando."
                        )
                        continue

                    amount_of_asset = round(amount_of_asset, precision_amount)

                    # 4. Criar ordem de mercado
                    logger.info(
                        f"BG TASK [{rnn_tx_id}]: Criando ordem de compra para {amount_of_asset} {asset_symbol.split('/')[0]}..."
                    )
                    order = await exchange.create_market_buy_order(
                        symbol=asset_symbol,
                        amount=amount_of_asset
                    )

                    # 5. Extrair dados da ordem
                    filled = order.get("filled", 0)
                    cost = order.get("cost", 0)  # USD gasto
                    average = order.get("average", current_price)
                    fees = 0.0
                    fee_info = order.get("fees", [])
                    if fee_info:
                        for fee in fee_info:
                            if fee.get("currency") == "USDT":
                                fees += fee.get("cost", 0)

                    # 6. Atualizar valores
                    if cost > cash_remaining_after_execution:
                        logger.warning(
                            f"BG TASK [{rnn_tx_id}]: Saldo insuficiente para ordem de {asset_symbol}."
                        )
                        continue

                    cash_remaining_after_execution -= cost
                    current_portfolio_value += cost

                    # 7. Registrar trade
                    executed_trades_info.append({
                        "asset_id": asset_symbol,
                        "order_id_exchange": order["id"],
                        "type": "market",
                        "side": "buy",
                        "requested_usd_amount": usd_to_spend,
                        "asset_quantity_ordered": amount_of_asset,
                        "filled_quantity": filled,
                        "average_fill_price": round(average, 6),
                        "status_from_exchange": order["status"],
                        "cost_in_usd": round(cost, 2),
                        "fees_paid": round(fees, 4),
                        "timestamp": order["timestamp"],
                        "exchange_order_response": {k: v for k, v in order.items() if k not in ["info", "trades"]}
                    })

                    logger.info(
                        f"BG TASK [{rnn_tx_id}]: Ordem executada com sucesso para {asset_symbol}. "
                        f"Custo: {cost:.2f} USDT, Preço médio: {average:.4f}"
                    )

                except Exception as e:
                    logger.error(
                        f"BG TASK [{rnn_tx_id}]: Falha ao executar ordem para {asset_symbol}: {str(e)}"
                    )
                    executed_trades_info.append({
                        "asset_id": asset_symbol,
                        "error": str(e),
                        "requested_usd_amount": usd_to_spend,
                        "status": "failed"
                    })
                    order_execution_overall_success = False

        if not order_execution_overall_success:
            error_details += "One or more orders failed during execution; "
            # final_status = "completed_with_partial_failure"  # Descomente se quiser um status intermediário

    elif not exchange and investment_decisions:
        logger.warning(
            f"BG TASK [{rnn_tx_id}]: Decisões geradas, mas exchange não disponível para execução."
        )
        error_details += "Exchange not available for order execution; "
        final_status = "failed_order_execution"
        cash_remaining_after_execution = amount


    # =========================================================================
    # 4. SIMULAÇÃO DO PERÍODO DE INVESTIMENTO E CÁLCULO DE LUCRO/PERDA (Só se não houve falha crítica antes)
    # =========================================================================
    value_of_investments_at_eod = current_portfolio_value  # Começa com o valor de custo

    if final_status == "completed":  # Ou "completed_with_partial_failure"
        transactions_db[rnn_tx_id]["status_details"] = "Simulating EOD valuation"
        logger.info(f"BG TASK [{rnn_tx_id}]: Simulando valorização do portfólio no final do dia com base em dados de mercado...")

        if current_portfolio_value > 0 and executed_trades_info:
            # --- Coletar preços iniciais (de quando a ordem foi executada) ---
            # Precisamos dos preços de entrada para cada ativo
            asset_entry_prices = {}
            for trade in executed_trades_info:
                if trade.get("side") == "buy" and trade.get("status_from_exchange") == "filled":
                    asset_id = trade["asset_id"]
                    avg_price = trade.get("average_fill_price")
                    if avg_price:
                        asset_entry_prices[asset_id] = avg_price

            if not asset_entry_prices:
                logger.warning(f"BG TASK [{rnn_tx_id}]: Não foi possível obter preços de entrada para os ativos. Usando simulação genérica.")
                actual_daily_return_on_portfolio = random.uniform(-0.03, 0.05)
                profit_or_loss_on_portfolio = current_portfolio_value * actual_daily_return_on_portfolio
                value_of_investments_at_eod = current_portfolio_value + profit_or_loss_on_portfolio
            else:
                # --- Obter preços finais (fechamento simulado) ---
                # Vamos usar os dados de mercado coletados e simular um movimento plausível
                simulated_final_prices = {}
                overall_market_trend = 0.0  # Baseado no BTC
                btc_data = market_data_results["crypto"].get("BTC/USDT")
                if btc_data and "ohlcv_1h" in btc_data:
                    ohlcv = btc_data["ohlcv_1h"]
                    if len(ohlcv) >= 2:
                        close_open = ohlcv[0][4]  # Preço de fechamento da 1ª vela (mais antiga)
                        close_recent = ohlcv[-1][4]  # Preço de fechamento da última vela
                        overall_market_trend = (close_recent - close_open) / close_open
                        logger.info(f"BG TASK [{rnn_tx_id}]: Tendência do mercado (BTC): {overall_market_trend*100:.2f}%")
                else:
                    # Tendência de mercado genérica
                    overall_market_trend = random.uniform(-0.02, 0.03)

                # Simular preços finais para cada ativo no portfólio
                for asset_id, entry_price in asset_entry_prices.items():
                    # Coeficientes de risco (volatilidade relativa ao BTC)
                    risk_coefficients = {
                        "BTC/USDT": 1.0,
                        "ETH/USDT": 1.2,
                        "SOL/USDT": 1.8,
                        "ADA/USDT": 2.0,
                        "DOGE/USDT": 2.5
                    }
                    risk_coeff = risk_coefficients.get(asset_id, 1.5)  # Padrão: 1.5

                    # Volatilidade diária baseada no coeficiente de risco
                    daily_volatility = risk_coeff * 0.05  # Escala baseada no BTC (~5% diário)

                    # Retorno esperado: tendência do mercado + ruído aleatório
                    # O ruído é proporcional à volatilidade
                    noise = random.gauss(0, daily_volatility)  # Distribuição normal
                    asset_daily_return = overall_market_trend * risk_coeff + noise

                    # Limitar extremos (ex: -90% a +100% por dia é irreal)
                    asset_daily_return = max(-0.5, min(asset_daily_return, 1.0))

                    # Calcular preço final simulado
                    simulated_final_price = entry_price * (1 + asset_daily_return)
                    simulated_final_prices[asset_id] = simulated_final_price

                    logger.info(f"BG TASK [{rnn_tx_id}]: {asset_id} | Preço entrada: {entry_price:.6f} | Retorno simulado: {asset_daily_return*100:.2f}% | Preço final: {simulated_final_price:.6f}")

                # --- Calcular valor final do portfólio ---
                value_of_investments_at_eod = 0.0
                for trade in executed_trades_info:
                    if trade.get("side") == "buy" and trade.get("status_from_exchange") == "filled":
                        asset_id = trade["asset_id"]
                        quantity = trade.get("filled_quantity", 0)
                        if asset_id in simulated_final_prices and quantity > 0:
                            final_value = quantity * simulated_final_prices[asset_id]
                            value_of_investments_at_eod += final_value
                        else:
                            # Se não conseguimos simular o preço, use o valor de custo (sem ganho/perda)
                            value_of_investments_at_eod += trade.get("cost_in_usd", 0)

                # Calcular P&L total do portfólio
                profit_or_loss_on_portfolio = value_of_investments_at_eod - current_portfolio_value

                logger.info(f"BG TASK [{rnn_tx_id}]: Portfólio inicial: {current_portfolio_value:.2f}, "
                            f"Lucro/Prejuízo: {profit_or_loss_on_portfolio:.2f}, "
                            f"Valor final do portfólio: {value_of_investments_at_eod:.2f}")
        else:
            logger.info(f"BG TASK [{rnn_tx_id}]: Nenhum portfólio para valorizar no EOD (nada foi comprado).")
            value_of_investments_at_eod = 0.0

        # O calculated_final_amount é o valor dos investimentos liquidados + o caixa que não foi usado
        calculated_final_amount = value_of_investments_at_eod + cash_remaining_after_execution

    else:  # Se houve falha antes, o valor final é o que sobrou após a falha
        calculated_final_amount = cash_remaining_after_execution + current_portfolio_value  # current_portfolio_value pode ser 0 ou parcial
        logger.warning(f"BG TASK [{rnn_tx_id}]: Ciclo de investimento não concluído normalmente ({final_status}). Valor final baseado no estado atual.")

    transactions_db[rnn_tx_id]["eod_portfolio_value_simulated"] = round(value_of_investments_at_eod, 2)
    transactions_db[rnn_tx_id]["final_calculated_amount"] = round(calculated_final_amount, 2)

       # =========================================================================
    # 5. TOKENIZAÇÃO / REGISTRO DA OPERAÇÃO (Só se não houve falha crítica antes)
    # =========================================================================
    if final_status not in ["failed_config", "failed_market_data", "failed_rnn_analysis"]:
        transactions_db[rnn_tx_id]["status_details"] = "Finalizing transaction log (tokenization)"
        logger.info(f"BG TASK [{rnn_tx_id}]: Iniciando tokenização segura da operação...")

        # --- Coleta completa de dados da transação ---
        full_transaction_data = {
            "rnn_transaction_id": rnn_tx_id,
            "aibank_transaction_token": aibank_tx_token,
            "client_id": client_id,
            "initial_amount_usd": amount,
            "final_amount_usd": calculated_final_amount,
            "profit_loss_usd": round(calculated_final_amount - amount, 2),
            "status": final_status,
            "timestamp": datetime.utcnow().isoformat(),
            "market_data_collected": market_data_results,
            "rnn_decisions": investment_decisions,
            "executed_trades": executed_trades_info,
            "portfolio_value_after_execution_usd": current_portfolio_value,
            "cash_remaining_after_execution_usd": cash_remaining_after_execution,
            "eod_portfolio_value_simulated_usd": value_of_investments_at_eod,
            "execution_summary": {
                "total_trades": len(executed_trades_info),
                "successful_trades": len([t for t in executed_trades_info if t.get("status_from_exchange") == "filled"]),
                "failed_trades": len([t for t in executed_trades_info if t.get("error")]),
                "total_fees_paid_usd": sum(t.get("fees_paid", 0) for t in executed_trades_info)
            }
        }

        # --- Gera hash criptográfico (SHA-256) dos dados ---
        # Garante integridade e imutabilidade
        ordered_data_str = json.dumps(full_transaction_data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        proof_hash = hashlib.sha256(ordered_data_str.encode('utf-8')).hexdigest()

        # --- Assinatura digital (prova de autoria) ---
        # Simula uma assinatura com uma chave privada (em produção: use uma wallet real)
        # Em produção, use web3.eth.account.sign_message() com uma chave segura
        try:
            private_key = os.environ.get("SIGNING_PRIVATE_KEY")  # Chave para assinar operações
            if private_key:
                # Simulando assinatura (em produção, use web3.py)
                message_to_sign = f"ATCoin-Neural-Proof:{proof_hash}"
                signature = hmac.new(
                    private_key.encode('utf-8'),
                    message_to_sign.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                logger.info(f"BG TASK [{rnn_tx_id}]: Operação assinada digitalmente (HMAC).")
            else:
                signature = None
                logger.warning(f"BG TASK [{rnn_tx_id}]: Chave de assinatura não configurada. Assinatura omitida.")
        except Exception as e:
            logger.error(f"BG TASK [{rnn_tx_id}]: Falha ao assinar operação: {str(e)}")
            signature = None

        # --- Armazenamento no banco de dados (simulado) --- Atlas Mongo
        # Em produção: use MongoDB, PostgreSQL, ou sistema de log imutável
        transactions_db[rnn_tx_id]["proof_of_operation_token"] = proof_hash
        transactions_db[rnn_tx_id]["operation_signature"] = signature
        transactions_db[rnn_tx_id]["tokenization_method"] = "sha256_internal_hash_with_hmac"
        transactions_db[rnn_tx_id]["full_transaction_data"] = full_transaction_data  # Ou armazene em DB externo

        # --- (OPCIONAL) Registro em Blockchain (Ethereum-like) ---
        # Em produção, use web3.py para interagir com um contrato ERC-721 ou ERC-1155
        # Exemplo de metadados para NFT:
        nft_metadata = {
            "name": f"ATCoin Neural Trade #{rnn_tx_id[:8]}",
            "description": "Comprovante de operação de trading algorítmico com IA RNN",
            "image": "https://aibank.app.br/assets/atcoin-nft.png",
            "attributes": [
                {"trait_type": "Cliente", "value": client_id},
                {"trait_type": "Montante Inicial", "value": f"{amount:.2f} USDT"},
                {"trait_type": "Retorno", "value": f"{calculated_final_amount - amount:.2f} USDT"},
                {"trait_type": "Status", "value": final_status},
                {"trait_type": "Data", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
            ]
        }

        # Simulação de mint de NFT
        blockchain_tx_hash = None
        if os.environ.get("ENABLE_BLOCKCHAIN_RECORD", "false").lower() == "true":
            try:
                logger.info(f"BG TASK [{rnn_tx_id}]: Registrando operação na blockchain (simulado)...")
                # Em produção: chame web3.py para mintar um NFT
                blockchain_tx_hash = f"0x{uuid.uuid4().hex[:64]}"  # Simulado
                logger.info(f"BG TASK [{rnn_tx_id}]: NFT de operação registrado na blockchain. TX: {blockchain_tx_hash}")
            except Exception as e:
                logger.error(f"BG TASK [{rnn_tx_id}]: Falha ao registrar na blockchain: {str(e)}")
        else:
            logger.info(f"BG TASK [{rnn_tx_id}]: Registro em blockchain desativado.")

        # --- Armazenar hash da blockchain ---
        transactions_db[rnn_tx_id]["blockchain_tx_hash"] = blockchain_tx_hash

        # --- Finalizar ---
        await asyncio.sleep(0.5)
        logger.info(f"BG TASK [{rnn_tx_id}]: Tokenização concluída. Prova: {proof_hash[:10]}... | NFT: {blockchain_tx_hash[:10] if blockchain_tx_hash else 'N/A'}")

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
    app.mount("/static", StaticFiles(directory="./static"), name="static")
    # ✅ Correção: use 'templates' (com 's') e armazene o template carregado
    env = Environment(loader=FileSystemLoader("./templates"))
    template = env.get_template("dashboard.html")  # Carrega o template específico
    logger.info("✅ Templates e arquivos estáticos carregados com sucesso.")
except Exception as e:
    logger.error(f"❌ Falha ao carregar templates ou arquivos estáticos: {e}")
    template = None  # Para evitar erros posteriores

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not template:
        logger.warning("⚠️ Template não disponível. Retornando erro de dashboard.")
        return HTMLResponse(
            content="<h1>Dashboard Indisponível</h1><p>Erro ao carregar o template.</p>",
            status_code=500
        )
    try:
        # ✅ Usa o template carregado
        content = template.render(request=request)
        return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"❌ Erro ao renderizar o template: {e}")
        return HTMLResponse(
            content="<h1>Erro Interno</h1><p>Falha ao renderizar a página.</p>",
            status_code=500
        )


@app.get("/api/transactions/recent")
async def get_recent_transactions():
    # Retorna as últimas 10 transações
    recent = list(transactions_db.values())[-10:]
    return {"transactions": recent}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "template_loaded": template is not None}


    # --- Imports para Background Task ---
import asyncio
import random


# --- Execução direta para HF Spaces ---
if __name__ == "__main__":
    import uvicorn
    logger.info("🔥 Iniciando servidor Uvicorn...")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        reload=False,  # Nunca True no HF
        log_level="info"
    )