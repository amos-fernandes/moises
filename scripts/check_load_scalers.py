from pathlib import Path
import traceback
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from src.utils.scaler_utils import load_scalers
    pv, ind, manifest = load_scalers(Path('src/model'), 'price_volume_atr_norm_scaler_sup.joblib', 'other_indicators_scaler_sup.joblib')
    print('Loaded pv, ind types:', type(pv), type(ind))
    print('Manifest keys:', list(manifest.keys()))
except Exception:
    traceback.print_exc()
