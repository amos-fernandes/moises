from typing import List, Tuple
import pandas as pd
import numpy as np
import ccxt
import pandas_ta as ta
from datetime import datetime, timedelta, timezone # Adicionado timezone

# Importa constantes do config.py
from config import PREDICTION_HORIZON, PRICE_CHANGE_THRESHOLD, BASE_FEATURE_COLS, WINDOW_SIZE


# Novos inidcadores mover para config
# Períodos para as novas MAs 
SHORT_MA_PERIOD = 10 # Exemplo: SMA de 10 períodos
LONG_MA_PERIOD = 50  # Exemplo: SMA de 50 períodos

# Períodos para ADX
ADX_PERIOD = 14

# Níveis para Osciladores Extremos
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
STOCH_OVERBOUGHT = 80 # Para Estocástico %K
STOCH_OVERSOLD = 20
CCI_OVERBOUGHT = 100
CCI_OVERSOLD = -100
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20

# Período para Média Móvel do Volume
VOLUME_AVG_PERIOD = 20

#Fim NI

def fetch_ohlcv_data_ccxt(symbol: str, timeframe: str, days_to_fetch: int, limit_per_call: int = 1000) -> pd.DataFrame:
    exchange = ccxt.binance()
    print(f"Buscando dados para {symbol} na {exchange.id} com timeframe {timeframe}...")
    all_ohlcv = []
    since_dt = datetime.now(timezone.utc) - timedelta(days=days_to_fetch)
    since = exchange.parse8601(since_dt.isoformat())
    
    while True:
        try:
            print(f"Buscando {limit_per_call} candles desde {exchange.iso8601(since)}...")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit_per_call)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            last_timestamp_in_batch = ohlcv[-1][0]
            since = last_timestamp_in_batch + exchange.rateLimit 
            print(f"Coletados {len(ohlcv)} candles. Último: {exchange.iso8601(last_timestamp_in_batch)}. Total: {len(all_ohlcv)}")
            if len(ohlcv) < limit_per_call: break
            # Condição de parada mais robusta
            processed_days = (last_timestamp_in_batch - exchange.parse8601(since_dt.isoformat())) / (1000 * 60 * 60 * 24)
            if processed_days >= days_to_fetch:
                 break
        except ccxt.NetworkError as e:
            print(f"Erro de rede CCXT: {e}. Tentando novamente em 5s...")
            # Adicionar um retry real aqui seria bom, ou time.sleep(5)
        except ccxt.ExchangeError as e:
            print(f"Erro da Exchange CCXT: {e}. Parando busca.")
            break
        except Exception as e:
            print(f"Erro inesperado no fetch: {e}. Parando busca.")
            break
            
    if not all_ohlcv:
        raise ValueError("Nenhum dado OHLCV foi coletado.")
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    print(f"Total de {len(df)} candles OHLCV coletados para {symbol}.")
    return df

