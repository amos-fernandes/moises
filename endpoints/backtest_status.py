from fastapi import APIRouter
from pathlib import Path
import pandas as pd
import re

router = APIRouter()


def _read_last_equity(csv_path: Path):
    try:
        df = pd.read_csv(csv_path, index_col=0)
        # If single-column equity series, get last value
        if df.shape[1] == 1:
            return float(df.iloc[-1, 0])
        # otherwise try first column
        return float(df.iloc[-1, 0])
    except Exception:
        return None


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
    last_val = _read_last_equity(latest)
    if last_val is None:
        # fallback: try to parse report txt file with similar prefix
        prefix = str(latest).rsplit('_equity.csv', 1)[0]
        report = Path(prefix + '_report.txt')
        if report.exists():
            try:
                txt = report.read_text(encoding='utf-8')
                m = re.search(r'End capital:\s*([0-9,.]+)', txt)
                if m:
                    last_val = float(m.group(1).replace(',', ''))
            except Exception:
                last_val = None

    prefix_display = str(latest.parent / latest.stem).replace('/', '\\')
    if last_val is not None:
        message = f"Tuned run saved to {prefix_display}_* . End capital: {last_val:.2f}"
    else:
        message = f"Tuned run saved to {prefix_display}_* . End capital: unknown"
    report_path = None
    # report path if exists
    prefix = str(latest).rsplit('_equity.csv', 1)[0]
    report = Path(prefix + '_report.txt')
    if report.exists():
        report_path = str(report)

    return {'message': message, 'end_capital': last_val, 'report_path': report_path}
