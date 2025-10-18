import importlib.util
import sys
from pathlib import Path
p = Path('..') / 'new-rede-a' / 'config.py'
mod_name = 'new_rede_a_config'
spec = importlib.util.spec_from_file_location(mod_name, str(p))
mod = importlib.util.module_from_spec(spec)
loader = spec.loader
loader.exec_module(mod)
print('WINDOW_SIZE=', getattr(mod, 'WINDOW_SIZE', None))
print('NUM_ASSETS=', getattr(mod, 'NUM_ASSETS', None))
print('ALL_ASSET_SYMBOLS sample=', (getattr(mod, 'ALL_ASSET_SYMBOLS', [])[:5]))
print('FINNHUB_API_KEY=', getattr(mod, 'FINNHUB_API_KEY', None))