def calculate_technical_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    print("Calculando indicadores técnicos...")
    df = ohlcv_df.copy()
    if ta:
        # Indicadores base 
        df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
        df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
        df.ta.log_return(length=14, close='close', append=True, col_names=('log_return',))
        df.ta.macd(close='close', append=True, col_names=('macd', 'macdh', 'macds')) # Pega só 'macd' depois
        df.ta.atr(length=14, append=True, col_names=('atr',))
        df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp')) # Pega só 'bbp' depois
        df.ta.cci(length=37, append=True, col_names=('cci_37',)) # Usando o período do exemplo
        df.ta.mfi(length=37, append=True, col_names=('mfi_37',)) # Usando o período do exemplo
        df['body_size'] = abs(df['close'] - df['open'])
        df['body_size_norm_atr'] = df['body_size'] / (df['atr'] + 1e-7)
        avg_body_period = 12 # Do exemplo do EA
        df['avg_body_prev_12'] = df['body_size'].shift(1).rolling(window=avg_body_period).mean() # Média dos 12 corpos anteriores
        df['body_vs_avg_body'] = df['body_size'] / (df['avg_body_prev_12'] + 1e-7)
        # Normalização pelo ATR (APÓS cálculo de ATR e outros indicadores base)
        # Garantir que 'atr' não é zero ou NaN antes da divisão
        df.dropna(subset=['atr'], inplace=True) # Remove linhas onde ATR não pôde ser calculado
        df = df[df['atr'] > 1e-7] # Remove linhas com ATR muito pequeno ou zero
        df['open_div_atr'] = df['open'] / df['atr']
        df['high_div_atr'] = df['high'] / df['atr']
        df['low_div_atr'] = df['low'] / df['atr']
        df['close_div_atr'] = df['close'] / df['atr']
        df['close_div_atr'] = df['close'] / df['atr']
        df['volume_div_atr'] = df['volume'] / df['atr'] 
        # Assegura que as colunas base para estas normalizações existam
        if 'sma_10' in df.columns:
            df['sma_10_div_atr'] = df['sma_10'] / df['atr']
        if 'macd' in df.columns: # 'macd' é a linha principal do MACD
            df['macd_div_atr'] = df['macd'] / df['atr']
       
        # ------ Novos indicadores -- #
        # --- Indicadores Base anteriores ---
        if 'sma_10' in BASE_FEATURE_COLS or 'sma_10_div_atr' in BASE_FEATURE_COLS: # Só calcula se for usar
            df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
        if 'rsi_14' in BASE_FEATURE_COLS:
            df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
        
        # Calcula componentes MACD, mesmo que só use 'macd' depois
        if 'macd' in BASE_FEATURE_COLS or 'macd_div_atr' in BASE_FEATURE_COLS or 'macd_cross_signal' in BASE_FEATURE_COLS:
            macd_results = df.ta.macd(close='close', append=False) 
            if macd_results is not None and not macd_results.empty:
                df['macd'] = macd_results.iloc[:,0] # Linha MACD
                df['macds'] = macd_results.iloc[:,1] # Linha de Sinal MACD
                # df['macdh'] = macd_results.iloc[:,2] # Histograma MACD (opcional)
        
        if 'atr' in BASE_FEATURE_COLS or any('_div_atr' in col for col in BASE_FEATURE_COLS):
            df.ta.atr(length=14, append=True, col_names=('atr',))
        
        if 'bbp' in BASE_FEATURE_COLS or 'dist_bbu_norm_atr' in BASE_FEATURE_COLS or 'dist_bbl_norm_atr' in BASE_FEATURE_COLS:
            df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp'))

        if 'cci_37' in BASE_FEATURE_COLS:
            df.ta.cci(length=37, append=True, col_names=('cci_37',))
        
        if 'mfi_37' in BASE_FEATURE_COLS:
            df.ta.mfi(length=37, append=True, col_names=('mfi_37',))

        if 'body_size_norm_atr' in BASE_FEATURE_COLS or 'body_vs_avg_body' in BASE_FEATURE_COLS:
            if 'open' in df.columns and 'close' in df.columns:
                df['body_size'] = abs(df['close'] - df['open'])

        # --- 1. Cruzamentos de Médias Móveis ---
        if 'ma_short' not in df.columns and ('ma_cross_signal' in BASE_FEATURE_COLS or 'ma_diff_norm_atr' in BASE_FEATURE_COLS):
            df.ta.sma(length=SHORT_MA_PERIOD, close='close', append=True, col_names=('ma_short',))
        if 'ma_long' not in df.columns and ('ma_cross_signal' in BASE_FEATURE_COLS or 'ma_diff_norm_atr' in BASE_FEATURE_COLS):
            df.ta.sma(length=LONG_MA_PERIOD, close='close', append=True, col_names=('ma_long',))

        if 'ma_cross_signal' in BASE_FEATURE_COLS and 'ma_short' in df.columns and 'ma_long' in df.columns:
            df['ma_short_prev'] = df['ma_short'].shift(1)
            df['ma_long_prev'] = df['ma_long'].shift(1)
            # Sinal de Compra: curta cruza longa para cima
            buy_cross = (df['ma_short_prev'] < df['ma_long_prev']) & (df['ma_short'] > df['ma_long'])
            # Sinal de Venda: curta cruza longa para baixo
            sell_cross = (df['ma_short_prev'] > df['ma_long_prev']) & (df['ma_short'] < df['ma_long'])
            df['ma_cross_signal'] = 0
            df.loc[buy_cross, 'ma_cross_signal'] = 1  # Compra
            df.loc[sell_cross, 'ma_cross_signal'] = -1 # Venda (ou use 2 para outra classe)
            print("TA: Feature 'ma_cross_signal' calculada.")

        if 'ma_diff_norm_atr' in BASE_FEATURE_COLS and 'ma_short' in df.columns and 'ma_long' in df.columns and 'atr' in df.columns:
            df['ma_diff'] = df['ma_short'] - df['ma_long']
            df['ma_diff_norm_atr'] = df['ma_diff'] / (df['atr'] + 1e-9) # Evitar divisão por zero no ATR
            print("TA: Feature 'ma_diff_norm_atr' calculada.")

        # --- 2. Força da Tendência (ADX) ---
        if 'adx_14' in BASE_FEATURE_COLS or 'adx_trend_signal' in BASE_FEATURE_COLS:
            adx_results = df.ta.adx(length=ADX_PERIOD, append=False)
            if adx_results is not None and not adx_results.empty:
                df['adx_14'] = adx_results.iloc[:,0]  # ADX
                df['dmp_14'] = adx_results.iloc[:,1]  # +DI ou DMP
                df['dmn_14'] = adx_results.iloc[:,2]  # -DI ou DMN
                if 'adx_trend_signal' in BASE_FEATURE_COLS:
                    df['adx_trend_signal'] = 0
                    # ADX > 20-25 geralmente indica tendência. +DI > -DI = tendência de alta.
                    strong_uptrend = (df['adx_14'] > 20) & (df['dmp_14'] > df['dmn_14'])
                    strong_downtrend = (df['adx_14'] > 20) & (df['dmn_14'] > df['dmp_14'])
                    df.loc[strong_uptrend, 'adx_trend_signal'] = 1
                    df.loc[strong_downtrend, 'adx_trend_signal'] = -1
                print("TA: Features ADX calculadas.")

        # --- 3. Níveis de Suporte/Resistência Dinâmicos (Distância para BBands normalizada por ATR) ---
        if 'dist_bbu_norm_atr' in BASE_FEATURE_COLS and 'close' in df.columns and 'bbu' in df.columns and 'atr' in df.columns:
            df['dist_bbu_norm_atr'] = (df['bbu'] - df['close']) / (df['atr'] + 1e-9)
            print("TA: Feature 'dist_bbu_norm_atr' calculada.")
        if 'dist_bbl_norm_atr' in BASE_FEATURE_COLS and 'close' in df.columns and 'bbl' in df.columns and 'atr' in df.columns:
            df['dist_bbl_norm_atr'] = (df['close'] - df['bbl']) / (df['atr'] + 1e-9)
            print("TA: Feature 'dist_bbl_norm_atr' calculada.")

        # --- 4. Osciladores em Níveis Extremos ---
        # Estocástico (preciso calcular primeiro)
        if 'stoch_k_extreme' in BASE_FEATURE_COLS or 'stoch_d_extreme' in BASE_FEATURE_COLS:
            stoch_results = df.ta.stoch(k=14, d=3, smooth_k=3, append=False) # Configurações padrão
            if stoch_results is not None and not stoch_results.empty:
                df['stoch_k'] = stoch_results.iloc[:,0] # %K
                df['stoch_d'] = stoch_results.iloc[:,1] # %D
                if 'stoch_k_extreme' in BASE_FEATURE_COLS:
                    df['stoch_k_extreme'] = 0
                    df.loc[df['stoch_k'] > STOCH_OVERBOUGHT, 'stoch_k_extreme'] = 1  # Sobrecomprado
                    df.loc[df['stoch_k'] < STOCH_OVERSOLD, 'stoch_k_extreme'] = -1 # Sobrevendido
                print("TA: Features Estocástico e stoch_k_extreme calculadas.")
                
        if 'rsi_extreme' in BASE_FEATURE_COLS and 'rsi_14' in df.columns:
            df['rsi_extreme'] = 0
            df.loc[df['rsi_14'] > RSI_OVERBOUGHT, 'rsi_extreme'] = 1
            df.loc[df['rsi_14'] < RSI_OVERSOLD, 'rsi_extreme'] = -1
            print("TA: Feature 'rsi_extreme' calculada.")

        if 'cci_extreme' in BASE_FEATURE_COLS and 'cci_37' in df.columns:
            df['cci_extreme'] = 0
            df.loc[df['cci_37'] > CCI_OVERBOUGHT, 'cci_extreme'] = 1
            df.loc[df['cci_37'] < CCI_OVERSOLD, 'cci_extreme'] = -1
            print("TA: Feature 'cci_extreme' calculada.")

        if 'mfi_extreme' in BASE_FEATURE_COLS and 'mfi_37' in df.columns:
            df['mfi_extreme'] = 0
            df.loc[df['mfi_37'] > MFI_OVERBOUGHT, 'mfi_extreme'] = 1
            df.loc[df['mfi_37'] < MFI_OVERSOLD, 'mfi_extreme'] = -1
            print("TA: Feature 'mfi_extreme' calculada.")

        # --- 5. Sinais Combinados (Simples) ---
        # Ex: RSI sobrevendido E MACD cruzou para cima recentemente?
        if 'rsi_macd_buy_combo' in BASE_FEATURE_COLS and 'rsi_14' in df.columns and 'macd' in df.columns and 'macds' in df.columns:
            rsi_is_oversold = df['rsi_14'] < RSI_OVERSOLD
            # MACD cruzou sinal para cima no candle anterior ou atual
            macd_crossed_up = (df['macd'].shift(1) < df['macds'].shift(1)) & (df['macd'] > df['macds'])
            df['rsi_macd_buy_combo'] = (rsi_is_oversold & macd_crossed_up).astype(int)
            print("TA: Feature 'rsi_macd_buy_combo' calculada.")

        # --- 6. Volume Anômalo ---
        if 'volume_anom_signal' in BASE_FEATURE_COLS and 'volume' in df.columns:
            df['volume_avg'] = df['volume'].rolling(window=VOLUME_AVG_PERIOD).mean()
            # Sinal se volume atual > 2x a média
            df['volume_anom_signal'] = (df['volume'] > 2 * df['volume_avg']).astype(int)
            print("TA: Feature 'volume_anom_signal' calculada.")
            
        # --- Features de Corpo de Candle (já tinha antes, mas garantindo que serão usadas se estiverem em BASE_FEATURE_COLS) ---
        if 'body_size_norm_atr' in BASE_FEATURE_COLS:
            if 'body_size' in df.columns and 'atr' in df.columns:
                # Re-checar se ATR é válido, pois body_size pode ter menos NaNs
                temp_df_bs = df[['body_size', 'atr']].copy()
                temp_df_bs.dropna(subset=['atr'], inplace=True)
                temp_df_bs = temp_df_bs[temp_df_bs['atr'] > 1e-9]
                if not temp_df_bs.empty:
                    df['body_size_norm_atr'] = temp_df_bs['body_size'] / temp_df_bs['atr']
                # print("TA: body_size_norm_atr (re)calculado/verificado.")
            # else:
                # print("AVISO: 'body_size' ou 'atr' ausente para 'body_size_norm_atr'.")
                
        if 'body_vs_avg_body' in BASE_FEATURE_COLS:
            if 'body_size' in df.columns:
                if 'avg_body_prev' not in df.columns: # Evitar recalcular se já existe
                    df['avg_body_prev'] = df['body_size'].shift(1).rolling(window=12).mean()
                df['body_vs_avg_body'] = df['body_size'] / (df['avg_body_prev'] + 1e-7)
                # print("TA: body_vs_avg_body (re)calculado/verificado.")
            # else:
                # print("AVISO: 'body_size' ausente para 'body_vs_avg_body'.")

        # --- Features Derivadas _div_atr (já tinha antes, garantindo que serão usadas se estiverem em BASE_FEATURE_COLS) ---
        df.dropna(subset=['atr'], inplace=True) 
        df = df[df['atr'] > 1e-9] 

        if 'open_div_atr' in BASE_FEATURE_COLS and 'open' in df.columns: df['open_div_atr'] = df['open'] / df['atr']
        if 'high_div_atr' in BASE_FEATURE_COLS and 'high' in df.columns: df['high_div_atr'] = df['high'] / df['atr']
        if 'low_div_atr' in BASE_FEATURE_COLS and 'low' in df.columns: df['low_div_atr'] = df['low'] / df['atr']
        if 'close_div_atr' in BASE_FEATURE_COLS and 'close' in df.columns: df['close_div_atr'] = df['close'] / df['atr']
        if 'volume_div_atr' in BASE_FEATURE_COLS and 'volume' in df.columns: df['volume_div_atr'] = df['volume'] / df['atr'] 
        if 'sma_10_div_atr' in BASE_FEATURE_COLS and 'sma_10' in df.columns: df['sma_10_div_atr'] = df['sma_10'] / df['atr']
        if 'macd_div_atr' in BASE_FEATURE_COLS and 'macd' in df.columns: df['macd_div_atr'] = df['macd'] / df['atr']

        if 'log_return_1' in BASE_FEATURE_COLS and 'close' in df.columns:
            df['log_return_1'] = np.log(df['close'] / df['close'].shift(1))

        # Novas features AD e volume
        rolling_vol_mean = df['volume'].rolling(window=20).mean()
        rolling_vol_std = df['volume'].rolling(window=20).std()
        df['volume_zscore'] = (df['volume'] - rolling_vol_mean) / (rolling_vol_std + 1e-7)

        # Certifique-se que MACD, MACDS, SMA_50 já foram calculados
        df.ta.sma(length=50, close='close', append=True, col_names=('sma_50',)) 
        df['buy_condition_v1'] = ((df['macd'] > df['macds']) & (df['rsi_14'] > 50) & (df['close'] > df['sma_50'])).astype(int)

        df['cond_compra_v1'] = ((df['macd'] > df['macds']) & (df['rsi_14'] > 50) & (df['close'] > df.ta.sma(length=50, append=False))).astype(int)
        
        

        df.dropna(inplace=True) 
        
        final_cols_present = [col for col in BASE_FEATURE_COLS if col in df.columns]
        if len(final_cols_present) != len(BASE_FEATURE_COLS):
            missing = list(set(BASE_FEATURE_COLS) - set(final_cols_present))
            print(f"ALERTA: Após todos os cálculos, colunas de BASE_FEATURE_COLS estão faltando: {missing}")
            print(f"Verifique os cálculos e se as colunas base para eles (open, high, low, close, volume) existem no input.")
            print(f"Colunas disponíveis: {df.columns.tolist()}")
            # raise ValueError(f"Nem todas as features base foram geradas: {missing}")

        # Selecionar apenas as colunas que realmente existem e estão em BASE_FEATURE_COLS
        # para evitar erros se alguma não pôde ser calculada.
        # O script de treino verificará se todas as BASE_FEATURE_COLS existem antes de escalar.
        existing_base_features = [col for col in BASE_FEATURE_COLS if col in df.columns]
        print(f"Indicadores técnicos e features derivadas calculadas. Features retornadas: {existing_base_features}")
        return df[existing_base_features + (['open', 'high', 'low', 'close', 'volume'] if not any(c in existing_base_features for c in ['open', 'high', 'low', 'close', 'volume']) else [])] # Garante que OHLCV original está lá para calculate_targets, se não for parte das features



        # ---- Fim  NI

        # Remover todos os NaNs restantes gerados pelos indicadores
        df.dropna(inplace=True) 
        print("Indicadores técnicos calculados e features normalizadas pelo ATR criadas.")
    else:
        print("pandas_ta não disponível. Verifique a instalação.")
    return df

