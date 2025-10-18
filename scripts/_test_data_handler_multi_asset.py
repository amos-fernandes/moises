import sys
import os
import pandas as pd
from pathlib import Path

# Ensure repository root is on sys.path so we can import the portable loader
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from new_rede_a_portable_import import load_portable
import numpy as np
import numpy as np
import traceback

def main():
    try:
        # Some external libs used by the module (alpha_vantage, twelvedata) may not be installed
        # Create lightweight dummy modules to satisfy imports while testing feature calculation
        import types
        if 'alpha_vantage' not in sys.modules:
            alpha_mod = types.ModuleType('alpha_vantage')
            ts_mod = types.ModuleType('alpha_vantage.timeseries')
            fx_mod = types.ModuleType('alpha_vantage.foreignexchange')
            cc_mod = types.ModuleType('alpha_vantage.cryptocurrencies')
            # minimal classes
            class TimeSeries:
                def __init__(self, *a, **k):
                    pass
            class ForeignExchange:
                def __init__(self, *a, **k):
                    pass
            class CryptoCurrencies:
                def __init__(self, *a, **k):
                    pass
            ts_mod.TimeSeries = TimeSeries
            fx_mod.ForeignExchange = ForeignExchange
            cc_mod.CryptoCurrencies = CryptoCurrencies
            sys.modules['alpha_vantage'] = alpha_mod
            sys.modules['alpha_vantage.timeseries'] = ts_mod
            sys.modules['alpha_vantage.foreignexchange'] = fx_mod
            sys.modules['alpha_vantage.cryptocurrencies'] = cc_mod
        if 'twelvedata' not in sys.modules:
            td_mod = types.ModuleType('twelvedata')
            class TDClient:
                def __init__(self, *a, **k):
                    pass
            td_mod.TDClient = TDClient
            sys.modules['twelvedata'] = td_mod

        loader = load_portable()
        dh = loader.load_module('new-rede-a.data_handler_multi_asset')
        print('module_loaded', hasattr(dh, 'calculate_all_features_for_single_asset'))

        idx = pd.date_range('2023-01-01', periods=120, freq='H')
        df = pd.DataFrame({
            'open': np.linspace(100,110,120) + np.random.randn(120)*0.1,
            'high': np.linspace(100.5,110.5,120) + np.random.randn(120)*0.2,
            'low': np.linspace(99.5,109.5,120) + np.random.randn(120)*0.2,
            'close': np.linspace(100,110,120) + np.random.randn(120)*0.15,
            'volume': np.random.randint(100,1000,size=120),
        }, index=idx)

        res = dh.calculate_all_features_for_single_asset(df)
        print('result_type', type(res))
        if isinstance(res, pd.DataFrame):
            print('columns (first 40):', list(res.columns)[:40])
            canonical = ['open_div_atr','close_div_atr','sma_10_div_atr','log_return','buy_condition_v1']
            print('contains_canonical:', all(c in res.columns for c in canonical))
            # print a small sample
            print('\n--- sample head ---')
            print(res.head(3).to_dict())
            # diagnostics
            print('\n--- diagnostics ---')
            import numpy as _np
            any_inf = res.isin([_np.inf, -_np.inf]).any().any()
            any_nan = res.isna().any().any()
            max_abs = res.abs().max().max()
            print('any_inf:', any_inf)
            print('any_nan:', any_nan)
            print('max_abs_value:', max_abs)
            cap = 1e3
            print('any_abs_gt_cap:', (res.abs() > cap).any().any())
        else:
            print('no dataframe returned')
    except Exception as e:
        print('EXCEPTION in test:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
