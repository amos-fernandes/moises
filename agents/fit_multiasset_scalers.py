"""Fit exact multi-asset scalers by fetching each asset in new-rede-a.config.ASSET_CONFIGS,
computing features via agents.data_handler_multi_asset, concatenating per-asset features
in a stable order, and fitting two MinMaxScalers: price/volume and indicators.
Saves scalers to src/model and backs up existing files.
"""
from pathlib import Path
import os
import sys
import time
import joblib
import pandas as pd
import numpy as np

# Ensure repo root on path
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from agents.data_handler_multi_asset import fetch_single_asset_ohlcv_yf, calculate_all_features_for_single_asset

# new-rede-a directory contains a hyphen; import via file path to avoid module name issues
from importlib import util
cfg_path = Path(repo_root) / 'new-rede-a' / 'config.py'
if not cfg_path.exists():
    cfg_path = Path(repo_root) / 'new-rede-a' / 'config.py'
if not cfg_path.exists():
    raise RuntimeError(f'Could not find new-rede-a config at expected path: {cfg_path}')
spec = util.spec_from_file_location('new_rede_a_config', str(cfg_path))
nr_config = util.module_from_spec(spec)
spec.loader.exec_module(nr_config)

MODEL_DIR = Path('src/model')
MODEL_DIR.mkdir(parents=True, exist_ok=True)
PV_NAME = 'rl_price_volume_atr_norm_scaler.joblib'
IND_NAME = 'rl_other_indicators_scaler.joblib'


def flatten_asset_list(asset_configs: dict):
    symbols = []
    for group in asset_configs.values():
        for s in group.keys():
            symbols.append(s)
    return symbols


def normalize_symbol_for_yf(s: str) -> str:
    # Convert formats like BTC/USD or BTC/USD to BTC-USD for yfinance
    return s.replace('/', '-').replace(' ', '')


def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + f'.bak_{int(time.time())}')
        path.rename(bak)
        print(f'Backed up {path} -> {bak}')


def main():
    # Determine assets to fetch from new-rede-a config
    asset_configs = getattr(nr_config, 'ASSET_CONFIGS', None)
    # Prefer central scripts.config MULTI_ASSET_SYMBOLS if available
    try:
        import scripts.config as sconf
    except Exception:
        sconf = None
    if asset_configs is None:
        print('No ASSET_CONFIGS found in new-rede-a config; aborting')
        return

    # Prefer MULTI_ASSET_SYMBOLS mapping from scripts.config if available (gives exact yfinance tickers)
    multi_map = None
    if sconf is not None and hasattr(sconf, 'MULTI_ASSET_SYMBOLS'):
        multi_map = getattr(sconf, 'MULTI_ASSET_SYMBOLS')
    else:
        multi_map = getattr(nr_config, 'MULTI_ASSET_SYMBOLS', None)
    per_asset_dfs = {}

    if multi_map is not None and isinstance(multi_map, dict) and len(multi_map) > 0:
        print('Using MULTI_ASSET_SYMBOLS mapping from config')
        items = list(multi_map.items())
        print(f'Assets to fetch (from MULTI_ASSET_SYMBOLS): {items}')
        for friendly, yf_ticker in items:
            yf_sym = normalize_symbol_for_yf(yf_ticker)
            print(f'Fetching {friendly} -> {yf_sym}...')
            ohlcv = fetch_single_asset_ohlcv_yf(yf_sym, period='2y', interval='1h')
            if ohlcv is None or ohlcv.empty:
                print(f'Warning: no data for {yf_sym}; skipping')
                continue
            feats = calculate_all_features_for_single_asset(ohlcv)
            if feats is None or feats.empty:
                print(f'Warning: features empty for {yf_sym}; skipping')
                continue
            prefix = friendly.replace('-', '_').replace('/', '_')
            per_asset_dfs[prefix] = feats.add_prefix(prefix + '_')
    else:
        symbols = flatten_asset_list(asset_configs)
        print(f'Assets to fetch (from ASSET_CONFIGS keys): {symbols}')
        for sym in symbols:
            # sym may be either a ticker or a friendly name; try to use it as ticker first
            yf_sym = normalize_symbol_for_yf(sym)
            print(f'Fetching {yf_sym}...')
            ohlcv = fetch_single_asset_ohlcv_yf(yf_sym, period='2y', interval='1h')
            if ohlcv is None or ohlcv.empty:
                print(f'Warning: no data for {yf_sym}; skipping')
                continue
            feats = calculate_all_features_for_single_asset(ohlcv)
            if feats is None or feats.empty:
                print(f'Warning: features empty for {yf_sym}; skipping')
                continue
            # prefix columns with asset-friendly name (sanitize)
            prefix = yf_sym.replace('-', '_').replace('/', '_')
            per_asset_dfs[prefix] = feats.add_prefix(prefix + '_')

    if not per_asset_dfs:
        print('No per-asset feature DFs collected; aborting')
        return

    # Compute a union time index and reindex each per-asset DF to that index,
    # forward/back-fill per-asset so we have continuous series for scaler fitting.
    all_indexes = [df.index for df in per_asset_dfs.values()]
    # Build a union of all DatetimeIndex objects in a robust way (union_many not available)
    if len(all_indexes) == 1:
        union_index = all_indexes[0]
    else:
        union_index = all_indexes[0]
        for idx in all_indexes[1:]:
            try:
                union_index = union_index.union(idx)
            except Exception:
                # fallback: combine as naive timestamps
                union_index = pd.DatetimeIndex(list(set(list(union_index) + list(idx))))
    # Ensure sorted unique timestamps and attempt to normalize timezone to UTC when possible
    try:
        union_index = pd.DatetimeIndex(sorted(set(union_index)))
        if any(getattr(i, 'tz', None) is not None for i in all_indexes):
            # if any source index had tzinfo, make sure union is UTC-aware
            if union_index.tz is None:
                union_index = union_index.tz_localize('UTC')
            else:
                union_index = union_index.tz_convert('UTC')
    except Exception:
        # last-resort: coerce to datetimes and sort
        union_index = pd.DatetimeIndex(sorted(pd.to_datetime(list(set(list(union_index))))))

    reindexed = {}
    for k, df in per_asset_dfs.items():
        # reindex to union index and ffill/bfill per asset
        try:
            r = df.reindex(union_index).ffill().bfill()
        except Exception:
            r = df.reset_index().set_index(pd.DatetimeIndex(df.index)).reindex(union_index).ffill().bfill()
        reindexed[k] = r

    # Now concatenate horizontally (columns are already prefixed)
    combined = pd.concat([reindexed[k] for k in sorted(reindexed.keys())], axis=1)

    if combined is None or combined.empty:
        print('Combined DataFrame empty after join; aborting')
        return

    print(f'Combined shape: {combined.shape}')

    # Determine base feature names by stripping one prefix
    sample_prefix = list(per_asset_dfs.keys())[0]
    base_cols = [c[len(sample_prefix)+1:] for c in per_asset_dfs[sample_prefix].columns]
    # Ensure a stable ordering: assets sorted, then base_cols in given order
    assets_sorted = sorted(per_asset_dfs.keys())
    ordered_cols = []
    for a in assets_sorted:
        for b in base_cols:
            col = f'{a}_{b}'
            if col in combined.columns:
                ordered_cols.append(col)

    combined = combined[ordered_cols]

    # partition PV vs IND by tokens
    pv_tokens = ('open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 'body_size_norm_atr')
    pv_cols = [c for c in ordered_cols if any(c.endswith(tok) for tok in pv_tokens)]
    ind_cols = [c for c in ordered_cols if c not in pv_cols]

    print(f'PV cols count: {len(pv_cols)}, IND cols count: {len(ind_cols)}')

    from sklearn.preprocessing import MinMaxScaler
    from pathlib import Path as _Path
    from src.utils.scaler_utils import save_scalers
    pv_scaler = MinMaxScaler()
    ind_scaler = MinMaxScaler()

    # fit (avoid dropping all rows): forward/backfill then fill remaining NaNs with column median.
    Xpv = combined[pv_cols].ffill().bfill()
    Xind = combined[ind_cols].ffill().bfill()

    # If any columns are entirely NaN, drop them and warn.
    def prune_and_fill(df, name):
        cols_all_nan = [c for c in df.columns if df[c].isna().all()]
        if cols_all_nan:
            print(f'Warning: dropping {len(cols_all_nan)} all-NaN columns from {name}: {cols_all_nan[:5]}{"..." if len(cols_all_nan)>5 else ""}')
            df = df.drop(columns=cols_all_nan)
        if df.shape[1] == 0:
            return df, cols_all_nan
        # fill remaining NaNs with median per column
        med = df.median(axis=0)
        df = df.fillna(med)
        return df, cols_all_nan

    Xpv, pv_dropped = prune_and_fill(Xpv, 'PV')
    Xind, ind_dropped = prune_and_fill(Xind, 'IND')

    if Xpv.shape[0] == 0 or Xpv.shape[1] == 0 or Xind.shape[0] == 0 or Xind.shape[1] == 0:
        print('Insufficient data/columns to fit scalers after pruning/fill; aborting')
        return

    pv_scaler.fit(Xpv.values)
    ind_scaler.fit(Xind.values)

    # Save scalers and manifest using centralized utility
    model_dir_path = _Path(MODEL_DIR)
    manifest = {
        'assets': assets_sorted,
        'base_features': base_cols,
        'ordered_cols': ordered_cols,
        'pv_feature_order': pv_cols,
        'ind_feature_order': ind_cols,
    }
    try:
        written_manifest = save_scalers(pv_scaler, ind_scaler, model_dir_path, PV_NAME, IND_NAME, manifest=manifest)
        print(f'Saved multi-asset scalers to {model_dir_path / PV_NAME} and {model_dir_path / IND_NAME}')
        print('manifest:', written_manifest)
    except Exception as e:
        print(f'Warning: could not save scalers/manifest: {e}')


if __name__ == '__main__':
    main()
