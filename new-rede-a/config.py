# Este arquivo define valores padrão e tenta importar um conjunto central
# de configurações de `scripts.config` quando disponível. Isso permite
"""
Compatibility config for new-rede-a. This module exposes defaults and will
override them from the central `scripts.config` when that module is present.

Keep defaults small so the package can run standalone. To change behavior
project-wide, edit `scripts/config.py` and new-rede-a will pick up the values.
"""

# ---------- Defaults locais (mantidos se scripts.config não estiver presente)
WINDOW_SIZE = 30
NUM_FEATURES_PER_ASSET = 20  # Número de features calculadas para CADA ativo
L2_REG = 0.0001
PPO_LEARNING_RATE = 0.0005
RISK_FREE_RATE_ANNUAL = 0.2
REWARD_WINDOW = 252
REWARD_CALC_WINDOW = 60

# Default asset list (padrão local)
ASSET_CONFIGS = {
    "STOCKS": {
        "AAPL": {"interval": "60min"},
        "MSFT": {"interval": "60min"},
        "GOOGL": {"interval": "60min"},
        "AMZN": {"interval": "60min"},
        "NVDA": {"interval": "60min"},
        "TSLA": {"interval": "60min"},
        "PETR4.SA": {"interval": "60min"},
        "VALE3.SA": {"interval": "60min"},
    },
    "FOREX": {
        "EURUSD": {"interval": "60min"},
        "GBPUSD": {"interval": "60min"},
    },
    "CRYPTO": {
        "BTC/USD": {"interval": "60min"},
        "ETH/USD": {"interval": "60min"},
    }
}

# Default API keys placeholders (substitua por valores reais no scripts/config.py)
FINNHUB_API_KEY = None
TWELVE_DATA_API_KEY = None
ALPHA_VANTAGE_API_KEY = None

# Cache defaults
CACHE_DIR = "./data_cache"
CACHE_EXPIRATION_HOURS = 24


# ---------- Tenta importar `scripts.config` e sobrescrever defaults quando presente
try:
    import scripts.config as shared_config

    # scalar mappings
    WINDOW_SIZE = getattr(shared_config, 'WINDOW_SIZE', WINDOW_SIZE)
    NUM_FEATURES_PER_ASSET = getattr(shared_config, 'NUM_FEATURES_PER_ASSET', getattr(shared_config, 'NUM_FEATURES', NUM_FEATURES_PER_ASSET))
    L2_REG = getattr(shared_config, 'L2_REG', L2_REG)
    PPO_LEARNING_RATE = getattr(shared_config, 'PPO_LEARNING_RATE', PPO_LEARNING_RATE)
    RISK_FREE_RATE_ANNUAL = getattr(shared_config, 'RISK_FREE_RATE_ANNUAL', RISK_FREE_RATE_ANNUAL)
    REWARD_WINDOW = getattr(shared_config, 'REWARD_WINDOW', REWARD_WINDOW)
    REWARD_CALC_WINDOW = getattr(shared_config, 'REWARD_CALC_WINDOW', REWARD_CALC_WINDOW)

    # API keys
    FINNHUB_API_KEY = getattr(shared_config, 'FINNHUB_API_KEY', FINNHUB_API_KEY)
    TWELVE_DATA_API_KEY = getattr(shared_config, 'TWELVE_DATA_API_KEY', TWELVE_DATA_API_KEY)
    ALPHA_VANTAGE_API_KEY = getattr(shared_config, 'ALPHA_VANTAGE_API_KEY', ALPHA_VANTAGE_API_KEY)

    # Cache
    CACHE_DIR = getattr(shared_config, 'CACHE_DIR', CACHE_DIR)
    CACHE_EXPIRATION_HOURS = getattr(shared_config, 'CACHE_EXPIRATION_HOURS', CACHE_EXPIRATION_HOURS)

    # Assets: prefer an ASSET_CONFIGS structure if the shared config provides it.
    if hasattr(shared_config, 'ASSET_CONFIGS'):
        ASSET_CONFIGS = shared_config.ASSET_CONFIGS
    # Fallback: if shared_config has MULTI_ASSET_SYMBOLS (flat mapping), convert to a simple grouped form
    elif hasattr(shared_config, 'MULTI_ASSET_SYMBOLS'):
        multi = getattr(shared_config, 'MULTI_ASSET_SYMBOLS')
        timeframe = getattr(shared_config, 'TIMEFRAME', '60min')
        ASSET_CONFIGS = {'MIXED': {k: {'interval': timeframe} for k in multi}}

except Exception:
    # If import fails, keep the local defaults above. This is intentional so the
    # new-rede-a package remains utilizável independentemente.
    pass


# Flatten list of all symbols for convenience
ALL_ASSET_SYMBOLS = []
for group in ASSET_CONFIGS.values():
    for symbol in group.keys():
        ALL_ASSET_SYMBOLS.append(symbol)

NUM_ASSETS = len(ALL_ASSET_SYMBOLS)

# Model / network defaults (can be overridden via shared config if desired)
ASSET_CNN_FILTERS1 = getattr(globals(), 'ASSET_CNN_FILTERS1', 32)
ASSET_CNN_FILTERS2 = getattr(globals(), 'ASSET_CNN_FILTERS2', 64)
ASSET_LSTM_UNITS1 = getattr(globals(), 'ASSET_LSTM_UNITS1', 64)
ASSET_LSTM_UNITS2 = getattr(globals(), 'ASSET_LSTM_UNITS2', 32)
ASSET_DROPOUT = getattr(globals(), 'ASSET_DROPOUT', 0.2)
MHA_NUM_HEADS = getattr(globals(), 'MHA_NUM_HEADS', 4)
MHA_KEY_DIM_DIVISOR = getattr(globals(), 'MHA_KEY_DIM_DIVISOR', 2)
FINAL_DENSE_UNITS1 = getattr(globals(), 'FINAL_DENSE_UNITS1', 128)
FINAL_DENSE_UNITS2 = getattr(globals(), 'FINAL_DENSE_UNITS2', ASSET_LSTM_UNITS2)
FINAL_DROPOUT = getattr(globals(), 'FINAL_DROPOUT', 0.3)
USE_SENTIMENT_ANALYSIS = getattr(globals(), 'USE_SENTIMENT_ANALYSIS', True)

# Reward shaping defaults (aim for daily target and penalize drawdown/volatility)
REWARD_TARGET_DAILY = getattr(globals(), 'REWARD_TARGET_DAILY', 0.8642)  # default user target per day
REWARD_DRAWDOWN_PENALTY = getattr(globals(), 'REWARD_DRAWDOWN_PENALTY', 5.0)
REWARD_VOL_PENALTY = getattr(globals(), 'REWARD_VOL_PENALTY', 1.0)
REWARD_SCALE = getattr(globals(), 'REWARD_SCALE', 1.0)
PPO_LEARNING_RATE = 0.0005

RISK_FREE_RATE_ANNUAL = 0.2
