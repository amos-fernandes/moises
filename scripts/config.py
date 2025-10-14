# --- Parâmetros de Configuração ---
# Dados
SYMBOL = 'ETH/USDT'  # MUDAMOS PARA ETH/USDT PARA TESTE
MULTI_ASSET_SYMBOLS = {
    'crypto_eth': 'ETH-USD',  # yfinance ticker para ETH/USD
    'crypto_ada': 'ADA-USD',  # yfinance ticker para ADA/USD
    'stock_aapl': 'AAPL',     # NASDAQ
    'stock_petr': 'PETR4.SA'  # B3
} # Use os tickers corretos para yfinance ou ccxt
TIMEFRAME_YFINANCE = '1h' # yfinance suporta '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
# Para '1h', yfinance só retorna os últimos 730 dias. Para mais dados, use '1d'.
# Se usar ccxt, TIMEFRAME = '1h' como antes.
DAYS_TO_FETCH = 365 * 2 # 2 anos

# Lista das features base que você quer calcular para CADA ativo
# (as 19 que definimos antes)
INDIVIDUAL_ASSET_BASE_FEATURES = [
    'open', 'high', 'low', 'close', 'volume', # OHLCV originais são necessários para os cálculos
    'sma_10', 'rsi_14', 'macd', 'macds', 'atr', 'bbp', 'cci_37', 'mfi_37', 'adx_14',
    'volume_zscore', 'body_size', 'body_size_norm_atr', 'body_vs_avg_body',
    'log_return', 'buy_condition_v1', # 'sma_50' é calculada dentro de buy_condition_v1
    # As colunas _div_atr serão criadas a partir destas
]

# Features que serão normalizadas pelo ATR
COLS_TO_NORM_BY_ATR = ['open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd', 'body_size']


TIMEFRAME = '1h'
DAYS_OF_DATA_TO_FETCH = 365 * 2
LIMIT_PER_FETCH = 1000

# Features e Janela
WINDOW_SIZE = 60

# BASE_FEATURE_COLS define as features *originais* ou *derivadas diretamente dos dados brutos*
# que serão usadas ANTES do escalonamento específico para o modelo no script de treino,
# e também as features que o rnn_predictor.py precisará calcular/ter ANTES de aplicar SEUS scalers.
BASE_FEATURE_COLS = [
    'open_div_atr',         # Feature 1 (Preço normalizado)
    'high_div_atr',         # Feature 2 (Preço normalizado)
    'low_div_atr',          # Feature 3 (Preço normalizado)
    'close_div_atr',        # Feature 4 (Preço normalizado)
    'volume_div_atr',       # Feature 5 (Volume normalizado)
    'log_return',           # Feature 6 (Momento)
    'rsi_14',               # Feature 7 (Oscilador)
    'atr',                  # Feature 8 (Volatilidade - será escalada)
    'bbp',                  # Feature 9 (%B - será escalado)
    'cci_37',               # Feature 10 (Oscilador - será escalado)
    'mfi_37',               # Feature 11 (Volume/Oscilador - será escalado)
    'body_size_norm_atr',   # Feature 12 (Candle normalizado)
    'body_vs_avg_body',     # Feature 13 (Candle relativo)
    'macd',                 # Feature 14 (Linha MACD - será escalada)
    'sma_10_div_atr',       # Feature 15 (Preço normalizado)
    'adx_14',               # Feature 16 (Força da Tendência - será escalada)
    'volume_zscore',        # Feature 17 (Volume relativo - será escalado)
    'buy_condition_v1',     # Feature 18 (Condição Composta - binária, pode ou não ser escalada)
    # 'cond_compra_v1',    # Parece ser um duplicado de 'buy_condition_v1', remova se for.
                            # Se for diferente, mantenha, mas garanta que está sendo calculada.
]
# REMOVA as colunas _scaled de BASE_FEATURE_COLS. Elas são o *resultado* do escalonamento.
# BASE_FEATURE_COLS são as features ANTES do último passo de escalonamento para o modelo.

# Vamos assumir que cond_compra_v1 e buy_condition_v1 são a mesma.
# Se forem diferentes, você precisará ajustar.
if 'cond_compra_v1' in BASE_FEATURE_COLS and 'buy_condition_v1' in BASE_FEATURE_COLS:
    if 'cond_compra_v1' == 'buy_condition_v1': # Redundante se nomes iguais, mas para clareza
         print("AVISO em config.py: 'cond_compra_v1' e 'buy_condition_v1' parecem ser a mesma feature. Verifique.")
         # Decida qual manter ou se são realmente diferentes. Por ora, vou assumir que você quer ambas se estiverem listadas.
         # Se forem a mesma, remova uma. Vou remover 'cond_compra_v1' se 'buy_condition_v1' for a oficial.
         # BASE_FEATURE_COLS.remove('cond_compra_v1') # Exemplo


NUM_FEATURES = len(BASE_FEATURE_COLS) # ATUALIZADO AUTOMATICAMENTE

# Alvo da Predição (Target)
PREDICTION_HORIZON = 5
PRICE_CHANGE_THRESHOLD = 0.0075 # Você aumentou, OK.

# Modelo RNN
LSTM_UNITS = [64, 64]  # Boa escolha para mais features
DENSE_UNITS = 32
DROPOUT_RATE = 0.3     # Bom para regularizar um modelo maior
LEARNING_RATE = 0.0005 # LR inicial para ReduceLROnPlateau
L2_REG = 0.0001        # Regularização L2 leve

# Treinamento
BATCH_SIZE = 128
EPOCHS = 100 # Deixe EarlyStopping controlar

# Caminhos para Salvar
MODEL_SAVE_DIR = "app/model" 
MODEL_NAME = "model.h5"
# Nomes de scaler mais descritivos que você sugeriu:
PRICE_VOL_SCALER_NAME = "price_volume_atr_norm_scaler.joblib"
INDICATOR_SCALER_NAME = "other_indicators_scaler.joblib"

# EXPECTED_SCALED_FEATURES_FOR_MODEL define os nomes das colunas APÓS o escalonamento
# que são usadas para criar as sequências e alimentar o modelo no script de treino.
# E também o que o rnn_predictor.py DEVE produzir após aplicar seus scalers carregados.
EXPECTED_SCALED_FEATURES_FOR_MODEL = [f"{col}_scaled" for col in BASE_FEATURE_COLS]
# ^^^ IMPORTANTE: Esta linha assume que TODAS as features em BASE_FEATURE_COLS
#     serão escaladas e terão o sufixo _scaled.
#     Se 'rsi_14', 'bbp', 'buy_condition_v1' não forem escaladas ou tiverem
#     outro tratamento, esta lista precisa ser ajustada manualmente.
#     Exemplo: Se 'buy_condition_v1' é binária e não escalada:
#     EXPECTED_SCALED_FEATURES_FOR_MODEL = [f"{col}_scaled" for col in BASE_FEATURE_COLS if col != 'buy_condition_v1'] + ['buy_condition_v1']
#     Por simplicidade, vamos assumir que todas são escaladas por enquanto.
EXPECTED_FEATURES_ORDER = EXPECTED_SCALED_FEATURES_FOR_MODEL

INDIVIDUAL_ASSET_BASE_FEATURES = EXPECTED_FEATURES_ORDER

MODEL_SAVE_DIR = "app/model"
PRICE_VOL_SCALER_NAME = "price_volume_atr_norm_scaler.joblib"
INDICATOR_SCALER_NAME = "other_indicators_scaler.joblib"