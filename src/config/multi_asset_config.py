"""
Sistema Multi-Asset Trading com foco na Bolsa Americana
Objetivo: 60% de assertividade operando com múltiplos ativos
Integração com Alpha Vantage API para dados premium
"""

import os
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass

# =====================================================
# CONFIGURAÇÃO MULTI-ASSET PARA BOLSA AMERICANA
# =====================================================

@dataclass
class AssetConfig:
    symbol: str
    interval: str
    market: str
    weight: float  # Peso no portfólio (0.0 - 1.0)
    priority: int  # Prioridade para seleção (1=alta, 3=baixa)
    sector: str
    
# Configuração otimizada para bolsa americana (60% assertividade)
ENHANCED_ASSET_CONFIGS = {
    "US_TECH": {
        "AAPL": AssetConfig("AAPL", "60min", "NASDAQ", 0.20, 1, "Technology"),
        "MSFT": AssetConfig("MSFT", "60min", "NASDAQ", 0.18, 1, "Technology"), 
        "GOOGL": AssetConfig("GOOGL", "60min", "NASDAQ", 0.15, 1, "Technology"),
        "NVDA": AssetConfig("NVDA", "60min", "NASDAQ", 0.12, 1, "Technology"),
        "TSLA": AssetConfig("TSLA", "60min", "NASDAQ", 0.10, 2, "Automotive"),
    },
    "US_ECOMMERCE": {
        "AMZN": AssetConfig("AMZN", "60min", "NASDAQ", 0.15, 1, "E-commerce"),
    },
    "BRAZILIAN_STOCKS": {
        "PETR4.SA": AssetConfig("PETR4.SA", "60min", "B3", 0.05, 3, "Energy"),
        "VALE3.SA": AssetConfig("VALE3.SA", "60min", "B3", 0.05, 3, "Mining"),
    },
    "FOREX_MAJORS": {
        "EURUSD": AssetConfig("EUR/USD", "60min", "FOREX", 0.0, 3, "Currency"),
        "GBPUSD": AssetConfig("GBP/USD", "60min", "FOREX", 0.0, 3, "Currency"),
    },
    "CRYPTO_PREMIUM": {
        "BTC/USD": AssetConfig("BTC-USD", "60min", "CRYPTO", 0.0, 2, "Cryptocurrency"),
        "ETH/USD": AssetConfig("ETH-USD", "60min", "CRYPTO", 0.0, 2, "Cryptocurrency"),
    }
}

# =====================================================
# ESTRATÉGIAS ESPECÍFICAS POR MERCADO
# =====================================================

# Configuração para Alpha Vantage (Premium API para bolsa americana)
ALPHA_VANTAGE_CONFIG = {
    "api_key": "0BZTLZG8FP5KZHFV",  # Sua chave atual
    "premium": True,  # Permite mais chamadas por minuto
    "rate_limit_per_minute": 75,  # Premium permite até 75 calls/min
    "preferred_intervals": ["60min", "15min", "5min"],
    "us_market_focus": True
}

# Parâmetros otimizados para 60% assertividade
PERFORMANCE_TARGET_CONFIG = {
    "target_accuracy": 0.60,  # 60% assertividade
    "min_confidence_threshold": 0.65,  # Só opera com 65%+ confiança
    "risk_per_trade": 0.02,  # 2% risco por trade
    "max_portfolio_risk": 0.08,  # 8% risco total do portfólio
    "profit_target_multiplier": 3.0,  # R:R 1:3 (2% risco, 6% alvo)
    "max_correlation_limit": 0.7,  # Evita ativos muito correlacionados
}

# Features específicas para cada tipo de ativo
ASSET_TYPE_FEATURES = {
    "US_TECH": [
        "rsi_14", "macd", "bb_percent", "volume_ratio", "price_momentum_5",
        "volatility_15min", "support_resistance", "sector_strength",
        "market_sentiment", "earnings_proximity", "options_flow"
    ],
    "FOREX": [
        "rsi_14", "macd", "atr_normalized", "currency_strength",
        "interest_rate_differential", "economic_calendar_impact",
        "session_volatility", "correlation_analysis"
    ],
    "CRYPTO": [
        "rsi_14", "macd", "bb_percent", "volume_profile", "whale_activity",
        "social_sentiment", "funding_rates", "market_dominance"
    ]
}

# =====================================================
# SISTEMA DE SELEÇÃO DE ATIVOS DINÂMICO
# =====================================================

