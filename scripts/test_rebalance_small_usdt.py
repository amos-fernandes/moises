import asyncio, logging
from src.utils.ccxt_utils import execute_portfolio_rebalance

# Mock small USDT balance converted from R$100 -> USD $18
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_rebalance_small_usdt')

async def main():
    class FakeExchangeSmall:
        id = 'mock'
        async def fetch_ticker(self, market):
            if 'ETH' in market:
                return {'ask': 2000.0, 'last': 2000.0, 'bid': 1999.0}
            if 'BTC' in market:
                return {'ask': 40000.0, 'last': 40000.0, 'bid': 39950.0}
            return {'ask': 1.0, 'last':1.0, 'bid':1.0}
        async def fetch_balance(self):
            # small USDT balance only
            return {'USDT': {'free': 18.0}, 'ETH': {'free': 0.0}, 'BTC': {'free': 0.0}}
        markets = {
            'ETH/USDT': {'limits': {'amount': {'min': 0.0001}, 'cost': {'min': 10}}},
            'BTC/USDT': {'limits': {'amount': {'min': 0.000001}, 'cost': {'min': 10}}},
        }

    fake = FakeExchangeSmall()
    target = {'eth': 0.5, 'btc': 0.5}
    result = await execute_portfolio_rebalance(fake, target, logger)
    print('\nSmall-balance mocked dry-run result:\n', result)

if __name__ == '__main__':
    asyncio.run(main())
