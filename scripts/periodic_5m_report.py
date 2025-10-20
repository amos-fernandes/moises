"""
Periodic reporter for 5M runs: every interval seconds it snapshots `scripts/5m_runs_report.json`
and appends a timestamped copy to `scripts/5m_runs_progress.log` so we have a concise time series of monitor snapshots.
Run this in background alongside the monitor.
"""
import time
import json
from pathlib import Path

REPORT = Path("scripts/5m_runs_report.json")
OUTLOG = Path("scripts/5m_runs_progress.log")
INTERVAL = 15 * 60  # 15 minutes

if __name__ == '__main__':
    # write an immediate snapshot
    while True:
        ts = time.time()
        if REPORT.exists():
            try:
                j = json.loads(REPORT.read_text())
            except Exception as e:
                j = {"error": f"failed to read report: {e}"}
        else:
            j = {"error": "report not found"}
        snapshot = {"ts": ts, "report": j}
        OUTLOG.parent.mkdir(parents=True, exist_ok=True)
        with OUTLOG.open("a", encoding="utf8") as fh:
            fh.write(json.dumps(snapshot) + "\n")
        # sleep until next round
        time.sleep(INTERVAL)
