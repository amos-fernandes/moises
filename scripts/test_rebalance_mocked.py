import asyncio, logging
from src.utils.ccxt_utils import execute_portfolio_rebalance

# This script calls execute_portfolio_rebalance but first creates a dummy exchange-like
# object by monkeypatching get_current_portfolio behavior inside the module. Simulates
# having $10,000 USDT and no crypto holdings so we can exercise buy logic.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_rebalance_mocked')

async def main():
    # Build a fake exchange object with necessary methods used by execute_portfolio_rebalance
    class FakeExchange:
        id = 'mock'
        async def fetch_ticker(self, market):
            # Return a price map: e.g., ETH-USD -> ask 2000, BTC-USD -> ask 40000
            if 'ETH' in market:
                return {'ask': 2000.0, 'last': 2000.0, 'bid': 1999.0}
            if 'BTC' in market:
                return {'ask': 40000.0, 'last': 40000.0, 'bid': 39950.0}
            return {'ask': 1.0, 'last':1.0, 'bid':1.0}
        async def fetch_balance(self):
            # Return empty crypto balances, USDT balance 10000
            return {'USDT': {'free': 10000.0}, 'ETH': {'free': 0.0}, 'BTC': {'free': 0.0}}
        # minimal markets metadata used by code
        markets = {
            'ETH/USDT': {'limits': {'amount': {'min': 0.0001}, 'cost': {'min': 10}}},
            'BTC/USDT': {'limits': {'amount': {'min': 0.000001}, 'cost': {'min': 10}}},
        }

    fake = FakeExchange()
    # target weights
    target = {'eth': 0.5, 'btc': 0.5}
    result = await execute_portfolio_rebalance(fake, target, logger)
    print('\nMocked dry-run result:\n', result)

if __name__ == '__main__':
    asyncio.run(main())
