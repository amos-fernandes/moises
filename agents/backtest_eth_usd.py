import os
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
import datetime as dt
import sys
import types

# Ensure repository root is on sys.path so relative imports like `agents.*` work
from pathlib import Path as _Path
_repo_root = str(_Path(__file__).resolve().parents[1])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Lightweight agents.config fallback for import-time safety
if 'agents.config' not in sys.modules:
    fake_cfg = types.ModuleType('agents.config')
    fake_cfg.BASE_FEATURES_PER_ASSET_INPUT = [
        'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr',
        'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37',
        'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr',
        'adx_14', 'volume_zscore', 'buy_condition_v1'
    ]
    fake_cfg.WINDOW_SIZE = 60
    fake_cfg.MODEL_ROOT_DIR = 'src/model'
    fake_cfg.RL_PV_SCALER_NAME = 'rl_price_volume_atr_norm_scaler.joblib'
    fake_cfg.RL_INDICATOR_SCALER_NAME = 'rl_other_indicators_scaler.joblib'
    fake_cfg.EXPECTED_SCALED_FEATURES_FOR_MODEL = [f"{c}_scaled" for c in fake_cfg.BASE_FEATURES_PER_ASSET_INPUT]
    fake_cfg.API_PRICE_VOL_COLS = [
        'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 'body_size_norm_atr'
    ]
    sys.modules['agents.config'] = fake_cfg

from agents.data_handler_multi_asset import fetch_single_asset_ohlcv_yf, calculate_all_features_for_single_asset
from agents.feature_scaler_adapter import fit_and_create_scaled
import agents.config as cfg


MODEL_DIR = Path('src/model')
LOGS_DIR = Path('logs')
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def simple_signal_generator(features_df: pd.DataFrame) -> pd.Series:
    """Generate simple buy/sell signals from features."""
    if 'buy_condition_v1' in features_df.columns:
        return features_df['buy_condition_v1'].fillna(0).astype(int)
    if 'log_return' in features_df.columns:
        return ((features_df['log_return'] > 0) & (features_df['log_return'].rolling(3).mean() > 0)).astype(int).fillna(0)
    return pd.Series(0, index=features_df.index)


def run_backtest_from_features(feats: pd.DataFrame, start_capital=100000.0, target_annual_vol=0.6,
                               stop_loss_pct=0.08, partial_tp_pct=0.10):
    """Lightweight backtest engine using signals in feats and simple execution model."""
    signals = simple_signal_generator(feats)
    fee = 0.001
    slippage = 0.001
    cash = start_capital
    position = 0.0
    equity_curve = []
    trades = []

    df = feats.copy()
    df['signal'] = signals
    df['open_next'] = df.get('close').shift(-1)

    if 'log_return' in df.columns:
        vol_step = df['log_return'].rolling(window=24).std().bfill()
    else:
        vol_step = pd.Series(0.02, index=df.index)
    steps_per_year = 24 * 365

    for idx, row in df.iterrows():
        price = row.get('close', np.nan)
        if pd.isna(price):
            equity_curve.append(cash)
            continue
        exec_price = row.get('open_next', price)
        realized_vol = vol_step.loc[idx] if idx in vol_step.index else 0.02
        if realized_vol <= 0:
            frac = 0.0
        else:
            frac = min(1.0, (target_annual_vol / max(1e-6, realized_vol * (steps_per_year ** 0.5))))
        frac = max(0.0, min(frac, 1.0))

        if row['signal'] == 1 and position == 0:
            alloc = cash * frac
            if alloc > 0 and exec_price > 0:
                qty = (alloc * (1 - fee - slippage)) / exec_price
                position = qty
                cash -= alloc
                trades.append({'timestamp': idx, 'side': 'buy', 'price': exec_price, 'qty': qty, 'alloc': alloc})

        if position > 0:
            entry_price = trades[-1]['price'] if trades and trades[-1]['side'] == 'buy' else exec_price
            if price <= entry_price * (1 - stop_loss_pct):
                proceeds = position * exec_price * (1 - fee - slippage)
                trades.append({'timestamp': idx, 'side': 'sell', 'price': exec_price, 'qty': position, 'reason': 'stop_loss'})
                cash += proceeds
                position = 0.0
            else:
                if price >= entry_price * (1 + partial_tp_pct):
                    sell_qty = position * 0.5
                    proceeds = sell_qty * exec_price * (1 - fee - slippage)
                    trades.append({'timestamp': idx, 'side': 'sell', 'price': exec_price, 'qty': sell_qty, 'reason': 'partial_tp'})
                    cash += proceeds
                    position -= sell_qty

        if row['signal'] == 0 and position > 0:
            proceeds = position * exec_price * (1 - fee - slippage)
            trades.append({'timestamp': idx, 'side': 'sell', 'price': exec_price, 'qty': position, 'reason': 'signal_exit'})
            cash += proceeds
            position = 0.0

        net_worth = cash + position * price
        equity_curve.append(net_worth)

    equity = pd.Series(equity_curve, index=df.index)
    trades_df = pd.DataFrame(trades)
    return {'equity': equity, 'trades': trades_df}


