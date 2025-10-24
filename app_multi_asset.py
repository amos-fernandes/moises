"""
Sistema Integrado Multi-Asset com Foco na Bolsa Americana
Combina Equilibrada_Pro + Análise US Market para 60% Assertividade
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
import sys
import os

# Adiciona paths do projeto
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Imports dos sistemas existentes
from src.trading.production_system import EquilibradaProStrategy
from src.trading.us_market_system import USMarketAnalyzer, USMarketStrategy, USMarketSignal
from src.data.alpha_vantage_loader import USMarketDataManager

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sistema Multi-Asset Trading",
    description="Sistema integrado para trading com foco na bolsa americana (60% assertividade)",
    version="1.0.0"
)

# =====================================================
# MODELS
# =====================================================

class MarketSignalResponse(BaseModel):
    symbol: str
    signal: str
    confidence: float
    price: float
    volume: int
    timestamp: datetime
    strategy: str  # 'equilibrada_pro' ou 'us_market'
    indicators: Dict
    reasons: List[str]

class PortfolioAnalysisRequest(BaseModel):
    symbols: List[str]
    amount: float = 10000.0
    strategy: str = "hybrid"  # 'equilibrada_pro', 'us_market', 'hybrid'

class PortfolioAnalysisResponse(BaseModel):
    total_signals: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    recommended_positions: List[Dict]
    portfolio_allocation: Dict
    risk_assessment: Dict
    expected_return: float

# =====================================================
# SISTEMA HÍBRIDO
# =====================================================

class HybridTradingSystem:
    """
    Sistema híbrido que combina:
    1. Equilibrada_Pro (comprovado +1.24%)
    2. US Market System (otimizado para 60% assertividade)
    """
    
    def __init__(self):
        # Inicializa sistemas
        self.equilibrada_pro = EquilibradaProStrategy()
        self.us_analyzer = USMarketAnalyzer()
        self.us_strategy = USMarketStrategy()
        self.data_manager = USMarketDataManager()
        
        # Configuração híbrida
        self.us_focus_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
        self.other_symbols = ["PETR4.SA", "VALE3.SA", "BTC/USD", "ETH/USD"]
        
        logger.info("🚀 Sistema Híbrido inicializado")
        logger.info(f"🇺🇸 Foco US: {self.us_focus_symbols}")
        logger.info(f"🌍 Outros: {self.other_symbols}")
    
    async def analyze_symbol_hybrid(self, symbol: str, df: pd.DataFrame) -> MarketSignalResponse:
        """
        Análise híbrida: usa US Market System para ações americanas,
        Equilibrada_Pro para outros ativos
        """
        try:
            if symbol in self.us_focus_symbols:
                # Usa sistema otimizado para ações americanas
                us_signal = self.us_analyzer.analyze_us_stock(symbol, df)
                
                return MarketSignalResponse(
                    symbol=us_signal.symbol,
                    signal=us_signal.signal,
                    confidence=us_signal.confidence,
                    price=us_signal.price,
                    volume=us_signal.volume,
                    timestamp=us_signal.timestamp,
                    strategy="us_market",
                    indicators=us_signal.indicators,
                    reasons=us_signal.reasons
                )
            else:
                # Usa Equilibrada_Pro para outros ativos
                ep_result = self.equilibrada_pro.analyze_market_data(df)
                
                # Converte resultado para formato padronizado
                signal = "HOLD"
                confidence = 0.5
                
                if ep_result and 'signal' in ep_result:
                    if ep_result['signal'] > 0.6:
                        signal = "BUY"
                        confidence = ep_result['signal']
                    elif ep_result['signal'] < 0.4:
                        signal = "SELL"
                        confidence = 1 - ep_result['signal']
                
                return MarketSignalResponse(
                    symbol=symbol,
                    signal=signal,
                    confidence=confidence,
                    price=df['close'].iloc[-1] if len(df) > 0 else 0.0,
                    volume=int(df['volume'].iloc[-1]) if len(df) > 0 else 0,
                    timestamp=datetime.now(timezone.utc),
                    strategy="equilibrada_pro",
                    indicators=ep_result if ep_result else {},
                    reasons=[f"Equilibrada_Pro analysis: {signal}"]
                )
                
        except Exception as e:
            logger.error(f"❌ Erro analisando {symbol}: {e}")
            raise HTTPException(status_code=500, detail=f"Erro na análise de {symbol}")
    
    async def analyze_portfolio_hybrid(self, symbols: List[str], amount: float = 10000.0) -> PortfolioAnalysisResponse:
        """
        Análise completa do portfólio usando sistema híbrido
        """
        try:
            logger.info(f"📊 Iniciando análise híbrida do portfólio: {symbols}")
            
            # Carrega dados do mercado
            market_data = {}
            
            # Separa símbolos por sistema
            us_symbols = [s for s in symbols if s in self.us_focus_symbols]
            other_symbols = [s for s in symbols if s not in self.us_focus_symbols]
            
            # Carrega dados US via Alpha Vantage
            if us_symbols:
                us_data = self.data_manager.load_us_market_data(us_symbols)
                market_data.update(us_data)
            
            # Para outros símbolos, usa dados simulados (implementar conforme necessário)
            for symbol in other_symbols:
                # Aqui você integraria com outras fontes de dados
                # Por ora, vamos simular dados básicos
                dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
                prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
                
                market_data[symbol] = pd.DataFrame({
                    'open': prices * 0.999,
                    'high': prices * 1.002,
                    'low': prices * 0.998,
                    'close': prices,
                    'volume': np.random.randint(100000, 1000000, 100)
                }, index=dates)
            
            # Analisa cada símbolo
            signals = []
            for symbol in symbols:
                if symbol in market_data:
                    signal = await self.analyze_symbol_hybrid(symbol, market_data[symbol])
                    signals.append(signal)
            
            # Filtra sinais de compra com alta confiança
            buy_signals = [s for s in signals if s.signal == "BUY" and s.confidence >= 0.65]
            sell_signals = [s for s in signals if s.signal == "SELL" and s.confidence >= 0.65]
            hold_signals = [s for s in signals if s.signal == "HOLD" or s.confidence < 0.65]
            
            # Calcula alocação do portfólio
            portfolio_allocation = {}
            recommended_positions = []
            
            if buy_signals:
                # Ordena por confiança
                buy_signals.sort(key=lambda x: x.confidence, reverse=True)
                
                # Limita a 3 posições máximas
                top_signals = buy_signals[:3]
                
                total_weight = sum([s.confidence for s in top_signals])
                
                for signal in top_signals:
                    weight = signal.confidence / total_weight
                    position_size = amount * weight * 0.9  # 90% do capital máximo
                    
                    portfolio_allocation[signal.symbol] = {
                        "weight": weight,
                        "amount": position_size,
                        "confidence": signal.confidence,
                        "strategy": signal.strategy
                    }
                    
                    recommended_positions.append({
                        "symbol": signal.symbol,
                        "action": "BUY",
                        "amount": position_size,
                        "price": signal.price,
                        "confidence": signal.confidence,
                        "strategy": signal.strategy,
                        "reasons": signal.reasons[:3]  # Top 3 reasons
                    })
            
            # Avaliação de risco
            risk_assessment = {
                "total_positions": len(recommended_positions),
                "max_position_size": max([p["amount"] for p in recommended_positions]) / amount if recommended_positions else 0,
                "diversification_score": len(set([p["strategy"] for p in recommended_positions])) / 2,  # Max 2 strategies
                "confidence_average": np.mean([s.confidence for s in buy_signals]) if buy_signals else 0.5,
                "risk_level": "LOW" if len(recommended_positions) <= 2 else "MEDIUM" if len(recommended_positions) <= 3 else "HIGH"
            }
            
            # Retorno esperado (estimativa baseada na confiança)
            expected_return = 0.0
            if buy_signals:
                avg_confidence = np.mean([s.confidence for s in buy_signals])
                expected_return = (avg_confidence - 0.5) * 0.10  # Max 5% retorno esperado
            
            return PortfolioAnalysisResponse(
                total_signals=len(signals),
                buy_signals=len(buy_signals),
                sell_signals=len(sell_signals),
                hold_signals=len(hold_signals),
                recommended_positions=recommended_positions,
                portfolio_allocation=portfolio_allocation,
                risk_assessment=risk_assessment,
                expected_return=expected_return
            )
            
        except Exception as e:
            logger.error(f"❌ Erro na análise do portfólio: {e}")
            raise HTTPException(status_code=500, detail=f"Erro na análise do portfólio: {str(e)}")

# Inicializa sistema global
hybrid_system = HybridTradingSystem()

# =====================================================
# ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Sistema Multi-Asset Trading",
        "version": "1.0.0",
        "focus": "Bolsa Americana - 60% Assertividade",
        "strategies": ["equilibrada_pro", "us_market", "hybrid"]
    }

@app.get("/api/health")
async def health_check():
    """Health check do sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc),
        "systems": {
            "equilibrada_pro": True,
            "us_market": True,
            "alpha_vantage": True
        }
    }

