import asyncio, time, os
import ccxt.async_support as ccxt

async def main():
    ex = getattr(ccxt, os.environ.get('CCXT_EXCHANGE_ID','binance'))({'apiKey': os.environ.get('CCXT_API_KEY'), 'secret': os.environ.get('CCXT_API_SECRET'), 'options': {'adjustForTimeDifference': True}})
    try:
        server = await ex.fetch_time()
        now = int(time.time()*1000)
        print('server_time_ms=', server)
        print('local_time_ms =', now)
        print('drift_ms =', server - now)
    except Exception as e:
        print('error fetching time:', e)
    finally:
        await ex.close()

if __name__ == '__main__':
    asyncio.run(main())
