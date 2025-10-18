from fastapi import APIRouter
from pathlib import Path
import re
import json

router = APIRouter()


def find_latest_tuned_report(logs_dir: Path):
    # Look for tuned equity CSVs or report files matching the tuned pattern
    pattern = re.compile(r'backtest_ethusd_2y_1h_tuned_(\d{8}T\d{6}Z)')
    best = None
    for p in logs_dir.iterdir():
        m = pattern.search(p.name)
        if m:
            ts = m.group(1)
            if best is None or ts > best[0]:
                best = (ts, p)
    return best


@router.get('/backtest/latest_tuned')
async def latest_tuned():
    logs = Path('logs')
    if not logs.exists():
        return {'ok': False, 'message': 'No logs directory found'}

    found = find_latest_tuned_report(logs)
    if not found:
        return {'ok': False, 'message': 'No tuned backtest logs found'}

    ts, path = found
    # Try to read an accompanying report or equity file to extract end capital
    # Prefer report file ending with _report.txt
    report_files = list(logs.glob(f'backtest_ethusd_2y_1h_tuned_{ts}_report.txt'))
    equity_files = list(logs.glob(f'backtest_ethusd_2y_1h_tuned_{ts}_equity.csv'))

    end_capital = None
    if report_files:
        try:
            txt = report_files[0].read_text(encoding='utf-8')
            # look for End capital line
            m = re.search(r'End capital:\s*([0-9,.]+)', txt)
            if m:
                end_capital = float(m.group(1).replace(',', ''))
        except Exception:
            end_capital = None

    if end_capital is None and equity_files:
        try:
            import pandas as pd

            eq = pd.read_csv(equity_files[0], index_col=0)
            # equity column or first column
            col = eq.columns[0] if len(eq.columns) > 0 else None
            if col:
                end_capital = float(eq.iloc[-1, 0])
        except Exception:
            end_capital = None

    message = f'Tuned run saved to logs\\backtest_ethusd_2y_1h_tuned_{ts}_* .'
    if end_capital is not None:
        message = message + f' End capital: {end_capital:.2f}'

    return {'ok': True, 'timestamp': ts, 'message': message, 'end_capital': end_capital}
import os
from pathlib import Path
from fastapi import APIRouter
import pandas as pd

router = APIRouter()


@router.get('/backtest/status')
async def backtest_status():
    """Return the latest tuned backtest message and end capital.

    Searches the `logs/` directory for files matching
    `backtest_ethusd_2y_1h_tuned_*_equity.csv` and returns a message like:
    "Tuned run saved to logs\backtest_ethusd_2y_1h_tuned_20251017T221236Z_* . End capital: 21924.54"
    """
    logs_dir = Path('logs')
    if not logs_dir.exists():
        return {
            'message': 'No logs directory found',
            'end_capital': None,
        }

    pattern = 'backtest_ethusd_2y_1h_tuned_*_equity.csv'
    files = sorted(logs_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return {
            'message': 'No tuned backtest equity files found',
            'end_capital': None,
        }

    latest = files[0]
    try:
        df = pd.read_csv(latest, index_col=0)
        # equity CSV has a header like 'equity'; take last non-null
        if df.shape[1] >= 1:
            last_val = float(df.iloc[-1, 0])
        else:
            last_val = float(df.iloc[-1].values[0])
    except Exception:
        # fallback: try to parse report txt file with similar prefix
        prefix = str(latest).rsplit('_equity.csv', 1)[0]
        report = Path(prefix + '_report.txt')
        last_val = None
        if report.exists():
            try:
                txt = report.read_text(encoding='utf-8')
                for line in txt.splitlines():
                    if line.lower().startswith('end capital') or 'end capital' in line.lower():
                        # line like: End capital: 21924.54
                        parts = line.split(':')
                        last_val = float(parts[-1].strip())
                        break
            except Exception:
                last_val = None

    # Build the message with backslashes like the sample
    prefix_display = str(latest.parent / latest.stem).replace('/', '\\')
    message = f"Tuned run saved to {prefix_display}_* . End capital: {last_val:.2f}" if last_val is not None else f"Tuned run saved to {prefix_display}_* . End capital: unknown"
    return {'message': message, 'end_capital': last_val}
