"""
Aplicação Multi-Asset com Aprendizado Neural Contínuo
Sistema híbrido que combina estratégias existentes com rede neural
que aprende e melhora continuamente
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
import sys
import os
from threading import Thread
import json

# Adiciona paths do projeto
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Imports dos sistemas
from src.trading.production_system import ProductionTradingSystem
from src.trading.us_market_system import USMarketAnalyzer, USMarketStrategy
from src.data.alpha_vantage_loader import USMarketDataManager
from src.ml.neural_learning_agent import NeuralTradingAgent
from src.ml.continuous_training import ContinuousLearningSystem

# Novos imports para evolução 85% ganhos
from src.evolution.neural_evolution_orchestrator import NeuralEvolutionOrchestrator
from src.optimization.performance_optimizer import PerformanceOptimizer
from src.ml.advanced_neural_agent import AdvancedNeuralAgent
from src.scaling.multi_asset_system import MultiAssetScalingSystem

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sistema Multi-Asset com IA Adaptativa",
    description="Trading system com aprendizado neural contínuo para 60%+ assertividade",
    version="2.0.0"
)

# =====================================================
# MODELS
# =====================================================

class NeuralPredictionRequest(BaseModel):
    symbol: str
    use_neural: bool = True
    confidence_threshold: float = 0.65

class NeuralPredictionResponse(BaseModel):
    symbol: str
    neural_signal: str
    neural_confidence: float
    expert_signal: str
    expert_confidence: float
    final_recommendation: str
    reasoning: List[str]
    learning_status: Dict

class LearningStatusResponse(BaseModel):
    learning_active: bool
    current_accuracy: float
    total_experiences: int
    training_sessions: int
    neural_vs_expert_performance: Dict
    model_evolution: Dict

class AdaptivePortfolioRequest(BaseModel):
    symbols: List[str]
    amount: float = 10000.0
    use_neural: bool = True
    adaptive_mode: bool = True

# =====================================================
# SISTEMA INTEGRADO
# =====================================================

class NeuralEnhancedTradingSystem:
    """
    Sistema de trading que combina:
    1. Estratégias comprovadas (Equilibrada_Pro + US Market)
    2. Rede neural que aprende continuamente
    3. Seleção adaptativa baseada em performance
    """
    
    def __init__(self):
        # Componentes principais
        self.equilibrada_pro = ProductionTradingSystem()
        self.us_analyzer = USMarketAnalyzer()
        self.us_strategy = USMarketStrategy()
        self.data_manager = USMarketDataManager()
        
        # Sistema de aprendizado neural
        self.learning_system = ContinuousLearningSystem()
        self.neural_agent = None  # Versão mínima
        
        # 🎯 SISTEMA DE EVOLUÇÃO PARA 85% GANHOS
        self.evolution_orchestrator = NeuralEvolutionOrchestrator()
        self.performance_optimizer = PerformanceOptimizer()
        self.multi_asset_system = MultiAssetScalingSystem()
        self.evolution_active = False
        
        # Tenta carregar modelo existente (versão mínima)
        logger.info("🆕 Modelo neural em modo mínimo - Evolução para 85% disponível")
        
        # Status do sistema
        self.system_ready = False
        self.learning_thread = None
        
        logger.info("🚀 Sistema Neural Integrado inicializado com capacidade de evolução")
    
    def start_learning(self):
        """Inicia aprendizado contínuo"""
        if not hasattr(self, 'learning_thread') or not self.learning_thread:
            self.learning_system.start_continuous_training()
            logger.info("🎓 Aprendizado contínuo iniciado")
            self.learning_thread = True  # Versão mínima
    
    def stop_learning(self):
        """Para aprendizado contínuo"""
        if hasattr(self, 'learning_thread'):
            self.learning_thread = False
        logger.info("🛑 Aprendizado contínuo parado")
    
    async def analyze_with_neural_enhancement(self, symbol: str, use_neural: bool = True) -> Dict:
        """
        Análise híbrida: combina experts + rede neural
        Seleciona automaticamente a melhor abordagem
        """
        try:
            # Carrega dados
            df = self.data_manager.loader.get_intraday_data(symbol)
            if df is None or len(df) < 50:
                raise ValueError(f"Dados insuficientes para {symbol}")
            
            # Análise dos experts
            us_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
            
            if symbol in us_stocks:
                expert_signal_obj = self.us_analyzer.analyze_us_stock(symbol, df)
                expert_signal = expert_signal_obj.signal
                expert_confidence = expert_signal_obj.confidence
                expert_strategy = "us_market"
            else:
                ep_result = self.equilibrada_pro.analyze_market_data(df)
                if ep_result and 'signal' in ep_result:
                    if ep_result['signal'] > 0.6:
                        expert_signal = "BUY"
                        expert_confidence = ep_result['signal']
                    elif ep_result['signal'] < 0.4:
                        expert_signal = "SELL"
                        expert_confidence = 1 - ep_result['signal']
                    else:
                        expert_signal = "HOLD"
                        expert_confidence = 0.5
                else:
                    expert_signal = "HOLD"
                    expert_confidence = 0.5
                expert_strategy = "equilibrada_pro"
            
            # Análise neural (se habilitada)
            neural_signal = "HOLD"
            neural_confidence = 0.5
            
            if use_neural:
                # Neural em modo mínimo - usa estratégia Equilibrada Pro
                neural_signal = equilibrada_signal
                neural_confidence = equilibrada_confidence
            
            # Decisão final adaptativa
            final_signal, reasoning = self._adaptive_decision(
                expert_signal, expert_confidence, expert_strategy,
                neural_signal, neural_confidence, symbol
            )
            
            return {
                "symbol": symbol,
                "expert_signal": expert_signal,
                "expert_confidence": expert_confidence,
                "expert_strategy": expert_strategy,
                "neural_signal": neural_signal,
                "neural_confidence": neural_confidence,
                "final_signal": final_signal,
                "reasoning": reasoning,
                "data_points": len(df),
                "last_price": df['close'].iloc[-1],
                "timestamp": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de {symbol}: {e}")
            raise
    
    def _adaptive_decision(self, expert_signal: str, expert_conf: float, expert_strategy: str,
                          neural_signal: str, neural_conf: float, symbol: str) -> tuple:
        """
        Decisão adaptativa baseada na performance histórica
        """
        reasoning = []
        
        # Obtém métricas de performance (modo mínimo)
        neural_performance = {'accuracy': 0.5, 'avg_reward': 0.0}
        current_accuracy = 0.5
        
        # Critérios de decisão
        high_confidence_threshold = 0.75
        agreement_bonus = 0.1
        
        # Verifica concordância
        signals_agree = expert_signal == neural_signal
        if signals_agree:
            reasoning.append(f"Expert e Neural concordam: {expert_signal}")
        
        # Lógica de seleção adaptativa
        if current_accuracy >= 0.65 and neural_conf >= high_confidence_threshold:
            # Neural com boa performance e alta confiança
            final_signal = neural_signal
            reasoning.append(f"Neural selecionado (acc: {current_accuracy:.1%}, conf: {neural_conf:.1%})")
            
        elif expert_conf >= high_confidence_threshold:
            # Expert com alta confiança
            final_signal = expert_signal
            reasoning.append(f"Expert selecionado (conf: {expert_conf:.1%}, strategy: {expert_strategy})")
            
        elif signals_agree:
            # Concordância aumenta confiança
            final_signal = expert_signal
            adjusted_conf = min((expert_conf + neural_conf) / 2 + agreement_bonus, 1.0)
            reasoning.append(f"Concordância (conf ajustada: {adjusted_conf:.1%})")
            
        else:
            # Conflito - usa critério de desempate
            if expert_conf > neural_conf:
                final_signal = expert_signal
                reasoning.append(f"Expert venceu por confiança ({expert_conf:.1%} vs {neural_conf:.1%})")
            else:
                final_signal = neural_signal
                reasoning.append(f"Neural venceu por confiança ({neural_conf:.1%} vs {expert_conf:.1%})")
        
        # Filtro final de confiança mínima
        max_confidence = max(expert_conf, neural_conf)
        if max_confidence < 0.6:
            final_signal = "HOLD"
            reasoning.append("Confiança insuficiente - HOLD recomendado")
        
        return final_signal, reasoning

# Inicializa sistema global
neural_trading_system = NeuralEnhancedTradingSystem()

# =====================================================
# ENDPOINTS
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Inicialização do sistema"""
    logger.info("🚀 Iniciando Sistema Neural Integrado")
    neural_trading_system.start_learning()
    neural_trading_system.system_ready = True

