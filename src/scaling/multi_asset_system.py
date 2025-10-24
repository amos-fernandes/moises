"""
📈 MULTI-ASSET SCALING SYSTEM
Sistema de expansão para múltiplos mercados e ativos
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AssetClass(Enum):
    STOCKS_US = "stocks_us"
    STOCKS_BR = "stocks_br"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITIES = "commodities"
    INDICES = "indices"

@dataclass
class AssetConfig:
    symbol: str
    asset_class: AssetClass
    market_hours: Dict[str, str]
    min_position_size: float
    max_position_size: float
    commission_rate: float
    leverage: float = 1.0

class MultiAssetScalingSystem:
    """
    Sistema de scaling para múltiplos mercados e classes de ativos
    """
    
    def __init__(self):
        self.supported_assets = {}
        self.active_markets = set()
        self.correlation_matrix = {}
        self.market_schedulers = {}
        
        # Configurações de risco por classe de ativo
        self.risk_configs = {
            AssetClass.STOCKS_US: {"max_allocation": 0.40, "risk_multiplier": 1.0},
            AssetClass.STOCKS_BR: {"max_allocation": 0.30, "risk_multiplier": 1.2},
            AssetClass.CRYPTO: {"max_allocation": 0.15, "risk_multiplier": 2.0},
            AssetClass.FOREX: {"max_allocation": 0.25, "risk_multiplier": 1.5},
            AssetClass.COMMODITIES: {"max_allocation": 0.20, "risk_multiplier": 1.3},
            AssetClass.INDICES: {"max_allocation": 0.35, "risk_multiplier": 0.8}
        }
        
        self._initialize_asset_universe()
        logger.info("📈 MultiAssetScalingSystem inicializado")
    
    def _initialize_asset_universe(self):
        """
        Inicializa universo de ativos suportados
        """
        # Ações americanas (principais)
        us_stocks = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX",
            "AMD", "CRM", "ADBE", "PYPL", "INTC", "CSCO", "PFE", "JNJ"
        ]
        
        for symbol in us_stocks:
            self.supported_assets[symbol] = AssetConfig(
                symbol=symbol,
                asset_class=AssetClass.STOCKS_US,
                market_hours={"open": "09:30", "close": "16:00", "timezone": "EST"},
                min_position_size=1,
                max_position_size=10000,
                commission_rate=0.0005
            )
        
        # Ações brasileiras
        br_stocks = [
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA",
            "WEGE3.SA", "MGLU3.SA", "PETR3.SA", "B3SA3.SA", "RENT3.SA"
        ]
        
        for symbol in br_stocks:
            self.supported_assets[symbol] = AssetConfig(
                symbol=symbol,
                asset_class=AssetClass.STOCKS_BR,
                market_hours={"open": "10:00", "close": "17:00", "timezone": "BRT"},
                min_position_size=100,
                max_position_size=100000,
                commission_rate=0.0025
            )
        
        # Criptomoedas (principais)
        crypto_assets = [
            "BTC-USD", "ETH-USD", "BNB-USD", "ADA-USD", "SOL-USD",
            "DOT-USD", "AVAX-USD", "MATIC-USD", "LINK-USD", "UNI-USD"
        ]
        
        for symbol in crypto_assets:
            self.supported_assets[symbol] = AssetConfig(
                symbol=symbol,
                asset_class=AssetClass.CRYPTO,
                market_hours={"open": "00:00", "close": "23:59", "timezone": "UTC"},
                min_position_size=0.001,
                max_position_size=100,
                commission_rate=0.001,
                leverage=2.0
            )
        
        # Forex (principais pares)
        forex_pairs = [
            "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
            "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"
        ]
        
        for symbol in forex_pairs:
            self.supported_assets[symbol] = AssetConfig(
                symbol=symbol,
                asset_class=AssetClass.FOREX,
                market_hours={"open": "17:00", "close": "17:00", "timezone": "EST"},  # 24h
                min_position_size=1000,
                max_position_size=1000000,
                commission_rate=0.0002,
                leverage=10.0
            )
    
    def calculate_cross_asset_correlations(self, price_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Calcula correlações cruzadas entre ativos
        """
        logger.info("📊 Calculando correlações cross-asset...")
        
        # Preparar dados para correlação
        returns_data = {}
        
        for symbol, df in price_data.items():
            if len(df) >= 30:  # Mínimo de dados
                returns = df['close'].pct_change().dropna()
                returns_data[symbol] = returns.tail(252)  # 1 ano de dados
        
        if len(returns_data) < 2:
            return {"correlations": {}, "status": "insufficient_data"}
        
        # Criar DataFrame de retornos
        returns_df = pd.DataFrame(returns_data)
        
        # Calcular matriz de correlação
        correlation_matrix = returns_df.corr()
        
        # Identificar correlações altas (>0.7 ou <-0.7)
        high_correlations = []
        for i, asset1 in enumerate(correlation_matrix.columns):
            for j, asset2 in enumerate(correlation_matrix.columns):
                if i < j:  # Evitar duplicatas
                    corr = correlation_matrix.loc[asset1, asset2]
                    if abs(corr) > 0.7:
                        high_correlations.append({
                            "asset1": asset1,
                            "asset2": asset2,
                            "correlation": corr,
                            "risk_level": "high" if abs(corr) > 0.8 else "medium"
                        })
        
        # Agrupar por classe de ativo
        class_correlations = {}
        for asset_class in AssetClass:
            class_assets = [s for s, config in self.supported_assets.items() 
                          if config.asset_class == asset_class and s in returns_data]
            
            if len(class_assets) > 1:
                class_corr_matrix = returns_df[class_assets].corr()
                avg_correlation = class_corr_matrix.values[np.triu_indices_from(class_corr_matrix.values, k=1)].mean()
                class_correlations[asset_class.value] = {
                    "avg_correlation": avg_correlation,
                    "assets_count": len(class_assets),
                    "diversification_score": 1.0 - abs(avg_correlation)
                }
        
        self.correlation_matrix = {
            "full_matrix": correlation_matrix.to_dict(),
            "high_correlations": high_correlations,
            "class_correlations": class_correlations,
            "calculation_date": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Correlações calculadas para {len(returns_data)} ativos")
        return self.correlation_matrix
    
    def optimize_multi_asset_portfolio(self, 
                                     available_capital: float,
                                     risk_tolerance: str = "medium") -> Dict:
        """
        Otimiza portfólio multi-asset baseado em correlações e risco
        """
        logger.info("🎯 Otimizando portfólio multi-asset...")
        
        risk_multipliers = {
            "conservative": 0.5,
            "medium": 1.0,
            "aggressive": 1.5
        }
        
        risk_mult = risk_multipliers.get(risk_tolerance, 1.0)
        
        # Alocação base por classe de ativo
        base_allocations = {}
        total_allocation = 0.0
        
        for asset_class, config in self.risk_configs.items():
            max_alloc = config["max_allocation"] * risk_mult
            risk_adjusted_alloc = max_alloc / config["risk_multiplier"]
            
            base_allocations[asset_class] = {
                "percentage": min(risk_adjusted_alloc, max_alloc),
                "amount": available_capital * min(risk_adjusted_alloc, max_alloc),
                "risk_score": config["risk_multiplier"]
            }
            
            total_allocation += min(risk_adjusted_alloc, max_alloc)
        
        # Normalizar alocações
        if total_allocation > 1.0:
            for asset_class in base_allocations:
                base_allocations[asset_class]["percentage"] /= total_allocation
                base_allocations[asset_class]["amount"] /= total_allocation
        
        # Seleção específica de ativos
        selected_assets = {}
        
        for asset_class, allocation in base_allocations.items():
            if allocation["percentage"] > 0.01:  # Mínimo 1%
                class_assets = [s for s, config in self.supported_assets.items() 
                              if config.asset_class == asset_class]
                
                # Selecionar top ativos da classe (simplificado)
                num_assets = min(5, len(class_assets))  # Máximo 5 por classe
                selected_class_assets = class_assets[:num_assets]
                
                asset_allocation = allocation["amount"] / len(selected_class_assets)
                
                for asset in selected_class_assets:
                    selected_assets[asset] = {
                        "allocation_amount": asset_allocation,
                        "allocation_percentage": asset_allocation / available_capital,
                        "asset_class": asset_class.value,
                        "risk_score": allocation["risk_score"]
                    }
        
        portfolio = {
            "total_capital": available_capital,
            "risk_tolerance": risk_tolerance,
            "class_allocations": {k.value: v for k, v in base_allocations.items()},
            "selected_assets": selected_assets,
            "diversification_metrics": {
                "num_assets": len(selected_assets),
                "num_asset_classes": len([k for k, v in base_allocations.items() if v["percentage"] > 0.01]),
                "concentration_risk": max([v["allocation_percentage"] for v in selected_assets.values()])
            },
            "optimization_date": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Portfolio otimizado: {len(selected_assets)} ativos em {portfolio['diversification_metrics']['num_asset_classes']} classes")
        return portfolio
    
    def get_market_schedule(self) -> Dict:
        """
        Retorna cronograma de mercados ativos
        """
        current_utc = datetime.utcnow()
        
        schedules = {}
        
        for asset_class in AssetClass:
            class_assets = [config for config in self.supported_assets.values() 
                          if config.asset_class == asset_class]
            
            if class_assets:
                sample_config = class_assets[0]
                market_hours = sample_config.market_hours
                
                schedules[asset_class.value] = {
                    "market_open": market_hours.get("open", "00:00"),
                    "market_close": market_hours.get("close", "23:59"),
                    "timezone": market_hours.get("timezone", "UTC"),
                    "is_24h": asset_class in [AssetClass.CRYPTO, AssetClass.FOREX],
                    "estimated_assets": len(class_assets)
                }
        
        return {
            "current_utc": current_utc.isoformat(),
            "market_schedules": schedules,
            "active_markets": self._get_currently_active_markets(current_utc)
        }
    
    def _get_currently_active_markets(self, current_time: datetime) -> List[str]:
        """
        Determina quais mercados estão ativos no momento
        """
        # Simplificado - crypto e forex sempre ativos
        active = ["crypto", "forex"]
        
        # Verificar horário de ações (aproximado)
        hour_utc = current_time.hour
        
        # Ações US (14:30-21:00 UTC aproximadamente)
        if 14 <= hour_utc <= 21:
            active.append("stocks_us")
        
        # Ações BR (13:00-20:00 UTC aproximadamente)  
        if 13 <= hour_utc <= 20:
            active.append("stocks_br")
        
        return active
    
    def calculate_scaling_metrics(self) -> Dict:
        """
        Calcula métricas de scaling do sistema
        """
        metrics = {
            "supported_assets": {
                "total": len(self.supported_assets),
                "by_class": {}
            },
            "market_coverage": {
                "asset_classes": len(AssetClass),
                "geographic_regions": ["US", "BR", "Global"],
                "24h_markets": 2,  # Crypto + Forex
                "traditional_markets": 4  # Stocks, Commodities, Indices
            },
            "risk_management": {
                "correlation_tracking": bool(self.correlation_matrix),
                "position_sizing_rules": True,
                "cross_asset_limits": True
            },
            "scalability": {
                "max_concurrent_assets": 50,
                "max_positions_per_class": 10,
                "total_portfolio_limit": 100
            }
        }
        
        # Contagem por classe
        for asset_class in AssetClass:
            count = sum(1 for config in self.supported_assets.values() 
                       if config.asset_class == asset_class)
            metrics["supported_assets"]["by_class"][asset_class.value] = count
        
        return metrics
    
    def generate_expansion_roadmap(self) -> Dict:
        """
        Gera roadmap de expansão para novos mercados
        """
        roadmap = {
            "current_phase": "Multi-Asset Foundation",
            "expansion_phases": {
                "phase_1_completion": {
                    "description": "Finalizar implementação atual",
                    "targets": ["Otimizar correlações", "Validar risk management"],
                    "timeline": "2-3 semanas",
                    "priority": "high"
                },
                "phase_2_geographic": {
                    "description": "Expansão geográfica",
                    "targets": ["Europa (FTSE, DAX)", "Ásia (Nikkei, Hang Seng)"],
                    "timeline": "1-2 meses", 
                    "priority": "medium"
                },
                "phase_3_alternatives": {
                    "description": "Ativos alternativos",
                    "targets": ["REITs", "ETFs", "Bonds", "Derivatives"],
                    "timeline": "2-3 meses",
                    "priority": "medium"
                },
                "phase_4_advanced": {
                    "description": "Estratégias avançadas",
                    "targets": ["Pairs trading", "Statistical arbitrage", "Market making"],
                    "timeline": "3-6 meses",
                    "priority": "low"
                }
            },
            "success_metrics": {
                "target_assets": 200,
                "target_classes": 8,
                "target_regions": 5,
                "target_strategies": 10
            }
        }
        
        return roadmap