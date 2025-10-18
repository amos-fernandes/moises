import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os
# Ensure repo root is on sys.path so we can import the helper loader
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from new_rede_a_portable_import import import_env_and_config

Env, Config = import_env_and_config()

# Create 100 rows of hourly data
n = 100
rows = []
asset_symbols = getattr(Config, 'ALL_ASSET_SYMBOLS', [])
if not asset_symbols:
    asset_symbols = ['AAPL', 'MSFT']

for i in range(n):
    row = {}
    # Create one set of common features; per-asset close columns are required by the env
    for sym in asset_symbols:
        row[f"{sym}_close"] = 100.0 + i * 0.1

    # Add minimal numeric features used by new-rede-a data pipeline
    row[f"open_div_atr"] = 0.01
    row[f"close_div_atr"] = 0.02
    row[f"volume_div_atr"] = 0.5
    row[f"atr"] = 0.1
    row[f"body_size_norm_atr"] = 0.01

    # asset_id is a placeholder
    row['asset_id'] = asset_symbols[i % len(asset_symbols)]
    rows.append(row)

# Create DataFrame
df = pd.DataFrame(rows)

# Instantiate env
env = Env(df, initial_balance=1000, transaction_cost_pct=0.0)
obs, info = env.reset()
print('Initial obs shape:', obs.shape)

# Action: uniform allocation across available assets
action = np.full(len(asset_symbols), 1.0 / len(asset_symbols), dtype=float)
obs2, reward, terminated, truncated, info = env.step(action)
print('Step reward:', reward)
print('Terminated:', terminated)
print('Info:', info)
