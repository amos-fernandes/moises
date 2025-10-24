"""
Smoke demo: fetch OHLCV and perform dry-run order across available exchange adapters.
Usage: python scripts/smoke_trade_demo.py
"""
import sys
import asyncio
import logging
from pathlib import Path
# Ensure repo root is on sys.path for local imports
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.utils.ccxt_utils import get_ccxt_exchange, fetch_crypto_data
from src.utils.exchanges.ig_api import IGClient
from src.utils.exchanges.tdameritrade_api import TDClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('smoke_demo')

async def run_ccxt_demo():
    logger.info('--- CCXT demo: Binance (dry-run) ---')
    exch = await get_ccxt_exchange(logger_instance=logger)
    if exch is None:
        logger.error('Could not init CCXT exchange (skipping)')
        return
    pairs = ['BTC/USDT']
    data, ok, msg = await fetch_crypto_data(exch, pairs, logger_instance=logger)
    logger.info('CCXT fetched ok=%s msg=%s keys=%s', ok, msg, list(data.keys()))
    # Dry-run buy by not using real order (ccxt_utils honors CCXT_DRY_RUN env var)
    # Ensure exchange resources are closed to avoid unclosed session warnings
    try:
        pass
    finally:
        try:
            if hasattr(exch, 'close'):
                await exch.close()
                logger.debug('CCXT exchange closed')
        except Exception:
            logger.exception('Error while closing CCXT exchange')


def run_ig_demo():
    logger.info('--- IG demo (dry-run) ---')
    ig = IGClient(dry_run=True, logger=logger)
    ok = ig.authenticate()
    logger.info('IG auth ok=%s', ok)
    ohlcv = ig.fetch_ohlcv('CS.D.EURUSD.MINI.IP', timeframe='H1', max_points=10)
    logger.info('IG ohlcv sample len=%d', len(ohlcv))
    res = ig.place_order('CS.D.EURUSD.MINI.IP', 'BUY', 1.0)
    logger.info('IG place_order res=%s', res)


def run_tda_demo():
    logger.info('--- TDA demo (dry-run) ---')
    tda = TDClient(dry_run=True, logger=logger)
    ohlcv = tda.fetch_ohlcv('AAPL', timeframe='60min', max_points=10)
    logger.info('TDA ohlcv sample len=%d', len(ohlcv))
    res = tda.place_order('AAPL', 'BUY', 1)
    logger.info('TDA place_order res=%s', res)


if __name__ == '__main__':
    # Use asyncio.run() which creates a fresh event loop and avoids "no current event loop" warnings
    try:
        asyncio.run(run_ccxt_demo())
    finally:
        # run synchronous demos
        run_ig_demo()
        run_tda_demo()
    logger.info('Smoke demo completed')