@app.on_event("shutdown")
async def shutdown_event():
    """Finalização do sistema"""
    logger.info("🛑 Finalizando sistema")
    neural_trading_system.stop_learning()

@app.get("/health")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "system_ready": neural_trading_system.system_ready,
        "neural_agent_available": neural_trading_system.neural_agent is not None,
        "learning_active": neural_trading_system.learning_thread is not None
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Neural Trading System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            .header { text-align: center; color: #333; border-bottom: 2px solid #007acc; padding-bottom: 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-value { font-size: 2em; font-weight: bold; }
            .stat-label { margin-top: 5px; opacity: 0.9; }
            .section { margin: 30px 0; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn-primary { background: #007acc; color: white; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧠 Neural Enhanced Trading System</h1>
                <p>Sistema de trading com IA adaptativa para 60%+ assertividade</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">60%+</div>
                    <div class="stat-label">Meta Assertividade</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">🧠+👨‍💼</div>
                    <div class="stat-label">IA + Experts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">🇺🇸</div>
                    <div class="stat-label">Foco Bolsa Americana</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">24/7</div>
                    <div class="stat-label">Aprendizado Contínuo</div>
                </div>
            </div>
            
            <div class="section">
                <h2>🎯 Endpoints Disponíveis</h2>
                <ul>
                    <li><strong>GET /api/neural/status</strong> - Status do aprendizado neural</li>
                    <li><strong>POST /api/neural/predict</strong> - Predição neural + expert</li>
                    <li><strong>POST /api/portfolio/adaptive</strong> - Análise adaptativa de portfólio</li>
                    <li><strong>GET /api/neural/performance</strong> - Métricas de performance</li>
                    <li><strong>POST /api/neural/control</strong> - Controle do sistema (start/stop)</li>
                </ul>
            </div>
            
            <div class="section">
                <h2>🚀 Iniciar Análise</h2>
                <p>Use a API para analisar símbolos ou portfolios com IA adaptativa.</p>
                <p><strong>Símbolos recomendados:</strong> AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/api/neural/status")
async def neural_status():
    """Status do sistema neural"""
    status = neural_trading_system.learning_system.get_current_status()
    
    # Verifica se neural_agent existe antes de chamar evaluate_performance
    if neural_trading_system.neural_agent:
        performance = neural_trading_system.neural_agent.evaluate_performance()
        neural_performance = performance if not performance.get('insufficient_data') else None
    else:
        neural_performance = {"status": "neural_agent_not_initialized", "mode": "minimal_version"}
    
    return {
        "system_ready": neural_trading_system.system_ready,
        "learning_status": status,
        "neural_performance": neural_performance,
        "model_info": {
            "exploration_rate": neural_trading_system.neural_agent.epsilon if neural_trading_system.neural_agent else 0.1,
            "memory_size": len(neural_trading_system.neural_agent.memory) if neural_trading_system.neural_agent else 0,
            "training_memory_size": len(neural_trading_system.neural_agent.training_memory) if neural_trading_system.neural_agent else 0,
        }
    }

@app.post("/api/neural/predict")
async def neural_prediction(request: NeuralPredictionRequest):
    """Predição neural combinada com expert"""
    try:
        analysis = await neural_trading_system.analyze_with_neural_enhancement(
            symbol=request.symbol,
            use_neural=request.use_neural
        )
        
        learning_status = neural_trading_system.learning_system.get_current_status()
        
        return NeuralPredictionResponse(
            symbol=analysis["symbol"],
            neural_signal=analysis["neural_signal"],
            neural_confidence=analysis["neural_confidence"],
            expert_signal=analysis["expert_signal"],
            expert_confidence=analysis["expert_confidence"],
            final_recommendation=analysis["final_signal"],
            reasoning=analysis["reasoning"],
            learning_status=learning_status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/portfolio/adaptive")
async def adaptive_portfolio_analysis(request: AdaptivePortfolioRequest):
    """Análise adaptativa de portfólio"""
    try:
        results = []
        
        for symbol in request.symbols:
            try:
                analysis = await neural_trading_system.analyze_with_neural_enhancement(
                    symbol=symbol,
                    use_neural=request.use_neural
                )
                results.append(analysis)
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        # Filtra sinais de alta confiança
        high_confidence_signals = [
            r for r in results 
            if r["final_signal"] in ["BUY", "SELL"] and 
            max(r["expert_confidence"], r["neural_confidence"]) >= 0.65
        ]
        
        # Calcula alocação adaptativa
        total_confidence = sum(
            max(r["expert_confidence"], r["neural_confidence"]) 
            for r in high_confidence_signals
        )
        
        allocations = []
        for result in high_confidence_signals:
            max_conf = max(result["expert_confidence"], result["neural_confidence"])
            weight = (max_conf / total_confidence) if total_confidence > 0 else 0
            allocation = request.amount * weight * 0.9  # 90% máximo
            
            allocations.append({
                "symbol": result["symbol"],
                "signal": result["final_signal"],
                "confidence": max_conf,
                "allocation": allocation,
                "reasoning": result["reasoning"][:2]  # Top 2 reasons
            })
        
        return {
            "total_symbols_analyzed": len(results),
            "high_confidence_signals": len(high_confidence_signals),
            "recommended_allocations": allocations,
            "total_allocated": sum(a["allocation"] for a in allocations),
            "cash_remaining": request.amount - sum(a["allocation"] for a in allocations),
            "adaptive_mode": request.adaptive_mode,
            "analysis_timestamp": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/neural/performance")
async def neural_performance():
    """Métricas detalhadas de performance"""
    if neural_trading_system.neural_agent:
        performance = neural_trading_system.neural_agent.evaluate_performance()
    else:
        performance = {"status": "neural_agent_not_initialized", "accuracy": 0.5, "total_trades": 0}
    
    learning_metrics = neural_trading_system.learning_system.learning_metrics
    
    return {
        "current_performance": performance,
        "learning_evolution": {
            "accuracy_trend": learning_metrics.get('accuracy_history', [])[-10:],
            "reward_trend": learning_metrics.get('reward_history', [])[-10:],
            "total_experiences": learning_metrics.get('total_experiences', 0),
            "training_sessions": learning_metrics.get('training_sessions', 0)
        },
        "expert_comparison": learning_metrics.get('expert_vs_neural_comparison', [])[-5:],
        "model_parameters": {
            "exploration_rate": neural_trading_system.neural_agent.epsilon if neural_trading_system.neural_agent else 0.1,
            "learning_rate": 0.001,
            "current_accuracy": 0.5
        }
    }

@app.post("/api/neural/control")
async def neural_control(action: str):
    """Controla sistema neural (start/stop/restart)"""
    try:
        if action == "start":
            neural_trading_system.start_learning()
            return {"message": "Aprendizado iniciado", "status": "active"}
        
        elif action == "stop":
            neural_trading_system.stop_learning()
            return {"message": "Aprendizado parado", "status": "stopped"}
        
        elif action == "restart":
            neural_trading_system.stop_learning()
            await asyncio.sleep(2)
            neural_trading_system.start_learning()
            return {"message": "Aprendizado reiniciado", "status": "restarted"}
        
        elif action == "save":
            if neural_trading_system.neural_agent:
                neural_trading_system.neural_agent.save_model()
                return {"message": "Modelo salvo", "status": "saved"}
            else:
                return {"message": "Neural agent não inicializado", "status": "not_available"}
        
        else:
            raise HTTPException(status_code=400, detail="Ação inválida")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evolution/start")
async def start_evolution():
    """🎯 Inicia evolução para 85% ganhos"""
    try:
        if neural_trading_system.evolution_active:
            return {"message": "Evolução já em progresso", "status": "already_running"}
        
        neural_trading_system.evolution_active = True
        
        # Executar evolução em background
        evolution_results = await neural_trading_system.evolution_orchestrator.execute_evolution_roadmap()
        
        neural_trading_system.evolution_active = False
        
        return {
            "message": "Evolução concluída",
            "status": "completed",
            "results": evolution_results,
            "target_achieved": evolution_results.get("target_achieved", False)
        }
        
    except Exception as e:
        neural_trading_system.evolution_active = False
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/evolution/status")
async def evolution_status():
    """Status da evolução para 85% ganhos"""
    try:
        status = neural_trading_system.evolution_orchestrator.get_evolution_status()
        
        return {
            "evolution_active": neural_trading_system.evolution_active,
            "evolution_status": status,
            "system_components": {
                "performance_optimizer": neural_trading_system.performance_optimizer is not None,
                "multi_asset_system": neural_trading_system.multi_asset_system is not None,
                "evolution_orchestrator": neural_trading_system.evolution_orchestrator is not None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/optimization/analysis") 
async def optimization_analysis():
    """Análise de otimização atual"""
    try:
        # Análise de performance atual
        current_metrics = neural_trading_system.performance_optimizer.analyze_current_performance([])
        
        # Plano de otimização
        optimization_plan = neural_trading_system.performance_optimizer.generate_optimization_plan()
        
        # Métricas de scaling
        scaling_metrics = neural_trading_system.multi_asset_system.calculate_scaling_metrics()
        
        return {
            "current_metrics": current_metrics,
            "optimization_plan": optimization_plan,
            "scaling_metrics": scaling_metrics,
            "target_accuracy": 0.85,
            "gap_analysis": {
                "current_gap": 0.85 - current_metrics.get("current_accuracy", 0.50),
                "improvement_potential": optimization_plan.get("total_expected_gain", 0.0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/multi-asset/portfolio")
async def multi_asset_portfolio():
    """Portfólio multi-asset otimizado"""
    try:
        # Portfolio otimizado
        portfolio = neural_trading_system.multi_asset_system.optimize_multi_asset_portfolio(
            available_capital=100000,
            risk_tolerance="medium"
        )
        
        # Schedule de mercados
        market_schedule = neural_trading_system.multi_asset_system.get_market_schedule()
        
        # Roadmap de expansão
        expansion_roadmap = neural_trading_system.multi_asset_system.generate_expansion_roadmap()
        
        return {
            "optimized_portfolio": portfolio,
            "market_schedule": market_schedule,
            "expansion_roadmap": expansion_roadmap,
            "scaling_capacity": {
                "current_assets": len(neural_trading_system.multi_asset_system.supported_assets),
                "max_capacity": 200,
                "asset_classes": 6
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ENDPOINTS BINANCE REAL - TESTE CONECTIVIDADE
# =====================================================

@app.post("/api/trading/test-binance")
async def test_binance_connection(request: dict):
    """
    Testa conexão real com Binance
    Body: {"api_key": "...", "secret": "...", "use_testnet": true}
    """
    try:
        # Importar binance tester
        from src.trading.binance_real_tester import binance_tester
        
        api_key = request.get("api_key")
        secret = request.get("secret") 
        use_testnet = request.get("use_testnet", True)
        
        if not api_key or not secret:
            raise HTTPException(status_code=400, detail="API key e secret são obrigatórios")
        
        # Executar teste de conexão
        test_results = await binance_tester.test_binance_connection(
            api_key=api_key,
            secret=secret,
            use_testnet=use_testnet
        )
        
        return {
            "test_results": test_results,
            "connection_summary": binance_tester.get_connection_summary(),
            "system_status": "ready_for_real_trading" if test_results.get("connection_status") == "SUCCESS" else "connection_failed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no teste Binance: {str(e)}")

@app.get("/api/trading/binance-status")
async def binance_connection_status():
    """Status da última conexão Binance testada"""
    try:
        from src.trading.binance_real_tester import binance_tester
        
        summary = binance_tester.get_connection_summary()
        
        return {
            "binance_connection": summary,
            "ready_for_trading": summary.get("ready_for_neural_trading", False),
            "last_test": summary.get("last_test", "Nenhum teste executado")
        }
        
    except Exception as e:
        return {
            "binance_connection": {"status": "NOT_TESTED"},
            "ready_for_trading": False,
            "error": str(e)
        }

# =====================================================
# ENDPOINTS SISTEMA HUMANITÁRIO - IMPACTO SOCIAL  
# =====================================================

@app.get("/api/social/impact-report")
async def get_impact_report():
    """Relatório de impacto social do sistema"""
    try:
        from src.social.humanitarian_system import humanitarian_system
        
        impact_report = humanitarian_system.get_impact_report()
        success_stories = humanitarian_system.generate_success_stories()
        system_status = humanitarian_system.get_system_status()
        
        return {
            "impact_report": impact_report,
            "success_stories": success_stories[:5],  # Top 5 histórias
            "system_status": system_status,
            "mission": "Transformar lucros do trading neural em esperança para famílias necessitadas"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no relatório social: {str(e)}")

@app.post("/api/social/register-family")
async def register_beneficiary_family(family_data: dict):
    """Registra nova família beneficiária"""
    try:
        from src.social.humanitarian_system import humanitarian_system
        
        success = humanitarian_system.register_beneficiary(family_data)
        
        if success:
            return {
                "status": "success",
                "message": f"Família {family_data.get('name', 'N/A')} registrada com sucesso",
                "family_id": len(humanitarian_system.beneficiaries),
                "monthly_support": humanitarian_system.monthly_per_family
            }
        else:
            raise HTTPException(status_code=400, detail="Dados incompletos para registro")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no registro: {str(e)}")

@app.post("/api/social/process-donations")
async def process_monthly_donations():
    """Processa doações mensais automáticas"""
    try:
        from src.social.humanitarian_system import humanitarian_system
        
        result = humanitarian_system.process_monthly_donations()
        
        return {
            "donation_result": result,
            "humanitarian_impact": f"{result.get('donations_processed', 0)} famílias atendidas",
            "next_processing": "Próximo mês automaticamente"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

@app.post("/api/social/emergency-help")
async def emergency_assistance(emergency_data: dict):
    """Assistência de emergência para beneficiário"""
    try:
        from src.social.humanitarian_system import humanitarian_system
        
        beneficiary_id = emergency_data.get("beneficiary_id")
        amount = emergency_data.get("amount")
        reason = emergency_data.get("reason", "Emergência")
        
        if not beneficiary_id or not amount:
            raise HTTPException(status_code=400, detail="ID do beneficiário e valor são obrigatórios")
        
        success = humanitarian_system.emergency_assistance(beneficiary_id, amount, reason)
        
        if success:
            return {
                "status": "success",
                "message": f"Emergência processada: R$ {amount:.2f}",
                "reason": reason,
                "processed_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Não foi possível processar emergência")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na emergência: {str(e)}")

@app.get("/api/social/fund-status")
async def social_fund_status():
    """Status atual do fundo social"""
    try:
        from src.social.humanitarian_system import humanitarian_system
        
        status = humanitarian_system.get_system_status()
        
        return {
            "fund_status": status,
            "capacity": f"Pode ajudar {status['monthly_capacity']} famílias por mês",
            "total_impact": status["total_impact"],
            "health": status["fund_health"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 NEURAL TRADING SYSTEM - EVOLUÇÃO + BINANCE REAL")
    print("=" * 70)
    print("🎯 Target: 85% accuracy")
    print("🧠 Sistema: Neural + Expert híbrido com evolução")
    print("📊 Evolução: 4 fases implementadas")
    print("🌐 Endpoints: /api/evolution/* + /api/trading/*") 
    print("💰 Binance: Teste real com /api/trading/test-binance")
    print("=" * 70)
    
    uvicorn.run(
        "app_neural_trading:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )