import pandas as pd
import numpy as np
import yfinance as yf # / ccxt,
try:
    import pandas_ta as ta
except Exception:
    ta = None
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Try to import project config from common locations. Prefer agents.config, then scripts.config, then top-level config.
aconf = None
try:
    import agents.config as aconf
except Exception:
    try:
        import config as aconf
    except Exception:
        try:
            import scripts.config as aconf
        except Exception:
            aconf = None

# Resolve base feature list and window size from available config, with sensible defaults
if aconf is not None and hasattr(aconf, 'BASE_FEATURES_PER_ASSET_INPUT'):
    INDIVIDUAL_ASSET_BASE_FEATURES = list(aconf.BASE_FEATURES_PER_ASSET_INPUT)
else:
    # minimal safe default to avoid runtime issues; empty list forces graceful behavior upstream
    INDIVIDUAL_ASSET_BASE_FEATURES = []

# If config import failed to provide the base feature list, set a sensible default
if not INDIVIDUAL_ASSET_BASE_FEATURES:
    INDIVIDUAL_ASSET_BASE_FEATURES = [
        'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr',
        'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37',
        'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr',
        'adx_14', 'volume_zscore', 'buy_condition_v1'
    ]

if aconf is not None and hasattr(aconf, 'WINDOW_SIZE'):
    WINDOW_SIZE = int(getattr(aconf, 'WINDOW_SIZE'))
else:
    WINDOW_SIZE = 60

# Features que serão normalizadas pelo ATR
COLS_TO_NORM_BY_ATR = ['open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd', 'body_size']
#----------------------------------
# -- New get multi asset data for rl
# ... (imports e outras funções como antes) ...
def get_multi_asset_data_for_rl(
    asset_symbols_map: Dict[str, str],
    timeframe_yf: str,
    days_to_fetch: int,
    logger_instance=None,  # optional logger
) -> Optional[pd.DataFrame]:

    all_asset_features_list: List[pd.DataFrame] = [] # Tipagem para clareza
    min_data_length = float('inf')
    print(all_asset_features_list)
    
    #logger_instance.info(f"Iniciando get_multi_asset_data_for_rl para: {list(asset_symbols_map.keys())}")

    for asset_key, yf_ticker in asset_symbols_map.items():
       
        single_asset_ohlcv = fetch_single_asset_ohlcv_yf(yf_ticker, period=f"{days_to_fetch}d", interval=timeframe_yf) # Passar logger se a função aceitar

    
        single_asset_features = calculate_all_features_for_single_asset(single_asset_ohlcv)#, logger_instance) 
        
        if single_asset_features is None or single_asset_features.empty:
            if logger_instance:
                logger_instance.warning(f"Sem features calculadas para {yf_ticker}, pulando.")
            else:
                print(f"Sem features calculadas para {yf_ticker}, pulando.")
            continue
        
        #logger_instance.info(f"Features para {asset_key} shape: {single_asset_features.shape}, Index Min: {single_asset_features.index.min()}, Index Max: {single_asset_features.index.max()}")
        
        # Garantir que o índice é DatetimeIndex e UTC para todos antes de adicionar prefixo e à lista
        if not isinstance(single_asset_features.index, pd.DatetimeIndex):
            single_asset_features.index = pd.to_datetime(single_asset_features.index)
        if single_asset_features.index.tz is None:
            single_asset_features.index = single_asset_features.index.tz_localize('UTC')
        else:
            single_asset_features.index = single_asset_features.index.tz_convert('UTC')

        single_asset_features = single_asset_features.add_prefix(f"{asset_key}_")
        all_asset_features_list.append(single_asset_features)
        min_data_length = min(min_data_length, len(single_asset_features))

    if not all_asset_features_list:
        if logger_instance:
            logger_instance.error("Nenhum DataFrame de feature de ativo foi adicionado à lista.")
        else:
            print("Nenhum DataFrame de feature de ativo foi adicionado à lista.")
        return None

    if min_data_length == float('inf') or min_data_length < WINDOW_SIZE: # Adicionada checagem de WINDOW_SIZE
        msg = f"min_data_length inválido ({min_data_length}) ou menor que WINDOW_SIZE ({WINDOW_SIZE}). Não é possível truncar/usar."
        if logger_instance:
            logger_instance.error(msg)
        else:
            print(msg)
        return None

    #logger_instance.info(f"Menor número de linhas de dados encontrado (min_data_length): {min_data_length}")
    
    # Truncar para garantir que todos os DFs tenham o mesmo comprimento ANTES do concat
    # E que tenham pelo menos min_data_length.
    # É importante que os ÍNDICES de data/hora se sobreponham para o join='inner' funcionar.
    # Apenas pegar o .tail() pode não alinhar os timestamps se os DFs tiverem começos diferentes.
    
    # Melhor abordagem: encontrar o índice comum mais recente e o mais antigo.
    if not all_asset_features_list: # Checagem se a lista não ficou vazia por algum motivo
        logger_instance.error("all_asset_features_list está vazia antes do alinhamento de índice.")
        return None
    print(all_asset_features_list)
    # Alinhar DataFrames por um índice comum antes de concatenar
    # 1. Encontrar o primeiro timestamp comum a todos
    # 2. Encontrar o último timestamp comum a todos
    # Confiar no join='inner' do concat, mas garantir que os DFs são válidos.

    # Vamos simplificar e manter o truncamento pelo tail, mas com mais logs
    # e garantir que são DataFrames.
    
    truncated_asset_features_list = []
    for i, df_asset in enumerate(all_asset_features_list):
        if isinstance(df_asset, pd.DataFrame) and len(df_asset) >= min_data_length:
            truncated_df = df_asset.tail(min_data_length)
            #logger_instance.info(f"  DF truncado {i} ({df_asset.columns[0].split('_')[0]}): shape {truncated_df.shape}, ")
                                 #f"Index Min: {truncated_df.index.min()}, Max: {truncated_df.index.max()}")
            truncated_asset_features_list.append(truncated_df)
        else:
            asset_name_debug = df_asset.columns[0].split('_')[0] if isinstance(df_asset, pd.DataFrame) and not df_asset.empty else f"DF_{i}"
            msg = f"  DF {asset_name_debug} inválido ou muito curto (len: {len(df_asset) if isinstance(df_asset, pd.DataFrame) else 'N/A'}) para truncamento. Pulando."
            if logger_instance:
                logger_instance.warning(msg)
            else:
                print(msg)

    if not truncated_asset_features_list:
        #ogger_instance.error("Nenhum DataFrame válido restou após truncamento para concatenar.")
        return None
    
    # Se houver apenas UM DataFrame na lista, não precisa concatenar, apenas retorna ele.
    if len(truncated_asset_features_list) == 1:
        #logger_instance.info("Apenas um DataFrame de ativo processado, retornando-o diretamente.")
        combined_df = truncated_asset_features_list[0]
    else:
        #logger_instance.info(f"Concatenando {len(truncated_asset_features_list)} DataFrames de ativos com join='inner'...")
        try:
            combined_df = pd.concat(truncated_asset_features_list, axis=1, join='outer')
            print(combined_df)
        except Exception as e_concat:
            msg = f"ERRO CRÍTICO durante pd.concat: {e_concat}"
            if logger_instance:
                logger_instance.error(msg, exc_info=True)
            else:
                print(msg)
            return None
        

    combined_df.fillna(method='ffill', inplace=True)
    # Depois do ffill, ainda pode haver NaNs no início se algum ativo começar depois dos outros.
    if not combined_df.empty:
        #logger_instance.info(f"Shape após ffill: {combined_df.shape}. Buscando primeiro/último índice válido...")
        first_valid_index = combined_df.first_valid_index()
        last_valid_index = combined_df.last_valid_index()

    if pd.isna(first_valid_index) or pd.isna(last_valid_index):
        print("Não foi possível determinar first/last_valid_index após ffill.")
        return None
    
    print(f"Primeiro índice válido: {first_valid_index}, Último índice válido: {last_valid_index}")
    combined_df = combined_df.loc[first_valid_index:last_valid_index]
    print(f"Shape após fatiar por first/last valid index: {combined_df.shape}")
    
    # Um dropna final pode ser necessário se o ffill não pegou tudo (improvável, mas seguro)
    combined_df.dropna(inplace=True) 
    print(f"Shape após dropna final (pós-fatiamento): {combined_df.shape}")
    print("Imprimindo DF_COMBINED com index ")
    print(combined_df)

    #logger_instance.info(f"Tipo de combined_df após concat: {type(combined_df)}")
    if not isinstance(combined_df, pd.DataFrame):
        msg = f"combined_df NÃO é um DataFrame após concat. Tipo: {type(combined_df)}"
        if logger_instance:
            logger_instance.error(msg)
        else:
            print(msg)
        return None
    

    return combined_df
   




def fetch_single_asset_ohlcv_yf(ticker_symbol: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    """ Adaptação da sua função fetch_historical_ohlcv de financial_data_agent.py """
    print(f"Buscando dados para {ticker_symbol} com yfinance (period: {period}, interval: {interval})...")
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Para dados horários, o período máximo é geralmente 730 dias com yfinance
        # Considerar '1d' e depois reamostrar, ou usar ccxt para cripto. (Módulo de Cripto)
        if interval == '1h' and period.endswith('y') and int(period[:-1]) * 365 > 730:
             print(f"AVISO: yfinance pode limitar dados horários a 730 dias. Buscando 'max' para {interval} e depois fatiando.")
             data = ticker.history(interval=interval, period="730d") # Pega o máximo possível
        elif interval == '1d' and period.endswith('y'):
             data = ticker.history(period=period, interval=interval)
        else: # Para períodos menores ou outros intervalos
            data = ticker.history(period=period, interval=interval)

        if data.empty:
            print(f"Nenhum dado encontrado para {ticker_symbol}.")
            return pd.DataFrame()
        
        data.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume", "Adj Close": "adj_close"
        }, inplace=True)
        
        # Selecionar apenas as colunas OHLCV e garantir que o índice é DatetimeIndex UTC
        data = data[['open', 'high', 'low', 'close', 'volume']]
        if data.index.tz is None:
            data.index = data.index.tz_localize('UTC')
        else:
            data.index = data.index.tz_convert('UTC')

        # Para dados horários, yfinance pode retornar dados do fim de semana (sem volume)
        # e o último candle pode estar incompleto.
        # if interval == '1h':
        #     data = data[data['volume'] > 0] # Remover candles sem volume
            # data = data[:-1] # Remover o último candle que pode estar incompleto

        print(f"Dados coletados para {ticker_symbol}: {len(data)} linhas.")
        return data
    except Exception as e:
        print(f"Erro ao buscar dados para {ticker_symbol} com yfinance: {e}")
        return pd.DataFrame()


