"""Run an end-to-end prediction using RNNModelPredictor with synthetic OHLCV data.
This verifies scalers + TorchScript fallback inference pipeline.
"""
import sys
from pathlib import Path
import asyncio
import numpy as np
import pandas as pd

# Ensure repo root is importable
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.model.rnn_predictor import RNNModelPredictor
from src.config.config import WINDOW_SIZE


def make_synthetic_ohlcv(rows: int):
    end = pd.Timestamp.now(tz='UTC')
    start = end - pd.Timedelta(hours=rows - 1)
    idx = pd.date_range(start=start, end=end, freq='h')
    np.random.seed(42)
    close = np.cumsum(np.random.randn(len(idx)) * 2 + 0.1) + 30000
    open_ = close + np.random.randn(len(idx)) * 1
    high = np.maximum(open_, close) + np.abs(np.random.rand(len(idx)) * 5)
    low = np.minimum(open_, close) - np.abs(np.random.rand(len(idx)) * 5)
    volume = np.random.rand(len(idx)) * 100 + 10
    df = pd.DataFrame({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume}, index=idx)
    return df


async def main():
    predictor = RNNModelPredictor(model_dir='src/model')
    await predictor.load_model()
    print('Health:', predictor.health_check())

    rows = WINDOW_SIZE + 100
    ohlcv = make_synthetic_ohlcv(rows)
    sig, prob = await predictor.predict_for_asset_ohlcv(ohlcv, api_operation_threshold=0.65)
    print('Prediction -> signal:', sig, 'prob:', prob)


if __name__ == '__main__':
    asyncio.run(main())