def calculate_targets(df: pd.DataFrame, horizon: int, threshold: float) -> pd.DataFrame:
    print("Criando coluna alvo para predição...")
    data = df.copy()
    data['future_price'] = data['close'].shift(-horizon)
    data['price_change_pct'] = (data['future_price'] - data['close']) / data['close']
    data['target'] = (data['price_change_pct'] > threshold).astype(int)
    data.dropna(subset=['future_price', 'price_change_pct', 'target'], inplace=True)
    print(f"Distribuição do Alvo:\n{data['target'].value_counts(normalize=True, dropna=False)}")
    return data

def create_sequences(data: pd.DataFrame, target_col_name: str, window_size: int, feature_col_names: List[str]) -> tuple[np.ndarray, np.ndarray]:
    print(f"Criando sequências com window_size={window_size} usando features: {feature_col_names}")
    X_list, y_list = [], []
    
    # Verificar se todas as feature_col_names e target_col_name existem no DataFrame
    required_cols = feature_col_names + [target_col_name]
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"Colunas ausentes no DataFrame para criar sequências: {missing_cols}. Colunas disponíveis: {data.columns.tolist()}")

    # Usar .values pode ser mais rápido para DataFrames grandes, mas indexar por nome é mais seguro
    feature_values = data[feature_col_names].values
    target_values = data[target_col_name].values

    for i in range(len(feature_values) - window_size + 1): # Ajuste no loop para incluir o último elemento possível
        X_list.append(feature_values[i : i + window_size])
        y_list.append(target_values[i + window_size - 1]) # Alvo correspondente ao final da janela

    X = np.array(X_list)
    y = np.array(y_list)
    print(f"Shape de X (sequências): {X.shape}, Shape de y (alvos): {y.shape}")
    return X, y