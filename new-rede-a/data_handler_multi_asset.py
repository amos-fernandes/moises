
import pandas as pd
import numpy as np
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.cryptocurrencies import CryptoCurrencies
# pandas_ta_classic is optional; provide fallbacks when unavailable
try:
    import pandas_ta_classic as ta
    PANDAS_TA_AVAILABLE = True
except Exception:
    ta = None
    PANDAS_TA_AVAILABLE = False
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import sys
import os
import time
import requests
from twelvedata import TDClient
import traceback
import json
import hashlib
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from config import ASSET_CONFIGS, NUM_FEATURES_PER_ASSET, WINDOW_SIZE, FINNHUB_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY, CACHE_DIR, CACHE_EXPIRATION_HOURS

INDIVIDUAL_ASSET_BASE_FEATURES = [
    'open', 'high', 'low', 'close', 'volume',
    'sma_10', 'rsi_14', 'macd', 'macds', 'atr', 'bbp', 'cci_37', 'mfi_37', 'adx_14',
    'volume_zscore', 'body_size', 'body_size_norm_atr',
    'log_return', 'buy_condition_v1', 'sma_50'
]

COLS_TO_NORM_BY_ATR = [ 'open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd', 'body_size' ]

def calculate_all_features_for_single_asset(ohlcv_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    if ohlcv_df.empty: return None
    df = ohlcv_df.copy()
    print(f"Calculando features para ativo (shape inicial: {df.shape})...")
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        else:
            df[col] = 0.0
    df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
    if df.empty:
        print("DataFrame vazio após garantir tipos numéricos e remover NaNs essenciais.")
        return None

    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    try:
        df['close'] = pd.to_numeric(df['close'], errors='coerce').fillna(0.0)

        if PANDAS_TA_AVAILABLE:
            df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
            df['sma_10'] = df['sma_10'].fillna(0.0)
        else:
            # simple rolling SMA fallback
            df['sma_10'] = df['close'].rolling(window=10).mean().fillna(0.0)

        if PANDAS_TA_AVAILABLE:
            df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
            df['rsi_14'] = df['rsi_14'].fillna(0.0)
        else:
            # simple RSI fallback implementation
            delta = df['close'].diff()
            up = delta.clip(lower=0).rolling(14).mean()
            down = -delta.clip(upper=0).rolling(14).mean()
            rs = up / (down + 1e-9)
            df['rsi_14'] = (100 - (100 / (1 + rs))).fillna(0.0)
        close_for_macd = pd.to_numeric(df["close"], errors='coerce').fillna(0.0)
        
        df["macd"] = 0.0
        df["macds"] = 0.0
        if PANDAS_TA_AVAILABLE and len(close_for_macd) >= 34:
            try:
                macd_result = ta.macd(close=close_for_macd, append=False)
                if macd_result is not None and not macd_result.empty and isinstance(macd_result, pd.DataFrame):
                    if 'MACD' in macd_result.columns and 'MACDs' in macd_result.columns:
                        df["macd"] = pd.to_numeric(macd_result['MACD'], errors='coerce').fillna(0.0)
                        df["macds"] = pd.to_numeric(macd_result['MACDs'], errors='coerce').fillna(0.0)
            except Exception:
                df["macd"] = 0.0
                df["macds"] = 0.0

        if PANDAS_TA_AVAILABLE:
            df.ta.atr(length=14, append=True, col_names=('atr',))
            df['atr'] = df['atr'].fillna(0.0)
        else:
            # ATR fallback using True Range rolling mean
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift(1)).abs()
            low_close = (df['low'] - df['close'].shift(1)).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(window=14).mean().fillna(0.0)

        if PANDAS_TA_AVAILABLE:
            df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp'))
            df['bbp'] = df['bbp'].fillna(0.0)
        else:
            # BBI-like fallback: normalize distance to 20-period rolling mean
            ma20 = df['close'].rolling(20).mean()
            std20 = df['close'].rolling(20).std().replace(0, 1e-9)
            df['bbp'] = ((df['close'] - ma20) / (2 * std20)).fillna(0.0)

        if PANDAS_TA_AVAILABLE:
            df.ta.cci(length=37, append=True, col_names=('CCI_37',))
        else:
            # simple CCI approximation
            tp = (df['high'] + df['low'] + df['close']) / 3.0
            ma_tp = tp.rolling(37).mean()
            md = tp.rolling(37).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
            df['CCI_37'] = ((tp - ma_tp) / (0.015 * (md + 1e-9))).fillna(0.0)
        if 'CCI_37' in df.columns:
            df['cci_37'] = df['CCI_37'].fillna(0.0)
            df.drop(columns=['CCI_37'], inplace=True, errors='ignore')
        else:
            df['cci_37'] = 0.0

        if PANDAS_TA_AVAILABLE:
            df.ta.mfi(length=37, append=True, col_names=('mfi_37',))
        else:
            # MFI fallback: money flow index approx using volume * typical price
            typical = (df['high'] + df['low'] + df['close']) / 3.0
            money_flow = typical * df['volume']
            positive = money_flow.where(typical > typical.shift(1), 0.0).rolling(37).sum()
            negative = money_flow.where(typical < typical.shift(1), 0.0).rolling(37).sum()
            mfi = 100 - (100 / (1 + (positive / (negative + 1e-9))))
            df['mfi_37'] = mfi.fillna(0.0)
        if 'mfi_37' in df.columns:
            df['mfi_37'] = df['mfi_37'].astype('float64').fillna(0.0)
        else:
            df['mfi_37'] = 0.0

        if PANDAS_TA_AVAILABLE:
            adx_out = df.ta.adx(length=14, append=False)
            if adx_out is not None and not adx_out.empty and isinstance(adx_out, pd.DataFrame):
                df['adx_14'] = adx_out.iloc[:,0].fillna(0.0)
            else:
                df['adx_14'] = 0.0
        else:
            df['adx_14'] = 0.0

        df["open"] = pd.to_numeric(df["open"], errors='coerce').fillna(0.0)
        df["close"] = pd.to_numeric(df["close"], errors='coerce').fillna(0.0)
        df["body_size"] = abs(df["close"] - df["open"])
        df["body_size"] = df["body_size"].fillna(0.0)

        rolling_vol_mean = df["volume"].rolling(window=20).mean().fillna(0.0)
        rolling_vol_std = df["volume"].rolling(window=20).std().fillna(0.0)
        df["volume_zscore"] = (df["volume"] - rolling_vol_mean) / (rolling_vol_std + 1e-9)
        df["volume_zscore"] = np.nan_to_num(df["volume_zscore"], nan=0.0, posinf=1e5, neginf=-1e5)
        df["volume_zscore"] = df["volume_zscore"].fillna(0.0)

        df["body_vs_avg_body"] = df["body_size"] / (df["body_size"].rolling(window=20).mean().fillna(0.0) + 1e-9)
        df["body_vs_avg_body"] = np.nan_to_num(df["body_vs_avg_body"], nan=0.0, posinf=1e5, neginf=-1e5)
        df["body_vs_avg_body"] = df["body_vs_avg_body"].fillna(0.0)

        df_atr_valid = df[df['atr'] > 1e-9].copy()
        if df_atr_valid.empty:
            df['body_size_norm_atr'] = 0.0
            for col in COLS_TO_NORM_BY_ATR:
                df[f'{col}_div_atr'] = 0.0
        else:
            df['body_size_norm_atr'] = df['body_size'] / df['atr']
            for col in COLS_TO_NORM_BY_ATR:
                if col in df.columns:
                    df[f'{col}_div_atr'] = df[col] / (df['atr'] + 1e-9)
                else:
                    df[f'{col}_div_atr'] = 0.0
        df['body_size_norm_atr'] = df['body_size_norm_atr'].fillna(0.0)

        df['body_vs_avg_body'] = df['body_size'] / (df['body_size'].rolling(window=20).mean().fillna(0.0) + 1e-9)
        df['body_vs_avg_body'] = df['body_vs_avg_body'].fillna(0.0)
        
        close_safe = df['close'].replace(0, 1e-9)
        close_shifted_safe = df['close'].shift(1).replace(0, 1e-9)
        df['log_return'] = np.log(close_safe / close_shifted_safe)
        df['log_return'] = df['log_return'].fillna(0.0)
        
        if PANDAS_TA_AVAILABLE:
            sma_50_series = df.ta.sma(length=50, close='close', append=False)
            if sma_50_series is not None:
                if isinstance(sma_50_series, pd.DataFrame) and 'SMA_50' in sma_50_series.columns:
                    df['sma_50'] = sma_50_series['SMA_50'].fillna(0.0)
                elif isinstance(sma_50_series, pd.Series):
                    df['sma_50'] = sma_50_series.fillna(0.0)
                else:
                    df['sma_50'] = 0.0
            else:
                df['sma_50'] = 0.0
        else:
            df['sma_50'] = df['close'].rolling(window=50).mean().fillna(0.0)
        
        for col in ['macd', 'macds', 'rsi_14', 'close', 'sma_50']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            else:
                df[col] = 0.0

        # Compute buy_condition_v1 robustly
        try:
            df['buy_condition_v1'] = ((df.get('macd', 0.0) > df.get('macds', 0.0)) & (df.get('rsi_14', 0.0) > 50) & (df['close'] > df.get('sma_50', df['close']))).astype(int)
        except Exception:
            df['buy_condition_v1'] = 0
        
        # Ensure canonical names expected by training code exist
        canonical_cols = ['open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr',
                          'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 'body_size_norm_atr',
                          'body_vs_avg_body', 'macd', 'sma_10', 'sma_50', 'sma_10_div_atr', 'adx_14', 'volume_zscore', 'buy_condition_v1']

        # Create derived canonical columns where possible
        if 'sma_10' in df.columns and 'atr' in df.columns:
            df['sma_10_div_atr'] = df['sma_10'] / (df['atr'] + 1e-9)
        else:
            df['sma_10_div_atr'] = 0.0

        # log_return already computed earlier. For safety, ensure column exists
        if 'log_return' not in df.columns:
            close_safe = df['close'].replace(0, 1e-9)
            df['log_return'] = np.log(close_safe / close_safe.shift(1)).fillna(0.0)

        # Ensure price/volume div by ATR columns exist
        for base in ['open', 'high', 'low', 'close', 'volume']:
            col_name = f"{base}_div_atr"
            if col_name not in df.columns:
                if 'atr' in df.columns and base in df.columns:
                    df[col_name] = df[base] / (df['atr'] + 1e-9)
                else:
                    df[col_name] = 0.0

        current_feature_cols = [col for col in canonical_cols if col in df.columns]
        missing_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col not in df.columns]
        if missing_cols:
            print(f"AVISO: Colunas de features ausentes após cálculo: {missing_cols}. Usando apenas as disponíveis: {current_feature_cols}")

        df_final_features = df[current_feature_cols].copy()
        # Replace infinite values with NaN, then winsorize/clip to robust ranges
        df_final_features.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Compute per-column percentiles (1% and 99%) ignoring NaNs
        try:
            lower = df_final_features.quantile(0.01)
            upper = df_final_features.quantile(0.99)
        except Exception:
            lower = None
            upper = None

        # Apply winsorization: clip to 1st-99th percentiles when available
        if lower is not None and upper is not None:
            for col in df_final_features.columns:
                try:
                    lo = lower.get(col, None)
                    hi = upper.get(col, None)
                    if pd.notna(lo) and pd.notna(hi) and lo < hi:
                        df_final_features[col] = df_final_features[col].clip(lower=lo, upper=hi)
                except Exception:
                    pass

        # Finally, apply a conservative absolute cap to any remaining extreme values
        ABS_CAP = 1e3
        df_final_features = df_final_features.clip(lower=-ABS_CAP, upper=ABS_CAP)

        # Drop rows that are completely NaN now
        df_final_features.dropna(how='all', inplace=True)
        print(f"Features calculadas. Shape após dropna: {df_final_features.shape}. Colunas: {df_final_features.columns.tolist()}")
        return df_final_features
    except Exception as e:
        print(f"Erro ao calcular features: {e}")
        traceback.print_exc()
        return None

