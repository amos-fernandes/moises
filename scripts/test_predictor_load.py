"""Simple test: instantiate RNNModelPredictor, call load_model(), and print health_check()"""
import asyncio
from pathlib import Path
import json

import sys
from pathlib import Path
# Ensure repo root is on sys.path
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.model.rnn_predictor import RNNModelPredictor


async def main():
    predictor = RNNModelPredictor(model_dir='src/model')
    await predictor.load_model()
    info = predictor.health_check()
    print(json.dumps(info, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
