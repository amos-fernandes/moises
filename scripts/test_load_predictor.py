import asyncio
from src.model.rnn_predictor import RNNModelPredictor

async def main():
    p = RNNModelPredictor(logger_instance=None)
    await p.load_model()
    print('Health:', p.health_check())

if __name__ == '__main__':
    asyncio.run(main())