class AssetSelector:
    def __init__(self, config: Dict):
        self.config = config
        self.active_assets = []
        
    def select_best_assets(self, market_conditions: str = "normal") -> List[str]:
        """
        Seleciona os melhores ativos baseado nas condições de mercado
        Foco: Maximizar assertividade em 60%+
        """
        selected = []
        
        if market_conditions == "bull_us_tech":
            # Mercado altista em tech - foca nos grandes
            selected = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]
            
        elif market_conditions == "volatile":
            # Mercado volátil - reduz exposição, foca em qualidade
            selected = ["AAPL", "MSFT", "GOOGL"]
            
        elif market_conditions == "bear":
            # Mercado baixista - defensive stocks + forex
            selected = ["AAPL", "MSFT", "EURUSD"]
            
        else:  # normal
            # Portfólio balanceado com foco americano
            selected = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
            
        return selected

# =====================================================
# INTEGRAÇÃO COM SISTEMA EXISTENTE
# =====================================================

def integrate_with_existing_system():
    """
    Integra a nova configuração multi-asset com o sistema Equilibrada_Pro
    """
    
    # Converte para formato compatível com sistema atual
    compatible_config = {
        "STOCKS": {},
        "FOREX": {},
        "CRYPTO": {}
    }
    
    # Mapeia ativos americanos prioritários
    for category, assets in ENHANCED_ASSET_CONFIGS.items():
        for symbol, config in assets.items():
            if category.startswith("US_") and config.priority == 1:
                compatible_config["STOCKS"][symbol] = {
                    "interval": config.interval,
                    "weight": config.weight,
                    "market": config.market
                }
            elif "FOREX" in category:
                compatible_config["FOREX"][symbol] = {
                    "interval": config.interval
                }
            elif "CRYPTO" in category:
                compatible_config["CRYPTO"][symbol] = {
                    "interval": config.interval
                }
                
    return compatible_config

# =====================================================
# CONFIGURAÇÃO FINAL OTIMIZADA
# =====================================================

# Sistema híbrido: mantém compatibilidade + adiciona inteligência
OPTIMIZED_ASSET_CONFIGS = {
    "STOCKS": {
        # Foco em ações americanas de alta qualidade
        "AAPL": {"interval": "60min", "weight": 0.25, "priority": 1, "market": "US"},
        "MSFT": {"interval": "60min", "weight": 0.20, "priority": 1, "market": "US"},
        "GOOGL": {"interval": "60min", "weight": 0.18, "priority": 1, "market": "US"},
        "AMZN": {"interval": "60min", "weight": 0.15, "priority": 1, "market": "US"},
        "NVDA": {"interval": "60min", "weight": 0.12, "priority": 1, "market": "US"},
        "TSLA": {"interval": "60min", "weight": 0.10, "priority": 2, "market": "US"},
        # Ações brasileiras com menor peso
        "PETR4.SA": {"interval": "60min", "weight": 0.0, "priority": 3, "market": "BR"},
        "VALE3.SA": {"interval": "60min", "weight": 0.0, "priority": 3, "market": "BR"},
    },
    "FOREX": {
        # Pares principais - baixa prioridade no momento
        "EURUSD": {"interval": "60min", "weight": 0.0, "priority": 3},
        "GBPUSD": {"interval": "60min", "weight": 0.0, "priority": 3},
    },
    "CRYPTO": {
        # Crypto - baixa prioridade no momento
        "BTC/USD": {"interval": "60min", "weight": 0.0, "priority": 3},
        "ETH/USD": {"interval": "60min", "weight": 0.0, "priority": 3},
    }
}

# Parâmetros de performance para 60% assertividade
PERFORMANCE_PARAMS = {
    "confidence_threshold": 0.65,
    "max_positions": 3,  # Máximo 3 posições simultâneas
    "position_size_base": 0.15,  # 15% por posição
    "stop_loss": 0.02,  # 2% stop loss
    "take_profit": 0.06,  # 6% take profit (R:R 1:3)
    "trailing_stop": 0.015,  # 1.5% trailing stop
    "min_volume_filter": 1000000,  # Mínimo 1M volume diário
}

# API Configuration para dados premium
API_CONFIG = {
    "alpha_vantage": {
        "key": "0BZTLZG8FP5KZHFV",
        "premium": True,
        "calls_per_minute": 75
    },
    "finnhub": {
        "key": "d3ledrhr01qq28en5ebgd3ledrhr01qq28en5ec0",
        "tier": "premium"
    },
    "twelve_data": {
        "key": "8798569186934c3089c169619aea9975", 
        "plan": "premium"
    }
}

if __name__ == "__main__":
    print("🚀 Configuração Multi-Asset para Bolsa Americana")
    print("📊 Objetivo: 60% de assertividade")
    print("💼 Foco: Ações americanas de alta qualidade")
    
    selector = AssetSelector(OPTIMIZED_ASSET_CONFIGS)
    best_assets = selector.select_best_assets("normal")
    print(f"✅ Ativos selecionados: {best_assets}")