"""
TD Ameritrade adapter (skeleton)

Provides a minimal interface for fetching OHLCV via TDA and placing orders (dry-run).
Requires a TDA developer account for production; here we provide a simple dry-run and
placeholder HTTP calls.

Environment variables used:
 - TDA_API_KEY
 - TDA_REFRESH_TOKEN
 - TDA_ACCOUNT_ID

"""
from typing import Optional, Dict, Any, List
import os
import time
import requests

TDA_API_KEY = os.environ.get('TDA_API_KEY')
TDA_REFRESH_TOKEN = os.environ.get('TDA_REFRESH_TOKEN')
TDA_ACCOUNT_ID = os.environ.get('TDA_ACCOUNT_ID')
TDA_SANDBOX = os.environ.get('TDA_SANDBOX', 'false').lower() == 'true'

BASE = 'https://api.tdameritrade.com/v1'


class TDClient:
    def __init__(self, dry_run: bool = True, logger=None):
        self.dry_run = dry_run
        self.logger = logger
        self.session = requests.Session()

    def fetch_ohlcv(self, symbol: str, timeframe: str = '60min', max_points: int = 500) -> List[Dict[str, Any]]:
        if self.dry_run:
            now = int(time.time())
            return [{'timestamp': now - i * 3600, 'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.5, 'volume': 1000} for i in range(max_points)][::-1]

        # Placeholder for real TDA price history endpoints
        url = f"{BASE}/marketdata/{symbol}/pricehistory"
        params = {'apikey': TDA_API_KEY, 'periodType': 'day', 'frequencyType': 'minute', 'frequency': 60}
        r = self.session.get(url, params=params)
        r.raise_for_status()
        return r.json()

    def place_order(self, symbol: str, instruction: str, quantity: int, price: Optional[float] = None) -> Dict[str, Any]:
        if self.dry_run:
            order = {'symbol': symbol, 'instruction': instruction, 'quantity': quantity, 'price': price, 'status': 'dry-run'}
            if self.logger: self.logger.info(f'TDClient.place_order dry-run: {order}')
            return order
        # Real order placement requires OAuth and account ID
        url = f"{BASE}/accounts/{TDA_ACCOUNT_ID}/orders"
        payload = {}
        r = self.session.post(url, json=payload, params={'apikey': TDA_API_KEY})
        r.raise_for_status()
        return r.json()


__all__ = ['TDClient']
