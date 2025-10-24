"""Analyze backtest equity CSV and print performance metrics.
Usage: python scripts/analyze_equity.py [path/to/equity.csv]
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np


def analyze(path: Path):
    df = pd.read_csv(path, parse_dates=True)
    # Try to find an equity column
    possible = [c for c in df.columns if 'equity' in c.lower() or 'balance' in c.lower() or 'wallet' in c.lower()]
    if not possible:
        # if timestamp + value columns common
        if df.shape[1] >= 2:
            col = df.columns[1]
        else:
            raise ValueError('No equity-like column found')
    else:
        col = possible[0]

    series = df[col].astype(float)
    # Ensure index is datetime if possible
    # compute returns
    returns = series.pct_change().fillna(0)
    total_return = series.iloc[-1] / series.iloc[0] - 1.0
    # annualization factor: infer frequency from timestamps if present
    freq = None
    if 'date' in [c.lower() for c in df.columns] or 'timestamp' in [c.lower() for c in df.columns]:
        # try to parse first col as datetime
        try:
            idx = pd.to_datetime(df.iloc[:,0])
            # compute avg days between samples
            delta = (idx.iloc[-1] - idx.iloc[0]).total_seconds()
            n = len(idx)
            secs_per_sample = delta / max(1, n-1)
            samples_per_year = 365*24*3600 / secs_per_sample
            annual_factor = samples_per_year
        except Exception:
            annual_factor = 252
    else:
        # fallback to hourly assumption given backtests are 1h
        annual_factor = 365*24

    # annualized return (CAGR approx)
    years = (len(series) / annual_factor)
    if years > 0:
        cagr = (series.iloc[-1] / series.iloc[0]) ** (1.0/years) - 1.0
    else:
        cagr = np.nan

    # annualized volatility
    vol_ann = returns.std() * np.sqrt(annual_factor)

    # Sharpe (assume rf=0)
    sharpe = (returns.mean() * annual_factor) / (returns.std() * np.sqrt(annual_factor)) if returns.std() > 0 else np.nan

    # Max drawdown
    cum = series
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    max_dd = drawdown.min()

    print(f'File: {path}')
    print(f'Equity column: {col}')
    print(f'Start: {series.iloc[0]:.2f}, End: {series.iloc[-1]:.2f}, Total return: {total_return*100:.2f}%')
    print(f'Approx years: {years:.4f}, CAGR: {cagr*100:.2f}%')
    print(f'Annual vol: {vol_ann*100:.2f}%, Sharpe (rf=0): {sharpe:.2f}, MaxDD: {max_dd*100:.2f}%')


if __name__ == '__main__':
    p = Path(sys.argv[1]) if len(sys.argv)>1 else None
    if p is not None and p.exists():
        analyze(p)
    else:
        files = sorted(list(Path('logs').glob('backtest_*equity.csv')), key=lambda x: x.stat().st_mtime)
        if not files:
            print('No equity files found in logs/')
            sys.exit(1)
        analyze(files[-1])