def fetch_finnhub_data(
    symbol: str,
    resolution: str,
    from_timestamp: int,
    to_timestamp: int,
    api_key: str
) -> Optional[pd.DataFrame]:
    cache_key = _get_cache_key("finnhub", symbol, resolution, str(from_timestamp), str(to_timestamp))
    cached_data = _load_from_cache(cache_key)
    if cached_data is not None:
        print(f"Dados de {symbol} carregados do cache (Finnhub).")
        return cached_data

    url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution={resolution}&from={from_timestamp}&to={to_timestamp}&token={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data["s"] == "ok":
            df = pd.DataFrame({
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"]
            }, index=pd.to_datetime(data["t"], unit="s"))
            df.index.name = "datetime"
            _save_to_cache(cache_key, df)
            return df
        else:
            print(f"Erro ao buscar dados do Finnhub para {symbol}: {data["s"]}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao Finnhub para {symbol}: {e}")
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar dados do Finnhub para {symbol}: {e}")
        return None

def fetch_twelve_data(
    symbol: str,
    interval: str,
    start_date: str,
    end_date: str,
    api_key: str,
    asset_type: str
) -> Optional[pd.DataFrame]:
    cache_key = _get_cache_key("twelve_data", symbol, interval, start_date, end_date)
    cached_data = _load_from_cache(cache_key)
    if cached_data is not None:
        print(f"Dados de {symbol} carregados do cache (Twelve Data).")
        return cached_data

    twelve_data_interval = {"1h": "1h", "1d": "1day", "5min": "5min"}.get(interval, "1h")
    
    td = TDClient(apikey=api_key)

    retries = 3
    for i in range(retries):
        try:
            ts = td.time_series(
                symbol=symbol,
                interval=twelve_data_interval,
                start_date=start_date,
                end_date=end_date
            ).as_pandas()

            if ts.empty:
                print(f"Nenhum dado encontrado para {symbol} do Twelve Data.")
                return None
            
            df = ts.copy()
            df = df.apply(pd.to_numeric, errors='coerce')

            if "volume" not in df.columns:
                df["volume"] = 0
            
            df = df[['open', 'high', 'low', 'close', 'volume']]
            _save_to_cache(cache_key, df)
            return df

        except Exception as e:
            print(f"Erro ao buscar dados do Twelve Data para {symbol} (tentativa {i+1}/{retries}): {e}")
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                sleep_time = 60 * (i + 1) # Espera 1 minuto, 2 minutos, etc.
                print(f"Limite de taxa atingido para Twelve Data. Esperando {sleep_time} segundos antes de tentar novamente...")
                time.sleep(sleep_time)
            else:
                print(f"Erro inesperado do Twelve Data para {symbol}: {e}")
                break
    return None

def get_multi_asset_data_for_rl(
    asset_configs: Dict[str, Dict[str, str]], 
    timeframe_av: str, 
    days_to_fetch: int,
    api_key: str,
    finnhub_api_key: str,
    twelve_data_api_key: str
) -> Optional[pd.DataFrame]:
    all_asset_features_list = []
    
    ts_av = TimeSeries(key=api_key, output_format='pandas')
    fx_av = ForeignExchange(key=api_key, output_format='pandas')
    cc_av = CryptoCurrencies(key=api_key, output_format='pandas')

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_to_fetch)
    from_timestamp = int(start_date.timestamp())
    to_timestamp = int(end_date.timestamp())

    start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

    for asset_type, assets in asset_configs.items():
        for asset_key, config in assets.items():
            symbol = asset_key
            interval = config.get("interval", timeframe_av)

            print(f"\n--- Processando {asset_type.upper()} - {asset_key} ---")
            data = pd.DataFrame()
            
            print(f"Tentando buscar dados do Twelve Data para {symbol}...")
            twelve_data_symbol = symbol
            if asset_type == "FOREX":
                twelve_data_symbol = f"{symbol[:3]}/{symbol[3:]}"
            data = fetch_twelve_data(twelve_data_symbol, interval, start_date_str, end_date_str, twelve_data_api_key, asset_type)

            if data is not None and not data.empty:
                print(f"Dados coletados do Twelve Data para {symbol}: {len(data)} linhas.")
            else:
                print(f"Falha ao buscar dados do Twelve Data para {symbol}. Tentando Finnhub...")
                finnhub_resolution = {"1h": "60", "1d": "D", "5min": "5"}.get(interval, "60")
                data = fetch_finnhub_data(symbol, finnhub_resolution, from_timestamp, to_timestamp, finnhub_api_key)

                if data is not None and not data.empty:
                    print(f"Dados coletados do Finnhub para {symbol}: {len(data)} linhas.")
                else:
                    print(f"Falha ao buscar dados do Finnhub para {symbol}. Tentando Alpha Vantage...")
                    try:
                        cache_key_av = _get_cache_key("alpha_vantage", symbol, interval, start_date_str, end_date_str)
                        cached_data_av = _load_from_cache(cache_key_av)
                        if cached_data_av is not None:
                            print(f"Dados de {symbol} carregados do cache (Alpha Vantage).")
                            data = cached_data_av
                        else:
                            # Fetch depending on asset type
                            if asset_type in ("STOCKS", "MINI_INDICES"):
                                if interval == "1d":
                                    data, meta_data = ts_av.get_daily(symbol=symbol, outputsize='compact')
                                elif interval == "60min":
                                    data, meta_data = ts_av.get_intraday(symbol=symbol, interval='60min', outputsize='compact')
                                elif interval == "5min":
                                    data, meta_data = ts_av.get_intraday(symbol=symbol, interval='5min', outputsize='compact')
                                else:
                                    print(f"Intervalo {interval} não suportado para {asset_type} na Alpha Vantage. Pulando {symbol}.")
                                    data = None
                                if data is not None:
                                    data.columns = [col.split(". ")[1] for col in data.columns]

                            elif asset_type == "FOREX":
                                from_symbol = symbol[:3]
                                to_symbol = symbol[3:]
                                if interval == "1d":
                                    data, meta_data = fx_av.get_currency_exchange_daily(from_symbol=from_symbol, to_symbol=to_symbol, outputsize='full')
                                elif interval == "60min":
                                    data, meta_data = fx_av.get_currency_exchange_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='60min', outputsize='full')
                                elif interval == "5min":
                                    data, meta_data = fx_av.get_currency_exchange_intraday(from_symbol=from_symbol, to_symbol=to_symbol, interval='5min', outputsize='full')
                                else:
                                    print(f"Intervalo {interval} não suportado para FOREX na Alpha Vantage. Pulando {symbol}.")
                                    data = None
                                if data is not None:
                                    data.columns = [col.split(". ")[1] for col in data.columns]
                                    data.rename(columns={'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close'}, inplace=True)
                                    data['volume'] = 0

                            elif asset_type == "CRYPTO":
                                market = config.get("market", "USD")
                                if interval == "daily":
                                    data, meta_data = cc_av.get_digital_currency_daily(symbol=symbol, market=market)
                                else:
                                    print(f"Intervalo {interval} não suportado para CRYPTO na Alpha Vantage. Pulando {symbol}.")
                                    data = None
                                if data is not None:
                                    data.columns = [col.split(". ")[1].replace(f' ({market})', '') for col in data.columns]
                                    data.rename(columns={'open (USD)': 'open', 'high (USD)': 'high', 'low (USD)': 'low', 'close (USD)': 'close', 'volume': 'volume'}, inplace=True)

                            # Save to cache only when data was successfully fetched
                            if data is not None and not data.empty:
                                _save_to_cache(cache_key_av, data)
                                print(f"Dados coletados da Alpha Vantage para {symbol}: {len(data)} linhas.")
                            else:
                                print(f"Falha ao buscar dados da Alpha Vantage para {symbol}.")
                                continue
                    except Exception as e:
                        print(f"Erro ao buscar dados da Alpha Vantage para {symbol}: {e}")
                        continue

            if data is not None and not data.empty:
                features_df = calculate_all_features_for_single_asset(data)
                if features_df is not None and not features_df.empty:
                    features_df["asset_id"] = asset_key
                    # Adicionar a coluna de preço de fechamento original com o prefixo do ativo
                    features_df[f"{asset_key}_close"] = data["close"]
                    all_asset_features_list.append(features_df)

                else:
                    print(f"Não foi possível calcular features para {asset_key}. Pulando.")
            else:
                print(f"Nenhum dado encontrado para {asset_key} em nenhuma fonte. Pulando.")

    if not all_asset_features_list:
        print("Nenhuma feature foi calculada para nenhum ativo. Retornando None.")
        return None

    all_features_df = pd.concat(all_asset_features_list, ignore_index=True)
    print(f"Shape final de todas as features: {all_features_df.shape}")
    return all_features_df




def _get_cache_key(provider: str, symbol: str, interval: str, start_date: str, end_date: str) -> str:
    """Gera uma chave de cache única para uma solicitação de dados."""
    hash_input = f"{provider}-{symbol}-{interval}-{start_date}-{end_date}"
    return hashlib.md5(hash_input.encode()).hexdigest()

def _save_to_cache(key: str, data: pd.DataFrame):
    """Salva um DataFrame no cache."""
    cache_path = Path(CACHE_DIR) / f"{key}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data.to_json(cache_path, orient='split', date_format='iso')

def _load_from_cache(key: str) -> Optional[pd.DataFrame]:
    """Carrega um DataFrame do cache se ele existir e não estiver expirado."""
    cache_path = Path(CACHE_DIR) / f"{key}.json"
    if cache_path.exists():
        modified_time = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
        if datetime.now(timezone.utc) - modified_time < timedelta(hours=CACHE_EXPIRATION_HOURS):
            return pd.read_json(cache_path, orient='split')
    return None