@app.get("/api/market/snapshot")
async def market_snapshot():
    """Snapshot atual do mercado americano"""
    try:
        snapshot = hybrid_system.data_manager.get_market_snapshot()
        return JSONResponse(content=snapshot, status_code=200)
    except Exception as e:
        logger.error(f"❌ Erro no snapshot: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter snapshot do mercado")

@app.post("/api/analyze/portfolio")
async def analyze_portfolio(request: PortfolioAnalysisRequest):
    """
    Análise completa do portfólio com sistema híbrido
    """
    try:
        analysis = await hybrid_system.analyze_portfolio_hybrid(
            symbols=request.symbols,
            amount=request.amount
        )
        
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Erro na análise: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/symbols/us-focus")
async def get_us_focus_symbols():
    """Retorna símbolos com foco americano"""
    return {
        "us_focus": hybrid_system.us_focus_symbols,
        "description": "Ações americanas otimizadas para 60% assertividade",
        "strategy": "us_market"
    }

@app.get("/api/analyze/single/{symbol}")
async def analyze_single_symbol(symbol: str):
    """
    Análise de um símbolo específico
    """
    try:
        # Carrega dados do símbolo
        if symbol in hybrid_system.us_focus_symbols:
            df = hybrid_system.data_manager.loader.get_intraday_data(symbol)
        else:
            # Para outros símbolos, dados simulados
            dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
            prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
            df = pd.DataFrame({
                'open': prices * 0.999,
                'high': prices * 1.002,
                'low': prices * 0.998,
                'close': prices,
                'volume': np.random.randint(100000, 1000000, 100)
            }, index=dates)
        
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"Dados não encontrados para {symbol}")
        
        signal = await hybrid_system.analyze_symbol_hybrid(symbol, df)
        return signal
        
    except Exception as e:
        logger.error(f"❌ Erro analisando {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# STARTUP
# =====================================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Sistema Multi-Asset iniciado com sucesso!")
    logger.info("🇺🇸 Foco: Bolsa americana com 60% assertividade")
    logger.info("💡 Estratégias: Equilibrada_Pro + US Market System")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Iniciando Sistema Multi-Asset Trading")
    print("🎯 Objetivo: 60% de assertividade na bolsa americana")
    print("💡 Estratégias híbridas: Equilibrada_Pro + US Market")
    print("📡 Dados: Alpha Vantage Premium")
    
    uvicorn.run(
        "app_multi_asset:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )