#!/usr/bin/env python3
"""Live progress monitor for ``pipelines/*.py`` runs.

Each Pipeline step writes its subprocess output to
``raw-data/pipeline/<script-stem>[_<args>].log``. This script counts
those log files (= steps started in the current run), figures out the
currently-running step from the most-recently-modified log, and
projects ETA from the elapsed time and average step duration.

Usage:
    # Default: assume pipelines/all.py is running. Total step count is
    # derived by importing pipelines/all.py and summing len(p.steps)
    # across every Pipeline in PIPELINES.
    python3 utils/pipeline_progress.py [--tail K]

    # Scope to a specific chapter (auto-imports pipelines/sections/<name>.py
    # to get the step count):
    python3 utils/pipeline_progress.py --pipeline baseline

    # Explicit total when running a custom pipeline:
    python3 utils/pipeline_progress.py --total 42

    # Watch mode: refresh every N seconds.
    python3 utils/pipeline_progress.py --watch 30

The "current run" is identified by walking back through logs sorted
by mtime and stopping at the first gap larger than ``--gap`` minutes
(default 60). If you've rerun the same pipeline multiple times in
quick succession, only the most recent batch counts.
"""
from __future__ import annotations

import argparse
import importlib
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR   = REPO_ROOT / "raw-data" / "pipeline"


def _human(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _total_for(pipeline_name: Optional[str]) -> Optional[int]:
    target = pipeline_name or "all"
    sys.path.insert(0, str(REPO_ROOT))
    try:
        if target == "all":
            mod = importlib.import_module("pipelines.all")
            pipelines = list(getattr(mod, "PIPELINES", []))
        else:
            mod = importlib.import_module(f"pipelines.sections.{target}")
            pipelines = [getattr(mod, "p")]
    except Exception as exc:
        print(f"  ! Could not auto-import pipeline {target!r}: {exc}",
              file=sys.stderr)
        return None
    return sum(len(p.steps) for p in pipelines)


def _current_run_logs(gap_seconds: int) -> list[Path]:
    # Walk descending by mtime; treat a gap > gap_seconds as a run boundary.
    if not LOG_DIR.is_dir():
        return []
    all_logs = sorted(
        LOG_DIR.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not all_logs:
        return []
    run = [all_logs[0]]
    for prev, cur in zip(all_logs, all_logs[1:]):
        if prev.stat().st_mtime - cur.stat().st_mtime > gap_seconds:
            break
        run.append(cur)
    return list(reversed(run))


def _report(total: Optional[int], gap_seconds: int, tail_lines: int) -> None:
    run_logs = _current_run_logs(gap_seconds)
    if not run_logs:
        print(f"No pipeline logs found in {LOG_DIR.relative_to(REPO_ROOT)}.")
        return

    now      = time.time()
    earliest = run_logs[0].stat().st_mtime
    latest   = run_logs[-1].stat().st_mtime
    elapsed  = int(now - earliest)
    n_done   = len(run_logs)
    avg      = int(elapsed / n_done) if n_done else 0
    since    = int(now - latest)

    print(f"Pipeline progress  (logs in {LOG_DIR.relative_to(REPO_ROOT)})")
    if total:
        pct       = 100.0 * n_done / total
        remaining = max(0, (total - n_done) * avg)
        print(f"  {n_done} / {total} steps started "
              f"({pct:5.1f} %)")
        print(f"  elapsed {_human(elapsed)}  "
              f"avg {_human(avg)}/step  "
              f"ETA {_human(remaining)}")
    else:
        print(f"  {n_done} steps started")
        print(f"  elapsed {_human(elapsed)}  avg {_human(avg)}/step")

    print(f"  Currently running: {run_logs[-1].stem}")
    print(f"    last update {_human(since)} ago "
          f"({time.strftime('%H:%M:%S', time.localtime(latest))})")

    stall_threshold = max(120, 3 * avg)
    if total and n_done < total and since > stall_threshold:
        print(f"  ! Warning: no new log activity in {_human(since)} -- "
              f"the pipeline may be stalled.")

    if tail_lines > 0:
        log = run_logs[-1]
        try:
            text = log.read_text(errors="replace").splitlines()
        except OSError as exc:
            print(f"  ! Could not read {log.name}: {exc}")
            return
        print(f"\n  --- tail of {log.name} ({len(text)} lines total) ---")
        for line in text[-tail_lines:]:
            print(f"  {line}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--total", type=int, default=None,
        help="Expected total step count. If omitted, derived from the "
             "selected pipeline (--pipeline).",
    )
    ap.add_argument(
        "--pipeline", default=None,
        help="Pipeline name for auto-total: 'all' (default) sums every "
             "Pipeline in pipelines/all.py; or a chapter name "
             "(e.g. 'baseline') to use pipelines/sections/<name>.py.",
    )
    ap.add_argument(
        "--gap", type=float, default=60.0,
        help="Mtime gap (minutes) that separates distinct pipeline runs. "
             "Default 60 -- raise if a single step legitimately takes "
             "longer than this and would otherwise look like a run "
             "boundary.",
    )
    ap.add_argument(
        "--tail", type=int, default=0,
        help="Show the last K lines of the currently-running step's log.",
    )
    ap.add_argument(
        "--watch", type=float, default=0.0,
        help="Re-print every N seconds (Ctrl-C to stop). Default 0 = "
             "one-shot.",
    )
    args = ap.parse_args()

    total = args.total if args.total is not None else _total_for(args.pipeline)
    gap_seconds = int(args.gap * 60)

    if args.watch > 0:
        try:
            while True:
                sys.stdout.write("\x1b[2J\x1b[H")
                _report(total, gap_seconds, args.tail)
                sys.stdout.flush()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print()
    else:
        _report(total, gap_seconds, args.tail)


if __name__ == "__main__":
    main()
