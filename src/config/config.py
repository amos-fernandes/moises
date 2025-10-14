# config.py

# --- Parâmetros de Dados ---
SYMBOL = 'BTC/USDT'  # Ativo principal para o modelo de classificação (se ainda usar)
MULTI_ASSET_SYMBOLS = { # Para o agente de portfólio RL
    'eth': 'ETH-USD',  # Chave amigável: ticker_yfinance
    'btc': 'BTC-USD',
    'ada': 'ADA-USD',
    'sol': 'SOL-USD'
}
NUM_ASSETS_PORTFOLIO = len(MULTI_ASSET_SYMBOLS) # Número de ativos no portfólio
NUM_ASSETS=4
TIMEFRAME = '1h' # Usado tanto para yfinance quanto para ccxt (se adaptar)
DAYS_OF_DATA_TO_FETCH = 365 * 2
LIMIT_PER_FETCH = 1000 # Para ccxt

# --- Parâmetros de Features e Janela ---
WINDOW_SIZE = 60

# BASE_FEATURE_COLS: Colunas calculadas para CADA ativo ANTES do escalonamento final para o modelo.
# Estas são as features que seu data_handler_multi_asset.py DEVE produzir para cada ativo.
# O rnn_predictor.py (ou a parte de features da DeepPortfolioAgentNetwork) também as calculará.
BASE_FEATURES_PER_ASSET_INPUT = [ # Renomeado para clareza
    'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr',
    'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37',
    'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr',
    'adx_14', 'volume_zscore', 'buy_condition_v1'
    # Se 'cond_compra_v1' for diferente de 'buy_condition_v1', adicione aqui.
    # Se for igual, remova a redundância. Assumindo que 'buy_condition_v1' é a correta.
]
# Nomes das colunas de preço/volume (normalizadas por ATR) que usarão o price_vol_scaler
API_PRICE_VOL_COLS = ['open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 'body_size_norm_atr']
# Nomes das colunas de indicadores (e outras) que usarão o indicator_scaler
API_INDICATOR_COLS = [col for col in BASE_FEATURES_PER_ASSET_INPUT if col not in API_PRICE_VOL_COLS]

# Número de features que CADA ativo terá após todos os cálculos e ANTES do escalonamento final.
NUM_FEATURES_PER_ASSET = len(BASE_FEATURES_PER_ASSET_INPUT)


# Nomes das colunas escaladas que o modelo RNN/RL efetivamente verá como entrada.
# Esta é a ordem que deve ser mantida após o escalonamento no data_handler e no rnn_predictor.
# E também o que o create_sequences espera.
EXPECTED_SCALED_FEATURES_FOR_MODEL = [f"{col}_scaled" for col in BASE_FEATURES_PER_ASSET_INPUT]
# NUM_FEATURES_MODEL_INPUT será len(EXPECTED_SCALED_FEATURES_FOR_MODEL), que é igual a NUM_FEATURES_PER_ASSET

# --- Parâmetros do Alvo da Predição (Para o Modelo de Classificação Supervisionado, se ainda usar) ---
PREDICTION_HORIZON = 5
PRICE_CHANGE_THRESHOLD = 0.0075

# --- Parâmetros da Rede Neural (DeepPortfolioAgentNetwork e seu AssetProcessor) ---
# Para AssetProcessor (processamento individual de ativo)
ASSET_CNN_FILTERS1 = 32
ASSET_CNN_FILTERS2 = 64
ASSET_LSTM_UNITS1 = 64
ASSET_LSTM_UNITS2 = 32  # Saída do AssetProcessor, se torna a dimensão da feature latente por ativo
ASSET_DROPOUT = 0.2

# Para DeepPortfolioAgentNetwork (camadas após processamento individual)
MHA_NUM_HEADS = 4
# key_dim da MHA será ASSET_LSTM_UNITS2 // MHA_KEY_DIM_DIVISOR
MHA_KEY_DIM_DIVISOR = 2 # Ex: 32 // 2 = 16. Garanta que ASSET_LSTM_UNITS2 seja divisível. Se não, ajuste.

# Camadas densas FINAIS DENTRO da DeepPortfolioAgentNetwork, ANTES da saída de features latentes
# ou da camada de alocação softmax (se não estiver retornando features latentes).
# `FINAL_DENSE_UNITS2_EXTRACTOR` será a dimensão das features que o extrator cospe para o SB3.
DPN_FINAL_DENSE1_UNITS = 64 # "DPN" para DeepPortfolioNetwork
DPN_LATENT_FEATURE_DIM = 32 # Saída da DPN quando output_latent_features=True. IGUAL A ASSET_LSTM_UNITS2 se não houver mais camadas após GAP.
                            # Se você adicionou Dense(final_dense_units1) e Dense(final_dense_units2) APÓS a atenção
                            # no DeepPortfolioAgentNetwork, então DPN_LATENT_FEATURE_DIM seria final_dense_units2.
                            # No nosso último design, era a saída do global_avg_pool_attention, então ASSET_LSTM_UNITS2.
                            # Vamos assumir que a saída do GAP é usada como feature latente por enquanto.
                            # DPN_LATENT_FEATURE_DIM = ASSET_LSTM_UNITS2

# Ajustando com base no seu código de `deep_portfolio.py` onde você tinha `final_dense_units1` e `final_dense_units2`
# após a atenção e antes do output de alocação.
# Estas são as camadas que produzem as features latentes para SB3.
DPN_SHARED_HEAD_DENSE1_UNITS = 128 # Corresponde a final_dense_units1 na sua DeepPortfolioAgentNetwork
DPN_SHARED_HEAD_LATENT_DIM = 32   # Corresponde a final_dense_units2, que será o self.features_dim do extrator
DPN_SHARED_HEAD_DROPOUT = 0.3

DEFAULT_EXTRACTOR_KWARGS=DPN_SHARED_HEAD_DENSE1_UNITS

# Para as cabeças de Política (Ator) e Valor (Crítico) no Stable-Baselines3 (APÓS o extrator)
# Se vazias, a saída do extrator é usada diretamente para as camadas finais de ação/valor.
POLICY_HEAD_NET_ARCH = [64]  # Ex: [64, 32] ou [] se não quiser camadas extras
VALUE_HEAD_NET_ARCH = [64]   # Ex: [64, 32] ou []

# --- Parâmetros Gerais do Modelo (se aplicável a ambos os tipos de modelo) ---
MODEL_DROPOUT_RATE = 0.3      # Você usou 0.3 na última rodada de classificação bem-sucedida
MODEL_L2_REG = 0.0001         # Você usou 0.0001 ou 0.0005

L2_REG = 0.0001 

# --- Parâmetros de Treinamento ---
# Para o modelo de classificação supervisionado (se ainda usar)
SUPERVISED_LEARNING_RATE = 0.0005
SUPERVISED_BATCH_SIZE = 128
SUPERVISED_EPOCHS = 100
LEARNING_RATE=0.0005

# Para o agente RL (PPO)
PPO_LEARNING_RATE = 0.0003 # Padrão do SB3 PPO, pode ajustar
PPO_N_STEPS = 2048
PPO_BATCH_SIZE_RL = 64 # Mini-batch size do PPO
PPO_ENT_COEF = 0.0
PPO_TOTAL_TIMESTEPS = 2048 #1000000 # Comece com menos para teste (ex: 50k-100k)

# --- Parâmetros do Ambiente RL ---
# RISK_FREE_RATE_ANNUAL = 0.02 # Taxa livre de risco anual (ex: 2%)
# REWARD_WINDOW_SHARPE = 252 * 1 # Ex: Janela de 1 ano de dados horários para Sharpe (252 dias * 24h)
                               # Ou uma janela menor como 60 ou 120 passos.
INITIAL_BALANCE = 100000
TRANSACTION_COST_PCT = 0.001 # 0.1%

# --- Caminhos para Salvar ---
MODEL_ROOT_DIR = "src/model" # Diretório raiz para todos os modelos e scalers
# Para modelo de classificação supervisionado (se mantiver)
SUPERVISED_MODEL_NAME = "ppo_custom_deep_portfolio_agent.zip"
SUPERVISED_PV_SCALER_NAME = "price_volume_atr_norm_scaler_sup.joblib"
PV_SCALER_FILENAME=SUPERVISED_PV_SCALER_NAME
SUPERVISED_IND_SCALER_NAME = "other_indicators_scaler_sup.joblib"
# Para modelo RL (agente PPO salvo pelo SB3)
RL_AGENT_MODEL_NAME = "ppo_custom_deep_portfolio_agent" # SB3 adiciona .zip
# Scalers usados para preparar dados para o DeepPortfolioAgentNetwork (que é o extrator do RL)
RL_PV_SCALER_NAME = "rl_price_volume_atr_norm_scaler.joblib" # Seus nomes descritivos
RL_INDICATOR_SCALER_NAME = "rl_other_indicators_scaler.joblib"
FINAL_DENSE_UNITS1_EXTRACTOR=DEFAULT_EXTRACTOR_KWARGS
USE_SENTIMENT_CONFIG=True

# Variaveis de backTesting
MULTI_ASSET_SYMBOLS_TEST=MULTI_ASSET_SYMBOLS

TIMEFRAME_YFINANCE_TEST='1h'

DAYS_OF_DATA_TO_FETCH_TEST=180 # para 6 meses, 365 para 1 ano

RL_AGENT_MODEL_NAME="ppo_custom_deep_portfolio_agent"

VEC_NORMALIZE_STATS_FILENAME="vec_normalize_stats.pkl"
DAYS_TO_FETCH_TEST=180

MODEL_SAVE_DIR="src/model_vec/"



ASSET_CNN_FILTERS1 = 32
ASSET_CNN_FILTERS2 = 64
ASSET_LSTM_UNITS1 = 64
ASSET_LSTM_UNITS2 = 64 # Saída do AssetProcessor LSTM2
ASSET_DROPOUT = 0.2
MHA_NUM_HEADS = 4
MHA_KEY_DIM_DIVISOR = 2
DPN_SHARED_HEAD_DENSE1_UNITS = 128


DPN_SHARED_HEAD_LATENT_DIM = 32  # <<< AJUSTE IMPORTANTE (baseado no erro de mlp_extractor)
DPN_SHARED_HEAD_DROPOUT = 0.3

# Para as cabeças da política no SB3 (após o extrator)
POLICY_HEAD_NET_ARCH = [64]
VALUE_HEAD_NET_ARCH = [64]


# --- Parâmetros de Treinamento RL (usados apenas no treino) ---
PPO_LEARNING_RATE = 0.0003
PPO_TOTAL_TIMESTEPS = 1000000

# --- Parâmetros do Ambiente ---
INITIAL_BALANCE = 100000
TRANSACTION_COST_PCT = 0.001
REWARD_WINDOW = 60
RISK_FREE_RATE_PER_STEP = 0.0



NUM_ASSETS_POLICY = 4
WINDOW_SIZE_POLICY = 60
NUM_FEATURES_PER_ASSET_POLICY = 18 #26
# Hiperparâmetros para DeepPortfolioAgentNetwork quando usada como extrator
ASSET_CNN_FILTERS1_POLICY = 32
ASSET_CNN_FILTERS2_POLICY = 64
ASSET_LSTM_UNITS1_POLICY = 64
ASSET_LSTM_UNITS2_POLICY = 32 # Esta será a dimensão das features latentes para ator/crítico
ASSET_DROPOUT_POLICY = 0.2
MHA_NUM_HEADS_POLICY = 4
MHA_KEY_DIM_DIVISOR_POLICY = 2 # Para key_dim = 32 // 2 = 16
FINAL_DENSE_UNITS1_POLICY = 128
FINAL_DENSE_UNITS2_POLICY = ASSET_LSTM_UNITS2_POLICY # A saída da dense2 SÃO as features latentes
FINAL_DROPOUT_POLICY = 0.3

MULTI_ASSET_SYMBOLS = { # Para o agente de portfólio RL
    'eth': 'ETH-USD',  # Chave amigável: ticker_yfinance
    'btc': 'BTC-USD',
    'ada': 'ADA-USD',
    'sol': 'SOL-USD'
}

MULTI_ASSET_SYMBOLS=MULTI_ASSET_SYMBOLS
CCXT_EXCHANGE_ID="binance"
CCXT_API_KEY="At0R6ebAME5rvFAFv2vfdniyamxdjIN3ouw9NcVU0jBuejrMRlpt2070wKwNGOil"
CCXT_API_SECRET="KwXApzKS3L0pbmrjT93CuDPgQ63pOrKi49TfSnU9eCBrrFkfi07362PF8Ryx7rF3"
CCXT_API_PASSWORD="M@$teraz260423"
CCXT_SANDBOX_MODE="false"




# Chaves para serviços externos
MARKET_DATA_API_KEY ="At0R6ebAME5rvFAFv2vfdniyamxdjIN3ouw9NcVU0jBuejrMRlpt2070wKwNGOil"
EXCHANGE_API_KEY="At0R6ebAME5rvFAFv2vfdniyamxdjIN3ouw9NcVU0jBuejrMRlpt2070wKwNGOil"
EXCHANGE_API_SECRET="KwXApzKS3L0pbmrjT93CuDPgQ63pOrKi49TfSnU9eCBrrFkfi07362PF8Ryx7rF3"