def _scaler_n_features(scaler):
    if scaler is None:
        return 0
    if hasattr(scaler, 'n_features_in_'):
        return int(getattr(scaler, 'n_features_in_'))
    if hasattr(scaler, 'scale_'):
        try:
            return int(getattr(scaler, 'scale_').shape[0])
        except Exception:
            return 0
    return 0


def apply_saved_scalers_or_fail(feats: pd.DataFrame):
    pv_path = MODEL_DIR / cfg.RL_PV_SCALER_NAME
    ind_path = MODEL_DIR / cfg.RL_INDICATOR_SCALER_NAME
    manifest_path = MODEL_DIR / 'scalers_manifest.json'

    if not (pv_path.exists() and ind_path.exists() and manifest_path.exists()):
        raise RuntimeError('Multi-asset scalers or manifest missing; run agents/fit_multiasset_scalers.py first')

    import json
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    lp = joblib.load(pv_path)
    li = joblib.load(ind_path)

    pv_n = _scaler_n_features(lp)
    ind_n = _scaler_n_features(li)
    if pv_n != manifest.get('pv_n_features') or ind_n != manifest.get('ind_n_features'):
        raise RuntimeError(f"Scaler/manifest mismatch: pv {pv_n}!={manifest.get('pv_n_features')}, ind {ind_n}!={manifest.get('ind_n_features')}")

    # Exact ordered_cols validation: ensure the manifest has ordered_cols and that the
    # base features for a single asset (manifest['base_features']) match the prefix-stripped
    # ordering expected by our feature generator. This prevents silent mismatches when
    # scalers were built with a different feature order.
    ordered_cols = manifest.get('ordered_cols')
    base_feats = manifest.get('base_features') or getattr(cfg, 'BASE_FEATURES_PER_ASSET_INPUT', None)
    if ordered_cols is None or base_feats is None:
        raise RuntimeError('Manifest missing ordered_cols or base_features; cannot validate exact column ordering')

    # Derive the manifest's base ordering by stripping the leading asset_ prefix from the first asset block
    # Find the first asset name listed in the manifest
    assets = manifest.get('assets', [])
    if not assets:
        raise RuntimeError('Manifest assets list empty; cannot validate ordering')
    first_asset = assets[0]
    # ordered_cols should be like ['asset_col1', 'asset_col2', ...]; extract the block for first_asset
    first_block = [c for c in ordered_cols if c.startswith(f"{first_asset}_")]
    if len(first_block) < 1:
        raise RuntimeError('Manifest ordered_cols does not contain columns for first asset; cannot validate')
    manifest_base = [c[len(first_asset) + 1:] for c in first_block]

    # Compare manifest_base to our base_feats; if they differ exactly, abort to enforce reproducibility
    if list(manifest_base) != list(base_feats):
        raise RuntimeError(f"Manifest base feature ordering mismatch. Manifest base: {manifest_base[:10]}... vs expected base: {base_feats[:10]}...")

    # pass the discovered base_features into the scaler application so the placeholder builder uses the exact order
    scaled_df = apply_scalers_with_exact_multi_asset_placeholders(feats, lp, li, expected_base=manifest_base)
    return scaled_df


def refit_and_save_scalers_univariate(feats_df: pd.DataFrame):
    """Fit MinMax scalers on ETH single-asset features and save to MODEL_DIR (back up existing)."""
    pv_cols = [c for c in feats_df.columns if any(tok in c for tok in ('open', 'high', 'low', 'close', 'volume', 'body'))]
    ind_cols = [c for c in feats_df.columns if c not in pv_cols]
    from sklearn.preprocessing import MinMaxScaler
    pv_scaler = MinMaxScaler()
    ind_scaler = MinMaxScaler()

    Xpv = feats_df[pv_cols].ffill().bfill().dropna(axis=0, how='any')
    Xind = feats_df[ind_cols].ffill().bfill().dropna(axis=0, how='any')

    if len(Xpv) > 0:
        pv_scaler.fit(Xpv.values)
    if len(Xind) > 0:
        ind_scaler.fit(Xind.values)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pv_path = MODEL_DIR / cfg.RL_PV_SCALER_NAME
    ind_path = MODEL_DIR / cfg.RL_INDICATOR_SCALER_NAME

    def backup_file(p: Path):
        if p.exists():
            bak = p.with_suffix(p.suffix + f'.bak_{dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")}')
            p.rename(bak)
            print(f"Backed up {p} -> {bak}")

    backup_file(pv_path)
    backup_file(ind_path)
    joblib.dump(pv_scaler, pv_path)
    joblib.dump(ind_scaler, ind_path)
    print(f"Saved new univariate scalers to {pv_path} and {ind_path}")
    return pv_scaler, ind_scaler


def apply_scalers_with_exact_multi_asset_placeholders(feats_df: pd.DataFrame, pv_scaler, ind_scaler,
                                                    expected_base=None, n_assets_hint=None):
    """Synthesize multi-asset placeholder matrix based on scaler expected input size and apply scalers.
    Returns feats_df augmented with <feature>_scaled for the first asset (ETH).
    """
    expected_base = expected_base if expected_base is not None else getattr(cfg, 'BASE_FEATURES_PER_ASSET_INPUT', list(feats_df.columns))
    L = len(expected_base)
    if L == 0:
        raise RuntimeError('No expected_base features found')

    # Determine number of assets to synthesize. Prefer explicit hint, else infer from scaler shapes
    import math
    pv_n = _scaler_n_features(pv_scaler)
    ind_n = _scaler_n_features(ind_scaler)

    pv_expected = getattr(cfg, 'API_PRICE_VOL_COLS', [])
    ind_expected = [c for c in expected_base if c not in pv_expected]

    n_assets_candidates = []
    if n_assets_hint:
        try:
            n_assets_candidates.append(int(n_assets_hint))
        except Exception:
            pass
    if pv_n and pv_expected:
        n_assets_candidates.append(math.ceil(pv_n / max(1, len([c for c in pv_expected if c in expected_base]))))
    if ind_n and ind_expected:
        n_assets_candidates.append(math.ceil(ind_n / max(1, len(ind_expected))))

    if n_assets_candidates:
        n_assets = max(1, max(n_assets_candidates))
    else:
        total_in = max(pv_n or 0, ind_n or 0)
        n_assets = max(1, math.ceil(total_in / L)) if total_in > 0 else 1

    print(f"Detected expected features: pv_n={pv_n}, ind_n={ind_n}; synthesizing {n_assets} assets each with {L} features.")

    base_mat = feats_df[expected_base].ffill().bfill().values
    big_mat = np.hstack([base_mat for _ in range(n_assets)])  # shape (T, n_assets*L)

    scaled_first_asset = {}
    try:
        # Price/volume slice
        if pv_scaler is not None and len(pv_expected) > 0:
            pv_idx = [expected_base.index(c) for c in pv_expected if c in expected_base]
            pv_big_cols = []
            for a in range(n_assets):
                pv_big_cols.extend([i + a * L for i in pv_idx])
            pv_slice = big_mat[:, pv_big_cols]
            # Ensure pv_slice has the number of features the scaler expects by tiling/slicing
            expected_pv_features = _scaler_n_features(pv_scaler)
            if expected_pv_features is not None:
                if pv_slice.shape[1] < expected_pv_features:
                    # tile columns to reach expected size
                    reps = math.ceil(expected_pv_features / pv_slice.shape[1])
                    pv_slice = np.hstack([pv_slice for _ in range(reps)])
                if pv_slice.shape[1] > expected_pv_features:
                    pv_slice = pv_slice[:, :expected_pv_features]
            pv_scaled_big = pv_scaler.transform(pv_slice)
            first_pv_scaled = pv_scaled_big[:, :len(pv_idx)]
            for i, col in enumerate([expected_base[i] for i in pv_idx]):
                scaled_first_asset[f"{col}_scaled"] = first_pv_scaled[:, i]

        # Indicator slice
        if ind_scaler is not None and len(ind_expected) > 0:
            ind_idx = [expected_base.index(c) for c in ind_expected if c in expected_base]
            ind_big_cols = []
            for a in range(n_assets):
                ind_big_cols.extend([i + a * L for i in ind_idx])
            ind_slice = big_mat[:, ind_big_cols]
            expected_ind_features = _scaler_n_features(ind_scaler)
            if expected_ind_features is not None:
                if ind_slice.shape[1] < expected_ind_features:
                    reps = math.ceil(expected_ind_features / ind_slice.shape[1])
                    ind_slice = np.hstack([ind_slice for _ in range(reps)])
                if ind_slice.shape[1] > expected_ind_features:
                    ind_slice = ind_slice[:, :expected_ind_features]
            ind_scaled_big = ind_scaler.transform(ind_slice)
            first_ind_scaled = ind_scaled_big[:, :len(ind_idx)]
            for i, col in enumerate([expected_base[i] for i in ind_idx]):
                scaled_first_asset[f"{col}_scaled"] = first_ind_scaled[:, i]
    except Exception as e:
        print(f"Error during multi-asset placeholder scaling: {e}")

    scaled_df = feats_df.copy()
    for k, v in scaled_first_asset.items():
        scaled_df[k] = v
    return scaled_df


if __name__ == '__main__':
    try:
        print('\nSTEP 0: Fetch ETH-USD features (2y 1h)')
        ohlcv = fetch_single_asset_ohlcv_yf('ETH-USD', period='2y', interval='1h')
        feats = calculate_all_features_for_single_asset(ohlcv)
        if feats is None or feats.empty:
            raise RuntimeError('Failed to compute ETH features')

        # Try to use on-disk validated multi-asset scalers (strict-by-default)
        scaled_df = None
        try:
            scaled_df = apply_saved_scalers_or_fail(feats)
            print('Applied on-disk multi-asset scalers')
        except Exception as e:
            if os.getenv('BACKTEST_FALLBACK_TO_REFIT', '0') == '1':
                print(f'On-disk scalers validation failed: {e} -- falling back to refit (env var enabled)')
                pv_s, ind_s = refit_and_save_scalers_univariate(feats)
                scaled_df = apply_scalers_with_exact_multi_asset_placeholders(feats, pv_s, ind_s)
            else:
                raise

        # Default backtest (unscaled features)
        out_default = run_backtest_from_features(feats, start_capital=100000.0)
        prefix = LOGS_DIR / f"backtest_ethusd_2y_1h_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        out_default['trades'].to_csv(str(prefix) + '_trades.csv', index=False)
        out_default['equity'].to_csv(str(prefix) + '_equity.csv', header=['equity'])

        # Tuned run (scaled inputs)
        tuned = run_backtest_from_features(scaled_df, start_capital=100000.0)
        tuned_prefix = LOGS_DIR / f"backtest_ethusd_2y_1h_tuned_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        tuned['trades'].to_csv(str(tuned_prefix) + '_trades.csv', index=False)
        tuned['equity'].to_csv(str(tuned_prefix) + '_equity.csv', header=['equity'])
        print(f"Tuned run saved to logs\\{tuned_prefix.stem}_* . End capital: {tuned['equity'].iloc[-1]:.2f}")

    except Exception as e:
        print('Backtest aborted:', e)
        sys.exit(1)