def calculate_all_features_for_single_asset(ohlcv_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Calcula todas as features base para um único ativo."""
    if ohlcv_df.empty: return None
    df = ohlcv_df.copy()
    print(f"Calculando features para ativo (shape inicial: {df.shape})...")

    # GARANTIR que a coluna 'close' original será preservada no DataFrame final
    if 'close' in df.columns:
        df['close'] = df['close']  # redundante, mas deixa explícito que não será sobrescrita

    # Prefer pandas_ta if available for speed/robustness; otherwise use pure-pandas fallbacks
    def sma(series: pd.Series, length: int) -> pd.Series:
        return series.rolling(window=length, min_periods=length).mean()

    def ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.ewm(alpha=1/length, adjust=False).mean()
        ma_down = down.ewm(alpha=1/length, adjust=False).mean()
        rs = ma_up / (ma_down + 1e-9)
        return 100 - (100 / (1 + rs))

    def macd(series: pd.Series):
        fast = ema(series, span=12)
        slow = ema(series, span=26)
        macd_line = fast - slow
        signal = ema(macd_line, span=9)
        hist = macd_line - signal
        out = pd.DataFrame({'macd': macd_line, 'macds': signal, 'macdh': hist})
        return out

    def true_range(df_local: pd.DataFrame) -> pd.Series:
        prev_close = df_local['close'].shift(1)
        tr1 = df_local['high'] - df_local['low']
        tr2 = (df_local['high'] - prev_close).abs()
        tr3 = (df_local['low'] - prev_close).abs()
        return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    def atr(df_local: pd.DataFrame, length: int = 14) -> pd.Series:
        tr = true_range(df_local)
        return tr.ewm(alpha=1/length, adjust=False).mean()

    def bbands_percent(series: pd.Series, length: int = 20):
        ma = series.rolling(window=length, min_periods=length).mean()
        std = series.rolling(window=length, min_periods=length).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        percent = (series - ma) / (upper - lower + 1e-9)
        return lower, ma, upper, percent

    def cci(df_local: pd.DataFrame, length: int = 37):
        tp = (df_local['high'] + df_local['low'] + df_local['close']) / 3
        ma = tp.rolling(window=length, min_periods=length).mean()
        mad = tp.rolling(window=length, min_periods=length).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        return (tp - ma) / (0.015 * (mad + 1e-9))

    def mfi(df_local: pd.DataFrame, length: int = 37):
        typical = (df_local['high'] + df_local['low'] + df_local['close']) / 3
        money_flow = typical * df_local['volume']
        positive = (typical > typical.shift(1)).astype(int)
        negative = (typical < typical.shift(1)).astype(int)
        pos_mf = (money_flow * positive).rolling(window=length, min_periods=length).sum()
        neg_mf = (money_flow * negative).rolling(window=length, min_periods=length).sum()
        mfi_val = 100 - (100 / (1 + (pos_mf / (neg_mf + 1e-9))))
        return mfi_val

    # Use pandas_ta if available; otherwise compute with fallbacks
    ta_available = ta is not None
    print(f"[dh] ta_available={ta_available}, initial columns={list(df.columns)[:10]}")
    if ta_available:
        try:
            df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
            df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
            macd_out = df.ta.macd(close='close', append=False)
            if macd_out is not None and not macd_out.empty:
                df['macd'] = macd_out.iloc[:,0]
                df['macds'] = macd_out.iloc[:,2] # signal
            df.ta.atr(length=14, append=True, col_names=('atr',))
            df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp'))
            df.ta.cci(length=37, append=True, col_names=('cci_37',))
            df['volume'] = df['volume'].astype(float)
            df.ta.mfi(length=37, close='close', high='high', low='low', volume='volume', append=True, col_names=('mfi_37',))
            adx_out = df.ta.adx(length=14, append=False)
            if adx_out is not None and not adx_out.empty:
                df['adx_14'] = adx_out.iloc[:,0]
        except Exception:
            # If pandas_ta exists but fails for any reason, fall back to pure-pandas
            ta_available = False

    if not ta_available:
        # ensure numeric types
        df['volume'] = df['volume'].astype(float)
        # sma_10
        df['sma_10'] = sma(df['close'], 10)
        # rsi_14
        df['rsi_14'] = rsi(df['close'], 14)
        # macd/macds
        macd_df = macd(df['close'])
        df['macd'] = macd_df['macd']
        df['macds'] = macd_df['macds']
        # atr
        df['atr'] = atr(df, length=14)
        # bollinger bands and percent
        bbl, bbm, bbu, bbp = bbands_percent(df['close'], length=20)
        df['bbl'] = bbl
        df['bbm'] = bbm
        df['bbu'] = bbu
        df['bbp'] = bbp
        # cci and mfi
        df['cci_37'] = cci(df, length=37)
        df['mfi_37'] = mfi(df, length=37)
        # adx is optional and expensive; set to NaN to keep schema if not available
        df['adx_14'] = np.nan

        # rolling volume zscore
        rolling_vol_mean = df['volume'].rolling(window=20).mean()
        rolling_vol_std = df['volume'].rolling(window=20).std()
        df['volume_zscore'] = (df['volume'] - rolling_vol_mean) / (rolling_vol_std + 1e-9)

        df['body_size'] = (df['close'] - df['open']).abs()

    print(f"[dh] post-fallback head:\n{df.head(3)}")

    print(f"[dh] after indicators, columns sample={list(df.columns)[:30]}")
    # ATR needs to be present before computing ATR-normalized values
    if 'atr' in df.columns:
        df.dropna(subset=['atr'], inplace=False)
    # Safe division with small epsilon
    df_atr_valid = df[df['atr'] > 1e-9].copy() if 'atr' in df.columns else pd.DataFrame()
    if df_atr_valid.empty:
        df['body_size_norm_atr'] = np.nan
        for col in COLS_TO_NORM_BY_ATR:
            df[f'{col}_div_atr'] = np.nan
    else:
        df['body_size_norm_atr'] = df['body_size'] / (df['atr'] + 1e-9)
        for col in COLS_TO_NORM_BY_ATR:
            if col in df.columns:
                df[f'{col}_div_atr'] = df[col] / (df['atr'] + 1e-9)
            else:
                df[f'{col}_div_atr'] = np.nan

    print(f"[dh] after div_atr sample cols: {', '.join([c for c in df.columns if '_div_atr' in c][:10])}")

    df['body_vs_avg_body'] = df['body_size'] / (df['body_size'].rolling(window=20).mean() + 1e-9)
    df['log_return'] = np.log(df['close'] / df['close'].shift(1))

    print(f"[dh] log_return head: {df['log_return'].head(3).tolist()}")

    sma_50_series = sma(df['close'], 50)
    df['sma_50'] = sma_50_series

    if all(col in df.columns for col in ['macd', 'macds', 'rsi_14', 'close', 'sma_50']):
        df['buy_condition_v1'] = ((df['macd'] > df['macds']) & (df['rsi_14'] > 50) & (df['close'] > df['sma_50'])).astype(int)
    else:
        df['buy_condition_v1'] = 0

    # Selecionar apenas as colunas que realmente usaremos como features base para o modelo
    # (incluindo as _div_atr e as originais que não foram normalizadas por ATR)
    # Esta lista de features é a que será passada para os scalers no script de treino.
    # E também as colunas que o rnn_predictor.py precisará ter antes de aplicar seus scalers.
    # Esta lista deve vir do config.py (BASE_FEATURE_COLS)

    # final_feature_columns = [
    #    'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 
    #    'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 
    #    'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr', 
    #    'adx_14', 'volume_zscore', 'buy_condition_v1'
    # ] # Esta é a BASE_FEATURE_COLS do config.py

    # Verificar se todas as colunas em INDIVIDUAL_ASSET_BASE_FEATURES existem
    # (INDIVIDUAL_ASSET_BASE_FEATURES deve ser igual a config.BASE_FEATURE_COLS)
    current_feature_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col in df.columns]
    missing_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col not in df.columns]
    if missing_cols:
        print(f"AVISO: Colunas de features ausentes após cálculo: {missing_cols}. Usando apenas as disponíveis: {current_feature_cols}")
    # GARANTIR que 'close' (preço original) está presente nas features finais
    if 'close' not in current_feature_cols and 'close' in df.columns:
        current_feature_cols.append('close')
    
    print(f"[dh] current_feature_cols={current_feature_cols}")
    try:
        df_final_features = df[current_feature_cols].copy()
        # only drop rows that are completely empty after feature construction
        df_final_features.dropna(how='all', inplace=True)
        print(f"Features calculadas. Shape após dropna: {df_final_features.shape}. Colunas: {df_final_features.columns.tolist()}")
        return df_final_features
    except Exception as e_inner:
        print(f"[dh] erro ao criar df_final_features: {e_inner}")
        import traceback as _tb
        _tb.print_exc()
        return None


if __name__ == '__main__':
    print("Testando data_handler_multi_asset.py...")
    
    test_assets = {
        'eth': 'ETH-USD', 
        'btc': 'BTC-USD',
        # 'aapl': 'AAPL' # Exemplo de ação
    }
    multi_asset_data = get_multi_asset_data_for_rl(
        test_assets, 
        timeframe_yf='1h', # Para teste rápido, período menor
        days_to_fetch=90   # Para teste rápido, período menor
    )

    if multi_asset_data is not None and not multi_asset_data.empty:
        print("\n--- Exemplo do DataFrame Multi-Ativo Gerado ---")
        print(multi_asset_data.head())
        print(f"\nShape: {multi_asset_data.shape}")
        print(f"\nInfo:")
        multi_asset_data.info()
    else:
        print("\nFalha ao gerar DataFrame multi-ativo.")