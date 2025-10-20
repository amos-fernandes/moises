"""
Monitor 5M runs directory for completion, collect final capital and basic model artifact checks.
Usage: python .\scripts\monitor_5m_runs.py --dir src/model/5m_runs --timeout 86400
"""
import argparse
import json
import os
import time
from pathlib import Path


def read_last_equity_from_logs(logs_dir: Path):
    # naive: scan logs for csv files named *equity*.csv and read last column
    for f in sorted(logs_dir.glob("**/*equity*.csv"), key=os.path.getmtime, reverse=True):
        try:
            import pandas as pd
            df = pd.read_csv(f)
            if df.empty:
                continue
            # assume last numeric column contains equity
            for col in reversed(df.columns.tolist()):
                try:
                    val = float(df[col].dropna().values[-1])
                    return f, val
                except Exception:
                    continue
        except Exception:
            continue
    return None, None


def check_model_dir(d: Path):
    # check presence of policy.zip or best_model.zip (SB3) or .pth (torch)
    found = []
    for pat in ("**/policy.zip", "**/best_model.zip", "**/*.zip", "**/*.pth", "**/*.pt"):
        for p in d.glob(pat):
            found.append(p)
    return found


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default="src/model/5m_runs")
    p.add_argument("--logs", default="logs")
    p.add_argument("--timeout", type=int, default=86400)
    p.add_argument("--interval", type=int, default=60)
    args = p.parse_args()

    root = Path(args.dir)
    logs_dir = Path(args.logs)
    deadline = time.time() + args.timeout

    report = {"start_time": time.time(), "runs": {}}

    while time.time() < deadline:
        for asset_dir in root.iterdir():
            if not asset_dir.is_dir():
                continue
            key = asset_dir.name
            if key not in report["runs"]:
                report["runs"][key] = {"checked_at": None, "artifacts": [], "final_equity": None}
            found = check_model_dir(asset_dir)
            report["runs"][key]["checked_at"] = time.time()
            report["runs"][key]["artifacts"] = [str(p) for p in found]
            if report["runs"][key]["final_equity"] is None:
                fp, val = read_last_equity_from_logs(logs_dir)
                if fp:
                    report["runs"][key]["final_equity"] = {"path": str(fp), "value": val}
        # write partial report
        with open("scripts/5m_runs_report.json", "w") as fh:
            json.dump(report, fh, indent=2)
        time.sleep(args.interval)
    print("Timeout reached, final report written to scripts/5m_runs_report.json")


if __name__ == '__main__':
    main()
