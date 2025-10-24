"""Inspect saved scaler artifacts and print diagnostic info.
Run from the repo root with the project's venv to see why scalers fail to load.
"""
import joblib
import json
from pathlib import Path

MODEL_DIR = Path('src') / 'model'
PATTERN = '*scaler*.joblib'

def info(path):
    print('\n---', path.name, '---')
    if not path.exists():
        print('MISSING')
        return
    try:
        s = joblib.load(path)
    except Exception as e:
        print('LOAD ERROR:', type(e).__name__, e)
        return
    def _get(obj, name):
        try:
            return getattr(obj, name)
        except Exception:
            return None
    print('type:', type(s))
    print('n_features_in_:', _get(s, 'n_features_in_'))
    print('feature_names_in_:', _get(s, 'feature_names_in_'))
    scale = _get(s, 'scale_')
    if scale is not None:
        try:
            print('scale_.shape:', getattr(scale, 'shape', None))
        except Exception:
            pass
    mean = _get(s, 'mean_')
    if mean is not None:
        print('mean_.shape:', getattr(mean, 'shape', None))
    # show first 10 feature names if present
    fn = _get(s, 'feature_names_in_')
    if fn is not None:
        try:
            print('first feature names:', list(fn)[:10])
        except Exception:
            pass

if __name__ == '__main__':
    print('Inspecting scalers in', MODEL_DIR)
    for p in sorted(MODEL_DIR.glob(PATTERN)):
        info(p)