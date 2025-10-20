"""Utility helpers to save/load/validate scaler artifacts and manifests.
Centralizes joblib dumping, backups and manifest schema used across training and API.
"""
from pathlib import Path
import joblib
import time
import json
from typing import Tuple, Optional


def _backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + f'.bak_{int(time.time())}')
        path.rename(bak)


def save_scalers(pv_scaler, ind_scaler, model_dir: Path, pv_name: str, ind_name: str,
                 manifest: Optional[dict] = None) -> dict:
    """Save price/volume and indicator scalers to disk under model_dir.

    Returns manifest dict written (either provided or generated).
    """
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    pv_path = model_dir / pv_name
    ind_path = model_dir / ind_name

    _backup(pv_path)
    _backup(ind_path)

    joblib.dump(pv_scaler, pv_path)
    joblib.dump(ind_scaler, ind_path)

    # try to infer n_features
    def _n_features(scaler):
        n = getattr(scaler, 'n_features_in_', None)
        if n is None:
            try:
                n = getattr(scaler, 'scale_', None).shape[0]
            except Exception:
                n = None
        return int(n) if n is not None else None

    n_pv = _n_features(pv_scaler)
    n_ind = _n_features(ind_scaler)

    if manifest is None:
        manifest = {}
    manifest.setdefault('created_at', None)
    manifest['pv_n_features'] = n_pv
    manifest['ind_n_features'] = n_ind

    # ensure created_at is set
    if not manifest.get('created_at'):
        try:
            import pandas as _pd
            manifest['created_at'] = _pd.Timestamp.now(tz=None).isoformat()
        except Exception:
            manifest['created_at'] = str(int(time.time()))

    manifest_path = model_dir / 'scalers_manifest.json'
    _backup(manifest_path)
    with manifest_path.open('w', encoding='utf-8') as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)

    return manifest


def load_scalers(model_dir: Path, pv_name: str, ind_name: str) -> Tuple[object, object, dict]:
    """Load scalers and manifest from model_dir. Returns (pv_scaler, ind_scaler, manifest).
    Raises FileNotFoundError if missing.
    """
    model_dir = Path(model_dir)
    pv_path = model_dir / pv_name
    ind_path = model_dir / ind_name
    manifest_path = model_dir / 'scalers_manifest.json'

    if not pv_path.exists() or not ind_path.exists():
        raise FileNotFoundError(f'Scaler files missing in {model_dir}: {pv_path}, {ind_path}')

    pv = joblib.load(pv_path)
    ind = joblib.load(ind_path)

    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf8'))
        except Exception:
            manifest = {}

    return pv, ind, manifest
