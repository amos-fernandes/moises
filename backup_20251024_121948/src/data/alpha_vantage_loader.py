"""
Alpha Vantage Data Loader Otimizado para Ações Americanas
Foco em alta qualidade de dados para 60% assertividade
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import time
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class AlphaVantageLoader:
    """
    Loader otimizado para Alpha Vantage
    Especializado em ações americanas para máxima assertividade
    """
    
    def __init__(self, api_key: str = "0BZTLZG8FP5KZHFV"):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limit_delay = 12  # 5 calls per minute = 12s delay
        self.last_call_time = 0
        
        # Cache para evitar chamadas desnecessárias
        self.cache = {}
        
    def _respect_rate_limit(self):
        """Respeita o rate limit da API"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_call
            logger.info(f"⏰ Rate limit: aguardando {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    def get_intraday_data(self, symbol: str, interval: str = "60min", outputsize: str = "full") -> Optional[pd.DataFrame]:
        """
        Busca dados intraday otimizados para ações americanas
        """
        self._respect_rate_limit()
        
        # Verifica cache primeiro
        cache_key = f"{symbol}_{interval}_{outputsize}"
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            # Cache válido por 1 hora
            if time.time() - cache_time < 3600:
                logger.info(f"📋 Usando cache para {symbol}")
                return data
        
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'apikey': self.api_key,
            'outputsize': outputsize,
            'datatype': 'json'
        }
        
        try:
            logger.info(f"📡 Buscando dados Alpha Vantage: {symbol} ({interval})")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Verifica erros da API
            if "Error Message" in data:
                logger.error(f"❌ Erro da API: {data['Error Message']}")
                return None
            
            if "Note" in data:
                logger.warning(f"⚠️ Limite da API: {data['Note']}")
                time.sleep(60)  # Espera 1 minuto se atingir limite
                return None
            
            # Extrai dados das séries temporais
            time_series_key = f"Time Series ({interval})"
            if time_series_key not in data:
                logger.error(f"❌ Chave não encontrada: {time_series_key}")
                logger.error(f"Chaves disponíveis: {list(data.keys())}")
                return None
            
            time_series = data[time_series_key]
            
            # Converte para DataFrame
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            
            # Renomeia colunas
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # Converte tipos
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove dados inválidos
            df = df.dropna()
            
            if df.empty:
                logger.error(f"❌ DataFrame vazio para {symbol}")
                return None
            
            # Cache do resultado
            self.cache[cache_key] = (time.time(), df.copy())
            
            logger.info(f"✅ {symbol}: {len(df)} registros carregados")
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro buscando {symbol}: {e}")
            return None
    
    def get_daily_data(self, symbol: str, outputsize: str = "full") -> Optional[pd.DataFrame]:
        """
        Busca dados diários para análise de longo prazo
        """
        self._respect_rate_limit()
        
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'apikey': self.api_key,
            'outputsize': outputsize,
            'datatype': 'json'
        }
        
        try:
            logger.info(f"📡 Buscando dados diários: {symbol}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if "Error Message" in data:
                logger.error(f"❌ Erro da API: {data['Error Message']}")
                return None
            
            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                logger.error(f"❌ Dados diários não encontrados para {symbol}")
                return None
            
            df = pd.DataFrame.from_dict(time_series, orient='index')
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna()
            
            logger.info(f"✅ {symbol} diário: {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro buscando dados diários {symbol}: {e}")
            return None
    
    def get_company_overview(self, symbol: str) -> Optional[Dict]:
        """
        Busca informações fundamentais da empresa
        """
        self._respect_rate_limit()
        
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            logger.info(f"📊 Buscando overview: {symbol}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or "Symbol" not in data:
                logger.warning(f"⚠️ Overview não encontrado para {symbol}")
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Erro buscando overview {symbol}: {e}")
            return None
    
    def get_technical_indicators(self, symbol: str, indicator: str, interval: str = "60min", **kwargs) -> Optional[pd.DataFrame]:
        """
        Busca indicadores técnicos prontos da Alpha Vantage
        """
        self._respect_rate_limit()
        
        params = {
            'function': indicator,
            'symbol': symbol,
            'interval': interval,
            'apikey': self.api_key,
            **kwargs
        }
        
        try:
            logger.info(f"📈 Buscando {indicator}: {symbol}")
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Encontra a chave dos dados técnicos
            tech_key = None
            for key in data.keys():
                if "Technical Analysis" in key or indicator.upper() in key:
                    tech_key = key
                    break
            
            if not tech_key:
                logger.error(f"❌ Dados técnicos não encontrados para {indicator}")
                return None
            
            tech_data = data[tech_key]
            
            df = pd.DataFrame.from_dict(tech_data, orient='index')
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro buscando indicador {indicator}: {e}")
            return None

class USMarketDataManager:
    """
    Gerenciador de dados específico para mercado americano
    Otimizado para alta assertividade (60%+)
    """
    
    def __init__(self, api_key: str = "0BZTLZG8FP5KZHFV"):
        self.loader = AlphaVantageLoader(api_key)
        self.us_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA"]
        self.data_cache = {}
        
    def load_us_market_data(self, symbols: Optional[List[str]] = None, interval: str = "60min") -> Dict[str, pd.DataFrame]:
        """
        Carrega dados de múltiplas ações americanas
        """
        if symbols is None:
            symbols = self.us_symbols
        
        market_data = {}
        
        logger.info(f"🇺🇸 Carregando dados do mercado americano: {len(symbols)} ações")
        
        for symbol in symbols:
            try:
                df = self.loader.get_intraday_data(symbol, interval)
                if df is not None and len(df) > 50:  # Mínimo 50 registros
                    market_data[symbol] = df
                    logger.info(f"✅ {symbol}: {len(df)} registros ({df.index[0]} a {df.index[-1]})")
                else:
                    logger.warning(f"⚠️ {symbol}: Dados insuficientes ou inválidos")
                    
            except Exception as e:
                logger.error(f"❌ Erro carregando {symbol}: {e}")
        
        logger.info(f"📊 Total carregado: {len(market_data)}/{len(symbols)} ações")
        return market_data
    
    def enrich_with_fundamentals(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Enriquece dados com informações fundamentais
        """
        fundamentals = {}
        
        for symbol in symbols:
            try:
                overview = self.loader.get_company_overview(symbol)
                if overview:
                    # Extrai métricas importantes
                    fundamentals[symbol] = {
                        'market_cap': overview.get('MarketCapitalization', 0),
                        'pe_ratio': overview.get('PERatio', 0),
                        'peg_ratio': overview.get('PEGRatio', 0),
                        'dividend_yield': overview.get('DividendYield', 0),
                        'profit_margin': overview.get('ProfitMargin', 0),
                        'sector': overview.get('Sector', 'Unknown'),
                        'industry': overview.get('Industry', 'Unknown'),
                        '52_week_high': overview.get('52WeekHigh', 0),
                        '52_week_low': overview.get('52WeekLow', 0),
                    }
                    
                    # Converte strings para números
                    for key, value in fundamentals[symbol].items():
                        if key not in ['sector', 'industry']:
                            try:
                                fundamentals[symbol][key] = float(value) if value != 'None' else 0
                            except:
                                fundamentals[symbol][key] = 0
                                
            except Exception as e:
                logger.error(f"❌ Erro carregando fundamentais {symbol}: {e}")
        
        return fundamentals
    
    def get_market_snapshot(self) -> Dict:
        """
        Retorna snapshot do mercado americano
        """
        # Carrega dados das principais ações
        market_data = self.load_us_market_data(self.us_symbols[:3], "60min")  # Top 3 para velocidade
        
        if not market_data:
            return {"status": "error", "message": "Sem dados disponíveis"}
        
        snapshot = {
            "timestamp": datetime.now(),
            "symbols_loaded": list(market_data.keys()),
            "market_summary": {}
        }
        
        # Calcula resumo do mercado
        total_symbols = len(market_data)
        up_count = 0
        down_count = 0
        
        for symbol, df in market_data.items():
            if len(df) >= 2:
                latest = df.iloc[-1]
                previous = df.iloc[-2]
                change = (latest['close'] - previous['close']) / previous['close']
                
                if change > 0:
                    up_count += 1
                else:
                    down_count += 1
                
                snapshot["market_summary"][symbol] = {
                    "price": latest['close'],
                    "change_pct": change * 100,
                    "volume": latest['volume']
                }
        
        snapshot["market_sentiment"] = {
            "up_stocks": up_count,
            "down_stocks": down_count,
            "net_sentiment": (up_count - down_count) / total_symbols if total_symbols > 0 else 0
        }
        
        return snapshot

# Exemplo de uso
if __name__ == "__main__":
    print("📡 Alpha Vantage Data Loader para Mercado Americano")
    
    # Teste básico
    loader = AlphaVantageLoader()
    data_manager = USMarketDataManager()
    
    # Carrega dados de uma ação
    aapl_data = loader.get_intraday_data("AAPL", "60min")
    if aapl_data is not None:
        print(f"✅ AAPL: {len(aapl_data)} registros carregados")
        print(f"📈 Último preço: ${aapl_data['close'].iloc[-1]:.2f}")
    
    # Snapshot do mercado
    snapshot = data_manager.get_market_snapshot()
    print(f"📊 Snapshot: {snapshot['symbols_loaded']}")
    print(f"📈 Sentimento: {snapshot['market_sentiment']}")