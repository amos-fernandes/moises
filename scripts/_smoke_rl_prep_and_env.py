"""Smoke test: compute features, scale them, instantiate env, and run a few random steps.

This script is fast and intended to validate the pipeline end-to-end.
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np

repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from new_rede_a_portable_import import load_portable

def main():
    loader = load_portable()
    dh_mod = loader.load_module('new-rede-a.data_handler_multi_asset')
    env_mod = loader.load_module('new-rede-a.portfolio_environment')
    fs_adapter = __import__('agents.feature_scaler_adapter', fromlist=['fit_and_create_scaled'])
    fit_and_create_scaled = getattr(fs_adapter, 'fit_and_create_scaled')

    idx = pd.date_range('2023-01-01', periods=200, freq='H')
    df = pd.DataFrame({
        'open': np.linspace(100,110,200) + np.random.randn(200)*0.2,
        'high': np.linspace(100.5,110.5,200) + np.random.randn(200)*0.3,
        'low': np.linspace(99.5,109.5,200) + np.random.randn(200)*0.3,
        'close': np.linspace(100,110,200) + np.random.randn(200)*0.25,
        'volume': np.random.randint(100,1000,size=200),
    }, index=idx)

    feat_df = dh_mod.calculate_all_features_for_single_asset(df)
    scaled_df, info = fit_and_create_scaled(feat_df, save_scalers=False)
    print('Scaled columns present sample:', list(scaled_df.columns)[:30])

    # Minimal env creation uses PortfolioEnv from new-rede-a
    EnvClass = getattr(env_mod, 'PortfolioEnv')
    # Create env with a single asset's scaled df wrapped as list to match expected multi-asset interface
    try:
        env = EnvClass(observations_df_list=[scaled_df], initial_balance=10000)
    except TypeError:
        # try alternative constructor signature
        env = EnvClass(scaled_features_by_asset=[scaled_df], initial_balance=10000)

    obs = env.reset()
    print('initial obs shape', np.array(obs).shape)
    for i in range(5):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        print(f'step {i} reward {reward} info_keys {list(info.keys())}')
        if done:
            break

if __name__ == '__main__':
    main()
