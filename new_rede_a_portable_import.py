import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
NEW_REDE_A_DIR = BASE / 'new-rede-a'

# Helper to load a module from file path
def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PortableLoader:
    """Simple loader object to load modules from the new-rede-a folder by dotted path.

    Usage:
        loader = load_portable()
        dh = loader.load_module('new-rede-a.data_handler_multi_asset')
    """
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def load_module(self, dotted_path: str):
        # map dotted paths like 'new-rede-a.data_handler_multi_asset' to file path
        parts = dotted_path.split('.')
        # allow both 'new-rede-a.module' or 'data_handler_multi_asset'
        if parts[0] == 'new-rede-a' or parts[0] == 'new_rede_a' or parts[0] == 'new-rede-a':
            rel_parts = parts[1:]
        else:
            rel_parts = parts
        file_name = rel_parts[-1] + '.py'
        file_path = self.base_dir.joinpath(*rel_parts[:-1], file_name)
        if not file_path.exists():
            # try direct file in base
            file_path = self.base_dir / file_name
        module_name = '_'.join(['new_rede_a'] + rel_parts)
        # Before loading, inject the package config into sys.modules as 'config'
        cfg = load_module_from_path('new_rede_a_config', self.base_dir / 'config.py')
        _orig = sys.modules.get('config')
        sys.modules['config'] = cfg
        try:
            mod = load_module_from_path(module_name, file_path)
        finally:
            if _orig is not None:
                sys.modules['config'] = _orig
            else:
                sys.modules.pop('config', None)
        return mod


def load_portable():
    return PortableLoader(NEW_REDE_A_DIR)

# Import env and config
_config = load_module_from_path('new_rede_a_config', NEW_REDE_A_DIR / 'config.py')

# Some modules inside new-rede-a do `from config import ...`.
# To ensure those imports resolve to the new-rede-a/config.py we just loaded,
# temporarily insert it into sys.modules under the name 'config' before loading
# other modules from this package.
_orig_config_module = sys.modules.get('config')
sys.modules['config'] = _config
try:
    _env = load_module_from_path('new_rede_a_env', NEW_REDE_A_DIR / 'portfolio_environment.py')
finally:
    # Restore previous 'config' module if it existed, otherwise remove our injection
    if _orig_config_module is not None:
        sys.modules['config'] = _orig_config_module
    else:
        sys.modules.pop('config', None)

# Expose the environment class
PortfolioEnv = getattr(_env, 'PortfolioEnv')

# Simple accessor for tests
def import_env_and_config():
    return PortfolioEnv, _config
