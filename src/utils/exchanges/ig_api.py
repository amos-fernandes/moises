"""
IG Markets adapter (skeleton)

Provides a minimal interface for fetching OHLCV and placing orders against IG's REST API.
This is a lightweight adapter with a dry-run mode. For production use, you should
use an official SDK or a well-tested client and implement robust auth token refresh,
error handling, rate limiting and signing.

Environment variables used:
 - IG_API_KEY
 - IG_USERNAME
 - IG_PASSWORD
 - IG_SANDBOX (optional, 'true' enables demo)

"""
from typing import Optional, Dict, Any, List
import os
import time
import requests

IG_API_KEY = os.environ.get('IG_API_KEY')
IG_USERNAME = os.environ.get('IG_USERNAME')
IG_PASSWORD = os.environ.get('IG_PASSWORD')
IG_SANDBOX = os.environ.get('IG_SANDBOX', 'false').lower() == 'true'

BASE_DEMO = 'https://demo-api.ig.com/gateway/deal'
BASE_LIVE = 'https://api.ig.com/gateway/deal'


class IGClient:
    def __init__(self, dry_run: bool = True, logger=None):
        self.dry_run = dry_run
        self.logger = logger
        self.base = BASE_DEMO if IG_SANDBOX else BASE_LIVE
        self.session = requests.Session()
        if IG_API_KEY:
            self.session.headers.update({'X-IG-API-KEY': IG_API_KEY})

    def authenticate(self) -> bool:
        """Perform login to IG REST API (simple username/password flow).
        For production, implement token refresh and handle two-factor flows as needed."""
        if self.dry_run:
            if self.logger: self.logger.info('IGClient: dry-run authenticate OK')
            return True
        if not (IG_USERNAME and IG_PASSWORD and IG_API_KEY):
            if self.logger: self.logger.error('IGClient: missing credentials')
            return False
        try:
            url = f"{self.base}/session"
            payload = {'username': IG_USERNAME, 'password': IG_PASSWORD}
            r = self.session.post(url, json=payload)
            r.raise_for_status()
            # Response contains tokens in headers; in full client you must capture them
            if self.logger: self.logger.info('IGClient: authenticated')
            return True
        except Exception as e:
            if self.logger: self.logger.error(f'IGClient authenticate failed: {e}')
            return False

    def fetch_ohlcv(self, epic: str, timeframe: str = 'H1', max_points: int = 500) -> List[Dict[str, Any]]:
        """Fetch candles for a given epic. Returns list of dicts with timestamp/open/high/low/close/volume.
        This is a simplified implementation and may require mapping timeframe names to IG's API.
        """
        if self.dry_run:
            # Return dummy data
            now = int(time.time())
            return [{'timestamp': now - i * 3600, 'open': 1.0, 'high': 1.0, 'low': 1.0, 'close': 1.0, 'volume': 0} for i in range(max_points)][::-1]

        # Real implementation would call the prices/candle endpoint for IG
        url = f"{self.base}/prices/{epic}/candles/{timeframe}"  # illustrative
        r = self.session.get(url, params={'max': max_points})
        r.raise_for_status()
        data = r.json()
        # Map data to expected structure
        return data

    def place_order(self, epic: str, direction: str, size: float, order_type: str = 'MARKET', price: Optional[float] = None) -> Dict[str, Any]:
        """Place an order. direction: 'BUY' or 'SELL'. In dry_run mode returns a mock order dict."""
        if self.dry_run:
            mock = {'epic': epic, 'direction': direction, 'size': size, 'order_type': order_type, 'price': price, 'status': 'dry-run'}
            if self.logger: self.logger.info(f'IGClient.place_order dry-run: {mock}')
            return mock

        payload = {
            'epic': epic,
            'dealType': 'MARKET' if order_type == 'MARKET' else 'LIMIT',
            'direction': direction,
            'size': size,
        }
        if price is not None:
            payload['price'] = price

        url = f"{self.base}/positions/otc"
        r = self.session.post(url, json=payload)
        r.raise_for_status()
        return r.json()


__all__ = ['IGClient']
