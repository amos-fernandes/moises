import pytest
import importlib
import numpy as np
import pandas as pd

rnn = importlib.import_module('src.model.rnn_predictor')
from src.config.config import RL_PV_SCALER_NAME, RL_INDICATOR_SCALER_NAME, WINDOW_SIZE, EXPECTED_SCALED_FEATURES_FOR_MODEL


def make_fake_ohlcv(rows):
    idx = pd.date_range(end=pd.Timestamp.now(tz='UTC'), periods=rows, freq='h')
    data = {
        'open': np.random.rand(rows) * 100 + 3000,
        'high': np.random.rand(rows) * 120 + 3000,
        'low': np.random.rand(rows) * 80 + 2990,
        'close': np.random.rand(rows) * 100 + 3000,
        'volume': np.random.rand(rows) * 1000 + 10
    }
    df = pd.DataFrame(data, index=idx)
    df['high'] = df[['high','open','close']].max(axis=1)
    df['low'] = df[['low','open','close']].min(axis=1)
    return df


def test_align_window_to_scaler_and_preprocess():
    predictor = rnn.RNNModelPredictor(model_dir='src/model', pv_scaler_filename=RL_PV_SCALER_NAME, ind_scaler_filename=RL_INDICATOR_SCALER_NAME, logger_instance=None)
    predictor._load_model_and_scalers()

    # Ensure scalers loaded
    assert predictor.price_volume_scaler is not None, "PV scaler not loaded"
    assert predictor.indicator_scaler is not None, "IND scaler not loaded"

    # Build a window dataframe
    # Generate a sufficiently large window so indicator calculations with rolling windows
    # won't drop us below the required WINDOW_SIZE after dropna.
    rows = WINDOW_SIZE + 400
    ohlcv = make_fake_ohlcv(rows)
    features = rnn.calculate_features_for_prediction(ohlcv, logger_instance=None)
    # If the features contain too many NaNs due to randomness, retry with a larger window
    if features is None or len(features) < WINDOW_SIZE:
        rows = WINDOW_SIZE + 800
        ohlcv = make_fake_ohlcv(rows)
        features = rnn.calculate_features_for_prediction(ohlcv, logger_instance=None)
    assert features is not None and len(features) >= WINDOW_SIZE

    # Align PV
    pv_input = rnn._align_window_to_scaler(features.tail(WINDOW_SIZE), rnn.API_PRICE_VOL_COLS_TO_SCALE, predictor.price_volume_scaler, scaler_type='pv')
    pv_expected = getattr(predictor.price_volume_scaler, 'n_features_in_', None)
    assert pv_input.shape[1] == pv_expected

    # Align IND
    ind_input = rnn._align_window_to_scaler(features.tail(WINDOW_SIZE), rnn.API_INDICATOR_COLS_TO_SCALE, predictor.indicator_scaler, scaler_type='ind')
    ind_expected = getattr(predictor.indicator_scaler, 'n_features_in_', None)
    assert ind_input.shape[1] == ind_expected

    # Preprocess output shape
    processed = rnn.preprocess_for_model_prediction(features, predictor.price_volume_scaler, predictor.indicator_scaler, EXPECTED_SCALED_FEATURES_FOR_MODEL, WINDOW_SIZE, logger_instance=None)
    assert processed.size > 0
    assert processed.shape == (1, WINDOW_SIZE, len(EXPECTED_SCALED_FEATURES_FOR_MODEL))

    # Health check
    health = predictor.health_check()
    assert 'pv_n_features_in' in health
    assert 'ind_n_features_in' in health
    assert health['expected_scaled_features_for_model_len'] == len(EXPECTED_SCALED_FEATURES_FOR_MODEL)
