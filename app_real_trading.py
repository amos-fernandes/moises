"""
App Principal Integrado - Equilibrada_Pro + Trading Real Binance
Sistema completo para operações reais com suas credenciais
"""

import sys
import os
import uuid
import hmac
import hashlib
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports FastAPI
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

# Imports locais
from src.utils.logger import get_logger
from src.trading.binance_real_trading import BinanceRealTrading
from contextlib import asynccontextmanager

# Inicializa logger
logger = get_logger()

# Configurações de ambiente
TRADING_MODE = os.getenv('TRADING_MODE', 'REAL')
AIBANK_API_KEY = os.getenv("AIBANK_API_KEY")
AIBANK_CALLBACK_URL = os.getenv("AIBANK_CALLBACK_URL") 
CALLBACK_SHARED_SECRET = os.getenv("CALLBACK_SHARED_SECRET")
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8000))

# Lifespan com Trading Real
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa sistema de trading real"""
    logger.info(f"🚀 Iniciando ATCoin REAL TRADING - Mode: {TRADING_MODE}")
    
    try:
        # Inicializa sistema de trading real
        real_trading = BinanceRealTrading()
        success = await real_trading.initialize()
        
        if success:
            app.state.real_trading = real_trading
            logger.info("✅ Sistema de Trading Real inicializado!")
            logger.info("💰 Binance conectada - pronto para operações reais")
        else:
            logger.error("❌ Falha ao inicializar trading real")
            app.state.real_trading = None
            
    except Exception as e:
        logger.error(f"❌ Erro crítico na inicialização: {e}")
        app.state.real_trading = None
    
    yield
    
    # Cleanup
    if hasattr(app.state, 'real_trading') and app.state.real_trading:
        if app.state.real_trading.exchange:
            await app.state.real_trading.exchange.close()
    
    logger.info("🔚 Sistema finalizado")

# FastAPI App
fastapi_app = FastAPI(
    title="ATCoin Real Trading - Equilibrada_Pro",
    description="Sistema de trading real na Binance com estratégia Equilibrada_Pro",
    version="3.0.0-real-trading",
    lifespan=lifespan
)

# CORS
cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arquivos estáticos
try:
    fastapi_app.mount("/static", StaticFiles(directory="./static"), name="static")
    env = Environment(loader=FileSystemLoader("./templates"))
    template = env.get_template("dashboard.html")
    logger.info("✅ Templates carregados")
except Exception as e:
    logger.warning(f"⚠️ Templates não encontrados: {e}")
    template = None

# Database de transações
transactions_db: Dict[str, Dict[str, Any]] = {}

# Modelos
class RealInvestmentRequest(BaseModel):
    client_id: str
    amount_brl: float  # Valor em reais
    aibank_transaction_token: str
    risk_level: str = "medium"  # low, medium, high

class InvestmentResponse(BaseModel):
    status: str
    message: str
    rnn_transaction_id: str
    trading_mode: str

class RealInvestmentResultPayload(BaseModel):
    rnn_transaction_id: str
    aibank_transaction_token: str
    client_id: str
    initial_amount_brl: float
    initial_amount_usd: float
    final_amount_usd: float
    profit_loss_usd: float
    profit_loss_brl: float
    trades_executed: List[Dict[str, Any]]
    status: str
    timestamp: datetime
    details: str = ""

# Lógica de negócio com trading real
async def execute_real_investment_strategy_background(
    rnn_tx_id: str, 
    client_id: str, 
    amount_brl: float, 
    aibank_tx_token: str,
    risk_level: str = "medium"
):
    """Executa estratégia com dinheiro real na Binance"""
    
    logger.info(f"🚀 REAL TRADING [{rnn_tx_id}]: Iniciando com R$ {amount_brl:.2f}")
    transactions_db[rnn_tx_id]["status"] = "processing"
    transactions_db[rnn_tx_id]["trading_mode"] = "REAL"
    
    real_trading = getattr(fastapi_app.state, 'real_trading', None)
    if not real_trading:
        logger.error(f"❌ [{rnn_tx_id}]: Sistema de trading real não inicializado")
        transactions_db[rnn_tx_id]["status"] = "failed"
        transactions_db[rnn_tx_id]["error"] = "Sistema não inicializado"
        return
    
    final_status = "completed"
    error_details = ""
    final_amount_usd = 0.0
    initial_amount_usd = 0.0
    trades_executed = []
    
    try:
        # Executa estratégia real
        result = await real_trading.run_equilibrada_strategy_real(amount_brl)
        
        if result['success']:
            initial_amount_usd = result.get('initial_amount_usd', 0)
            trades_executed = result.get('trades', [])
            
            # Calcula saldo final (simplificado)
            successful_trades = [t for t in trades_executed if t.get('success')]
            if successful_trades:
                # Simula valor final baseado nos trades
                total_pnl = result.get('total_pnl_usd', 0)
                final_amount_usd = initial_amount_usd + total_pnl
            else:
                final_amount_usd = initial_amount_usd
            
            logger.info(f"✅ [{rnn_tx_id}]: Trading concluído - {len(successful_trades)} trades")
            
        else:
            raise Exception(result.get('error', 'Erro desconhecido na execução'))
            
    except Exception as e:
        logger.error(f"❌ [{rnn_tx_id}]: Erro no trading real: {e}")
        final_status = "failed" 
        error_details = str(e)
        
        # Em caso de erro, tenta converter valor original
        try:
            initial_amount_usd = await real_trading.convert_brl_to_usd(amount_brl)
            final_amount_usd = initial_amount_usd  # Sem alteração em caso de erro
        except:
            initial_amount_usd = amount_brl / 5.0  # Taxa aproximada
            final_amount_usd = initial_amount_usd
    
    # Converte resultado para BRL
    try:
        # Taxa aproximada USD->BRL (invertida)
        usd_brl_rate = 5.0
        final_amount_brl = final_amount_usd * usd_brl_rate
        profit_loss_brl = final_amount_brl - amount_brl
    except:
        final_amount_brl = amount_brl
        profit_loss_brl = 0.0
    
    # Atualiza transação
    transactions_db[rnn_tx_id].update({
        "status": final_status,
        "initial_amount_brl": amount_brl,
        "initial_amount_usd": initial_amount_usd,
        "final_amount_usd": final_amount_usd,
        "final_amount_brl": final_amount_brl,
        "profit_loss_usd": final_amount_usd - initial_amount_usd,
        "profit_loss_brl": profit_loss_brl,
        "trades_count": len(trades_executed),
        "successful_trades": len([t for t in trades_executed if t.get('success')]),
        "error_details": error_details
    })
    
    # Envia callback
    callback_payload = RealInvestmentResultPayload(
        rnn_transaction_id=rnn_tx_id,
        aibank_transaction_token=aibank_tx_token,
        client_id=client_id,
        initial_amount_brl=amount_brl,
        initial_amount_usd=initial_amount_usd,
        final_amount_usd=final_amount_usd,
        profit_loss_usd=final_amount_usd - initial_amount_usd,
        profit_loss_brl=profit_loss_brl,
        trades_executed=trades_executed,
        status=final_status,
        timestamp=datetime.utcnow(),
        details=error_details or f"Real trading completed - {len(trades_executed)} trades executed"
    )
    
    await _send_callback_to_aibank(callback_payload)
    transactions_db[rnn_tx_id]["callback_status"] = "sent"
    
    logger.info(f"🏁 [{rnn_tx_id}]: Ciclo concluído - Status: {final_status}")

async def _send_callback_to_aibank(payload_data: RealInvestmentResultPayload):
    """Envia callback para AIBank"""
    if not AIBANK_CALLBACK_URL or not CALLBACK_SHARED_SECRET:
        logger.error("❌ Configuração de callback ausente")
        return
    
    try:
        payload_json_str = payload_data.model_dump_json()
        signature = hmac.new(
            CALLBACK_SHARED_SECRET.encode('utf-8'), 
            payload_json_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json', 
            'X-RNN-Signature': signature
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(AIBANK_CALLBACK_URL, content=payload_json_str, headers=headers)
            response.raise_for_status()
            logger.info(f"✅ Callback enviado: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Erro no callback: {e}")

# Dependências
async def verify_aibank_key(authorization: str = Header(None)):
    """Verifica chave API"""
    if not AIBANK_API_KEY:
        logger.warning("⚠️ AIBANK_API_KEY não configurada")
        return True
    if authorization != f"Bearer {AIBANK_API_KEY}":
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return True

# Endpoints principais
@fastapi_app.post("/api/invest/real", response_model=InvestmentResponse, dependencies=[Depends(verify_aibank_key)])
async def initiate_real_investment(request_data: RealInvestmentRequest, background_tasks: BackgroundTasks):
    """
    🔥 ENDPOINT PRINCIPAL - TRADING REAL
    Executa investimentos reais na Binance com Equilibrada_Pro
    """
    logger.info(f"🔥 REAL TRADING: Cliente {request_data.client_id}, R$ {request_data.amount_brl:.2f}")
    
    # Verifica sistema
    real_trading = getattr(fastapi_app.state, 'real_trading', None)
    if not real_trading:
        raise HTTPException(status_code=503, detail="Sistema de trading real não inicializado")
    
    # Verifica valor mínimo
    if request_data.amount_brl < 100.0:
        raise HTTPException(status_code=400, detail="Valor mínimo: R$ 100,00")
    
    # Cria transação
    rnn_tx_id = str(uuid.uuid4())
    transactions_db[rnn_tx_id] = {
        "status": "pending",
        "received_at": datetime.utcnow().isoformat(),
        "client_id": request_data.client_id,
        "amount_brl": request_data.amount_brl,
        "risk_level": request_data.risk_level,
        "trading_mode": "REAL",
        "strategy": "Equilibrada_Pro"
    }
    
    # Executa em background
    background_tasks.add_task(
        execute_real_investment_strategy_background,
        rnn_tx_id,
        request_data.client_id,
        request_data.amount_brl,
        request_data.aibank_transaction_token,
        request_data.risk_level
    )
    
    return InvestmentResponse(
        status="pending",
        message=f"Real investment of R$ {request_data.amount_brl:.2f} initiated. Real trading in progress...",
        rnn_transaction_id=rnn_tx_id,
        trading_mode="REAL"
    )

# Compatibilidade com endpoint antigo
@fastapi_app.post("/api/invest", response_model=InvestmentResponse, dependencies=[Depends(verify_aibank_key)])
async def initiate_investment_compatibility(request_data: RealInvestmentRequest, background_tasks: BackgroundTasks):
    """Endpoint de compatibilidade - redireciona para trading real"""
    return await initiate_real_investment(request_data, background_tasks)

@fastapi_app.get("/api/transaction_status/{rnn_tx_id}", response_class=JSONResponse)
async def get_transaction_status(rnn_tx_id: str):
    """Status da transação"""
    transaction = transactions_db.get(rnn_tx_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@fastapi_app.get("/health")
async def health_check():
    """Health check com informações de trading real"""
    real_trading_loaded = getattr(fastapi_app.state, 'real_trading', None) is not None
    
    health_info = {
        "status": "healthy" if real_trading_loaded else "degraded",
        "trading_mode": TRADING_MODE,
        "real_trading_system": real_trading_loaded,
        "strategy": "Equilibrada_Pro",
        "exchange": "Binance",
        "features": {
            "brl_usd_conversion": True,
            "real_orders": True,
            "risk_management": True,
            "automated_trading": True
        },
        "performance": {
            "expected_return": "+1.24%",
            "strategy_win_rate": "32.1%",
            "profit_factor": "1.05"
        },
        "transactions_count": len(transactions_db),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Adiciona informações da Binance se conectada
    if real_trading_loaded:
        try:
            real_trading = fastapi_app.state.real_trading
            if real_trading.initialized:
                health_info["binance_connected"] = True
                health_info["testnet_mode"] = real_trading.testnet
            else:
                health_info["binance_connected"] = False
        except:
            health_info["binance_connected"] = False
    
    return health_info

@fastapi_app.get("/api/binance/balance")
async def get_binance_balance():
    """Consulta saldo na Binance"""
    real_trading = getattr(fastapi_app.state, 'real_trading', None)
    if not real_trading or not real_trading.initialized:
        raise HTTPException(status_code=503, detail="Binance não conectada")
    
    try:
        balance = await real_trading.exchange.fetch_balance()
        
        # Filtra apenas saldos relevantes
        relevant_balances = {}
        for currency, data in balance.items():
            if isinstance(data, dict) and data.get('free', 0) > 0:
                relevant_balances[currency] = {
                    'free': data['free'],
                    'used': data.get('used', 0),
                    'total': data.get('total', 0)
                }
        
        return {
            "balances": relevant_balances,
            "timestamp": datetime.utcnow().isoformat(),
            "exchange": "Binance",
            "testnet": real_trading.testnet
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar saldo: {str(e)}")

@fastapi_app.get("/api/transactions/recent")
async def get_recent_transactions():
    """Transações recentes"""
    recent_keys = list(transactions_db.keys())[-10:]
    recent_transactions = [transactions_db[key] for key in recent_keys]
    return {
        "transactions": recent_transactions, 
        "trading_mode": TRADING_MODE,
        "strategy": "Equilibrada_Pro"
    }

@fastapi_app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal"""
    if not template:
        return HTMLResponse(
            "<h1>ATCoin Real Trading Dashboard</h1>"
            f"<p>Trading Mode: {TRADING_MODE}</p>"
            "<p>Sistema de trading real ativo!</p>", 
            status_code=200
        )
    return HTMLResponse(template.render(request=request))

if __name__ == "__main__":
    print(f"🚀 Iniciando ATCoin Real Trading System")
    print(f"💰 Mode: {TRADING_MODE}")
    print(f"🌐 Host: {HOST}:{PORT}")
    print(f"⚠️  ATENÇÃO: SISTEMA COM DINHEIRO REAL!")
    
    uvicorn.run(
        fastapi_app, 
        host=HOST, 
        port=PORT,
        workers=1,  # Importante: apenas 1 worker para manter state
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )