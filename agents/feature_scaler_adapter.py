"""Adapter to fit/save scalers and produce <feature>_scaled columns for RL training.

This module is deliberately defensive:
- It reads base feature lists and scaler names from agents.config when available,
  falling back to scripts.config if necessary.
- It fits MinMaxScaler by default (keeps compatibility with existing scripts),
  creates `<col>_scaled` columns, and saves scalers to the configured model dir.
"""
from pathlib import Path
import os
import warnings
import numpy as np
import pandas as pd
try:
    from sklearn.preprocessing import MinMaxScaler
except Exception:
    MinMaxScaler = None
import joblib


def _load_configs():
    # prefer agents.config, else scripts.config
    try:
        import agents.config as aconf
    except Exception:
        aconf = None
    try:
        import scripts.config as sconf
    except Exception:
        sconf = None
    return aconf, sconf


def fit_and_create_scaled(df: pd.DataFrame, save_scalers: bool = True, scaler_kind: str = 'minmax'):
    """Fit scalers on the given DataFrame and create `<col>_scaled` columns.

    Args:
        df: DataFrame with canonical base features (e.g. output of calculate_all_features_for_single_asset)
        save_scalers: whether to persist fitted scalers to disk using joblib
        scaler_kind: currently only 'minmax' supported (keeps compatibility)

    Returns:
        df_out: original df with new `<col>_scaled` columns appended (in-place also modified)
        info: dict with keys 'pv_scaler_path', 'ind_scaler_path', 'pv_cols', 'ind_cols'
    """
    aconf, sconf = _load_configs()

    # Determine base features list
    if aconf is not None and hasattr(aconf, 'BASE_FEATURES_PER_ASSET_INPUT'):
        base_feats = list(aconf.BASE_FEATURES_PER_ASSET_INPUT)
    elif sconf is not None and hasattr(sconf, 'BASE_FEATURE_COLS'):
        base_feats = list(sconf.BASE_FEATURE_COLS)
    else:
        raise RuntimeError('Could not find BASE features list in agents.config or scripts.config')

    # Determine price/volume vs indicator splits
    # Prefer explicit lists from config; else infer by scanning actual df column names
    if aconf is not None and hasattr(aconf, 'API_PRICE_VOL_COLS'):
        pv_base = [c for c in aconf.API_PRICE_VOL_COLS if c in base_feats]
    elif sconf is not None and hasattr(sconf, 'COLS_TO_NORM_BY_ATR'):
        pv_base = [c for c in sconf.COLS_TO_NORM_BY_ATR if c in base_feats]
    else:
        # Infer by common tokens in base features
        pv_tokens = ('open', 'high', 'low', 'close', 'volume', 'body')
        pv_base = [f for f in base_feats if any(tok in f.lower() for tok in pv_tokens)]
        if not pv_base:
            pv_base = base_feats[:6]

    ind_base = [c for c in base_feats if c not in pv_base]

    # Map base feature names to actual columns in df (supporting prefixed multi-asset columns)
    def _map_base_to_actual_cols(columns, base_names):
        cols = list(columns)
        mapped = []
        for b in base_names:
            # Prefer exact matches
            if b in cols:
                mapped.append(b)
                continue
            # Match columns that contain the base name as a token separated by underscores
            token_matches = [c for c in cols if (f'_{b}' in c) or (c.startswith(b + '_')) or (f'_{b}_' in c) or (c.endswith('_' + b)) or (b in c)]
            if token_matches:
                # stable ordering
                token_matches = sorted(set(token_matches))
                mapped.extend(token_matches)
        # Deduplicate while preserving order
        seen = set()
        out = []
        for c in mapped:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    # More robust grouping: scan columns for PV-like or indicator-like tokens
    pv_cols = [c for c in df.columns if any(tok in c.lower() for tok in ('open', 'high', 'low', 'close', 'volume', 'body'))]
    ind_cols = [c for c in df.columns if c not in pv_cols]

    # If pv_cols or ind_cols are empty, try mapping from base names to actual.
    if not pv_cols:
        pv_cols = _map_base_to_actual_cols(df.columns, pv_base)
    if not ind_cols:
        ind_cols = _map_base_to_actual_cols(df.columns, ind_base)

    # scaler creation
    if scaler_kind != 'minmax':
        warnings.warn('Only minmax scaler supported; falling back to MinMaxScaler')
    if MinMaxScaler is None:
        raise RuntimeError('sklearn MinMaxScaler not available in the environment')

    pv_scaler = MinMaxScaler()
    ind_scaler = MinMaxScaler()

    # Prepare save paths
    if aconf is not None and hasattr(aconf, 'MODEL_ROOT_DIR'):
        model_root = Path(aconf.MODEL_ROOT_DIR)
    elif sconf is not None and hasattr(sconf, 'MODEL_SAVE_DIR'):
        model_root = Path(sconf.MODEL_SAVE_DIR)
    else:
        model_root = Path('model')
    model_root.mkdir(parents=True, exist_ok=True)

    pv_scaler_name = 'rl_price_volume_atr_norm_scaler.joblib'
    ind_scaler_name = 'rl_other_indicators_scaler.joblib'
    if aconf is not None:
        pv_scaler_name = getattr(aconf, 'RL_PV_SCALER_NAME', pv_scaler_name)
        ind_scaler_name = getattr(aconf, 'RL_INDICATOR_SCALER_NAME', ind_scaler_name)
    elif sconf is not None:
        pv_scaler_name = getattr(sconf, 'PRICE_VOL_SCALER_NAME', pv_scaler_name)
        ind_scaler_name = getattr(sconf, 'INDICATOR_SCALER_NAME', ind_scaler_name)

    pv_scaler_path = model_root / pv_scaler_name
    ind_scaler_path = model_root / ind_scaler_name

    df_out = df.copy()

    # Defensive: replace infs and large values
    df_out = df_out.replace([np.inf, -np.inf], np.nan)

    info = {
        'pv_base': pv_base,
        'ind_base': ind_base,
        'pv_cols': pv_cols,
        'ind_cols': ind_cols,
        'pv_scaler_path': str(pv_scaler_path),
        'ind_scaler_path': str(ind_scaler_path),
    }

    # Fit pv scaler
    try:
        pv_present = [c for c in pv_cols if c in df_out.columns]
        if pv_present:
            Xpv = df_out.loc[:, pv_present].copy()
            # fill small gaps for fitting (avoid deprecated fillna(method=...))
            Xpv = Xpv.ffill().bfill()
            # if still NaN rows, drop them for fitting
            Xpv_fit = Xpv.dropna(axis=0, how='any')
            if Xpv_fit.shape[0] > 0:
                pv_scaler.fit(Xpv_fit.values)
                Xpv_scaled = pv_scaler.transform(Xpv.values)
                for i, col in enumerate(pv_present):
                    df_out[f"{col}_scaled"] = Xpv_scaled[:, i]
                if save_scalers:
                    joblib.dump(pv_scaler, pv_scaler_path)
            else:
                warnings.warn('No valid rows to fit PV scaler; skipping PV scaling')
        else:
            # No PV-like columns found; create placeholder scaled columns for expected names
            # This avoids noisy warnings and preserves column schema for downstream code.
            # Create NaN scaled columns for each expected pv_base per asset prefix if possible.
            # Attempt to detect asset prefixes (columns like asset_a_close)
            prefixes = set()
            for c in df_out.columns:
                parts = c.split('_')
                if len(parts) > 1:
                    prefixes.add(parts[0])
            for prefix in sorted(prefixes)[:10]:
                for b in pv_base:
                    colname = f"{prefix}_{b}"
                    if colname not in df_out.columns:
                        df_out[f"{colname}_scaled"] = np.nan
    except Exception as e:
        warnings.warn(f'PV scaler step failed: {e}')

    # Fit indicator scaler
    try:
        ind_present = [c for c in ind_cols if c in df_out.columns]
        if ind_present:
            Xind = df_out.loc[:, ind_present].copy()
            Xind = Xind.ffill().bfill()
            Xind_fit = Xind.dropna(axis=0, how='any')
            if Xind_fit.shape[0] > 0:
                ind_scaler.fit(Xind_fit.values)
                Xind_scaled = ind_scaler.transform(Xind.values)
                for i, col in enumerate(ind_present):
                    df_out[f"{col}_scaled"] = Xind_scaled[:, i]
                if save_scalers:
                    joblib.dump(ind_scaler, ind_scaler_path)
            else:
                warnings.warn('No valid rows to fit indicator scaler; skipping indicator scaling')
        else:
            # Same approach for indicators: create placeholder scaled columns for expected indicators
            prefixes = set()
            for c in df_out.columns:
                parts = c.split('_')
                if len(parts) > 1:
                    prefixes.add(parts[0])
            for prefix in sorted(prefixes)[:10]:
                for b in ind_base:
                    colname = f"{prefix}_{b}"
                    if colname not in df_out.columns:
                        df_out[f"{colname}_scaled"] = np.nan
    except Exception as e:
        warnings.warn(f'Indicator scaler step failed: {e}')

    # Ensure all expected scaled cols exist (create NaNs if missing to preserve ordering)
    try:
        expected = None
        if aconf is not None and hasattr(aconf, 'EXPECTED_SCALED_FEATURES_FOR_MODEL'):
            expected = list(aconf.EXPECTED_SCALED_FEATURES_FOR_MODEL)
        elif sconf is not None and hasattr(sconf, 'EXPECTED_SCALED_FEATURES_FOR_MODEL'):
            expected = list(sconf.EXPECTED_SCALED_FEATURES_FOR_MODEL)
        if expected is not None:
            for col in expected:
                if col not in df_out.columns:
                    df_out[col] = np.nan
    except Exception:
        pass

    return df_out, info


if __name__ == '__main__':
    print('Run this module from a test harness; it provides fit_and_create_scaled function')
