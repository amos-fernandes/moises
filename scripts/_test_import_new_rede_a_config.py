import importlib
cfg = importlib.import_module('new-rede-a.config')
print('WINDOW_SIZE=', getattr(cfg, 'WINDOW_SIZE', None))
print('NUM_ASSETS=', getattr(cfg, 'NUM_ASSETS', None))
print('ALL_ASSET_SYMBOLS sample=', (getattr(cfg, 'ALL_ASSET_SYMBOLS', [])[:5]))
print('FINNHUB_API_KEY=', getattr(cfg, 'FINNHUB_API_KEY', None))
