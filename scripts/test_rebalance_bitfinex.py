#!/usr/bin/env python
import asyncio
import logging
import os
from src.utils.ccxt_utils import get_ccxt_exchange, execute_portfolio_rebalance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_rebalance")

async def main():
    logger.info("Starting Bitfinex dry-run test")
    exchange = await get_ccxt_exchange(logger)
    if exchange is None:
        logger.error("Failed to initialize exchange. Check API key/secret and CCXT_EXCHANGE_ID.")
        return

    # Example target weights: 50% ETH, 50% BTC
    target_weights = {'eth': 0.5, 'btc': 0.5}
    results = await execute_portfolio_rebalance(exchange, target_weights, logger)
    logger.info("Dry-run results: %s", results)

    try:
        await exchange.close()
    except Exception:
        pass

if __name__ == '__main__':
    asyncio.run(main())
