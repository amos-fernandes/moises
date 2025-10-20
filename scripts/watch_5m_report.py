"""Watch scripts/5m_runs_report.json for changes and print concise diffs to stdout.

Usage:
    python .\scripts\watch_5m_report.py --file scripts/5m_runs_report.json --interval 5
"""
import argparse
import json
import time
from pathlib import Path


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def diff_reports(old, new):
    if old is None:
        return {'new': new}
    diffs = {}
    # compare runs dictionary
    old_runs = old.get('runs', {})
    new_runs = new.get('runs', {})
    for k, v in new_runs.items():
        if k not in old_runs:
            diffs.setdefault('added', {})[k] = v
        else:
            # simple check: stringify and compare
            if json.dumps(old_runs[k], sort_keys=True) != json.dumps(v, sort_keys=True):
                diffs.setdefault('updated', {})[k] = {'old': old_runs[k], 'new': v}
    return diffs


def pretty_print_diffs(diffs):
    if not diffs:
        return
    if 'new' in diffs:
        print('Full report read:')
        print(json.dumps(diffs['new'], indent=2))
        return
    if 'added' in diffs:
        for k, v in diffs['added'].items():
            arts = v.get('artifacts') or []
            sizes = []
            for a in arts:
                try:
                    sizes.append(str(Path(a).stat().st_size))
                except Exception:
                    sizes.append('N/A')
            print(f"[ADDED] {k}: artifacts={arts} sizes={sizes} final_equity={v.get('final_equity')}")
    if 'updated' in diffs:
        for k, v in diffs['updated'].items():
            old = v['old']
            new = v['new']
            print(f"[UPDATED] {k}")
            oa = old.get('artifacts')
            na = new.get('artifacts')
            if oa != na:
                print(f"  artifacts changed -> {na}")
            of = old.get('final_equity')
            nf = new.get('final_equity')
            if of != nf:
                print(f"  final_equity changed -> {nf}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', default='scripts/5m_runs_report.json')
    p.add_argument('--interval', type=int, default=5)
    args = p.parse_args()

    path = Path(args.file)
    last = None
    print(f"Watching {path} every {args.interval}s. Press Ctrl-C to stop.")
    try:
        while True:
            if path.exists():
                curr = load_json(path)
                if curr is not None:
                    diffs = diff_reports(last, curr)
                    if diffs:
                        pretty_print_diffs(diffs)
                    last = curr
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\nWatcher stopped by user')

if __name__ == '__main__':
    main()
