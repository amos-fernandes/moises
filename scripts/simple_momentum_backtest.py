"""Simple momentum + volatility-target backtest (synthetic price) to establish a robust baseline.
Produces an equity CSV and prints metrics.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import json


def generate_gbm(S0=1000, mu=0.0, sigma=0.8, days=365*2, freq_per_day=24, seed=42):
    np.random.seed(seed)
    n = days * freq_per_day
    dt = 1.0 / (252 * freq_per_day)
    returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * np.random.randn(n)
    price = S0 * np.exp(np.cumsum(returns))
    idx = pd.date_range(end=pd.Timestamp.now(tz='UTC'), periods=n, freq=f'{int(24*60/freq_per_day)}T')
    return pd.Series(price, index=idx, name='close')


def backtest_momentum(price: pd.Series, lookback=24*7, target_vol_ann=0.2, fee=0.0005, slippage=0.0005):
    # compute returns and realized vol (rolling)
    ret = price.pct_change().fillna(0)
    roll_vol = ret.rolling(window=lookback).std() * np.sqrt(252*24)
    # momentum signal: past return over lookback
    mom = price.pct_change(periods=lookback).fillna(0)
    # desired position: +1 if mom>0, -1 if mom<0
    raw_pos = np.sign(mom)
    # scale position by volatility target: pos * (target_vol / realized_vol)
    alloc = target_vol_ann / (roll_vol + 1e-9)
    pos = raw_pos * alloc
    # cap position to [-1,1]
    pos = pos.clip(-1,1).fillna(0)

    equity = 100000.0
    cash = equity
    size = 0.0
    records = []

    for t in range(1, len(price)):
        price_t = price.iloc[t]
        price_prev = price.iloc[t-1]
        desired_pos = pos.iloc[t]
        # compute desired notional
        desired_notional = desired_pos * equity
        # current notional
        current_notional = size * price_prev
        # adjust size
        notional_change = desired_notional - current_notional
        if abs(notional_change) > 0:
            # transaction costs
            trade_cost = abs(notional_change) * (fee + slippage)
        else:
            trade_cost = 0.0
        # execute: update size based on previous price
        if price_prev > 0:
            size = desired_notional / price_prev
        # mark-to-market
        equity = size * price_t - trade_cost
        records.append({'timestamp': price.index[t], 'price': float(price_t), 'equity': float(equity), 'position': float(size)})

    df = pd.DataFrame(records)
    return df


def analyze(df):
    series = df['equity']
    returns = series.pct_change().fillna(0)
    total_return = series.iloc[-1] / series.iloc[0] - 1
    years = (len(series) / (365*24))
    cagr = (series.iloc[-1] / series.iloc[0]) ** (1.0/years) - 1 if years>0 else np.nan
    vol_ann = returns.std() * np.sqrt(365*24)
    sharpe = (returns.mean() * 365*24) / (returns.std() * np.sqrt(365*24)) if returns.std()>0 else np.nan
    roll_max = series.cummax()
    max_dd = ((series - roll_max)/roll_max).min()
    print('Synthetic momentum backtest results:')
    print(f'Start {series.iloc[0]:.2f}, End {series.iloc[-1]:.2f}, Total return {total_return*100:.2f}%')
    print(f'CAGR {cagr*100:.2f}%, Ann vol {vol_ann*100:.2f}%, Sharpe {sharpe:.2f}, MaxDD {max_dd*100:.2f}%')


if __name__ == '__main__':
    price = generate_gbm(S0=2000, mu=0.05, sigma=0.9, days=365*2, freq_per_day=24)
    df = backtest_momentum(price, lookback=24*7, target_vol_ann=0.15)
    out = Path('out')
    out.mkdir(exist_ok=True)
    path = out / 'synthetic_momentum_equity.csv'
    df.to_csv(path, index=False)
    analyze(df)
