#!/usr/bin/env python3
"""Live progress monitor for any in-progress ParameterOptimization sweep.

Counts completed cells (each finished cell writes
``ParamOptimizationMetrics_run<N>.csv``), reports elapsed time, average
seconds-per-cell, and ETA. Optionally prints the current top-K cells
across the partial dataset so you can spot whether the early winners
look reasonable without waiting for the full run.

Usage:
    # Auto-detect: pick the most-recently-modified ParamOptimization
    # subdir and use it.
    python3 utils/check_progress.py [--total N] [--top K]

    # Explicit:
    python3 utils/check_progress.py \
        raw-data/Results/AlgorithmOptimizations/ParameterOptimization/RefinedGrid \
        --total 864 [--top 5]

    # Aggregate across every 1D-sweep axis under ParameterOptimization/
    # (useful while run_all_1d_sweeps.py is mid-flight):
    python3 utils/check_progress.py --aggregate --total 63 [--top 5]

Top-K mode requires a Cyl Baseline CSV next door at
``ParameterOptimization/Baseline/`` so it can compute Δ vs Cyl. If the
Baseline isn't present, top-K is skipped and only progress is shown.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Optional


REPO_HINTS = (
    Path("raw-data/Results/AlgorithmOptimizations/ParameterOptimization"),
    Path.cwd() / "raw-data/Results/AlgorithmOptimizations/ParameterOptimization",
)

# Sweep-dir names that aren't 1D axes (don't aggregate over these).
NON_AXIS_DIRS = {
    "Baseline", "Grid", "Confirmation", "RefinedGrid", "CoarseGrid",
    "Probe", "EventsSaturation",
}

# Defaults if configs/parameter_optimization/selection_rules.yaml is absent.
DEFAULT_TOLERANCE_PP            = 0.1
DEFAULT_FASTEST_EFFICIENCY_FLOOR = 0.95


def _load_selection_rules() -> dict:
    fallback = {
        "tolerance_pp": DEFAULT_TOLERANCE_PP,
        "best_tolerance_pp": DEFAULT_TOLERANCE_PP,
        "fastest_efficiency_floor": DEFAULT_FASTEST_EFFICIENCY_FLOOR,
    }
    cfg_path = (Path(__file__).resolve().parent.parent
                / "configs" / "parameter_optimization" / "selection_rules.yaml")
    if not cfg_path.exists():
        return fallback
    try:
        import yaml
        with cfg_path.open() as f:
            cfg = yaml.safe_load(f) or {}
        global_tol = float(cfg.get("tolerance_pp", DEFAULT_TOLERANCE_PP))
        return {
            "tolerance_pp":             global_tol,
            "best_tolerance_pp":        float(cfg.get("best_tolerance_pp", global_tol)),
            "fastest_efficiency_floor": float(cfg.get("fastest_efficiency_floor",
                                                       DEFAULT_FASTEST_EFFICIENCY_FLOOR)),
        }
    except Exception:
        return fallback


def _param_opt_root() -> Optional[Path]:
    for hint in REPO_HINTS:
        if hint.is_dir():
            return hint
    return None


def _autodetect_grid_dir() -> Optional[Path]:
    root = _param_opt_root()
    if root is None:
        return None
    candidates = []
    for p in root.iterdir():
        if not p.is_dir() or p.name == "Baseline":
            continue
        metrics = list(p.glob("ParamOptimizationMetrics_run*.csv"))
        if metrics:
            latest = max(m.stat().st_mtime for m in metrics)
            candidates.append((latest, p))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return None


def _aggregate_grid_dirs() -> list[Path]:
    root = _param_opt_root()
    if root is None:
        return []
    out = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if p.name in NON_AXIS_DIRS or p.name.startswith("legacy_"):
            continue
        if list(p.glob("ParamOptimizationMetrics_run*.csv")):
            out.append(p)
    return out


def _baseline_dir(grid_dir: Path) -> Optional[Path]:
    parent = grid_dir.parent
    cand = parent / "Baseline"
    if (cand / "ParamOptimizationMetrics.csv").exists():
        return cand
    return None


def _read_baseline(baseline_dir: Path) -> Optional[dict]:
    metrics = baseline_dir / "ParamOptimizationMetrics.csv"
    timing  = baseline_dir / "ParamOptimizationTiming.csv"
    if not metrics.exists() or not timing.exists():
        return None
    with metrics.open() as f:
        row = next(csv.DictReader(f))
    with timing.open() as f:
        last = None
        for r in csv.DictReader(f):
            last = r
    if last is None:
        return None
    return {
        "eff":  float(row["seeding_particle_efficiency"]),
        "fake": float(row["seeding_particle_fake_ratio"]),
        "dup":  float(row["seeding_particle_duplicate_ratio"]),
        "time": float(last["AVERAGE_TIME_NS"]) / 1e6,
    }


def _read_cell(grid_dir: Path, n: int) -> Optional[dict]:
    metrics = grid_dir / f"ParamOptimizationMetrics_run{n}.csv"
    timing  = grid_dir / f"ParamOptimizationTiming_run{n}.csv"
    if not metrics.exists() or not timing.exists():
        return None
    try:
        with metrics.open() as f:
            row = next(csv.DictReader(f))
        with timing.open() as f:
            last = None
            for r in csv.DictReader(f):
                last = r
        if last is None:
            return None
        return {
            "n":    n,
            "eff":  float(row["seeding_particle_efficiency"]),
            "fake": float(row["seeding_particle_fake_ratio"]),
            "dup":  float(row["seeding_particle_duplicate_ratio"]),
            "time": float(last["AVERAGE_TIME_NS"]) / 1e6,
        }
    except (StopIteration, KeyError, ValueError):
        return None


def _fmt_metrics(c: dict, baseline: Optional[dict]) -> str:
    if baseline:
        d_eff  = (c['eff']  - baseline['eff'])  * 100
        d_fake = (c['fake'] - baseline['fake']) * 100
        d_dup  = (c['dup']  - baseline['dup'])  * 100
        d_time = c['time'] - baseline['time']
        return (f"eff={c['eff']:.4f} ({d_eff:+.2f}pp)  "
                f"fake={c['fake']:.4f} ({d_fake:+.2f}pp)  "
                f"dup={c['dup']:.4f} ({d_dup:+.2f}pp)  "
                f"time={c['time']:.1f}ms ({d_time:+.1f}ms)")
    return (f"eff={c['eff']:.4f}  fake={c['fake']:.4f}  "
            f"dup={c['dup']:.4f}  time={c['time']:.1f}ms")


def _human_secs(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def _report_progress(metrics_files, total, label):
    done = len(metrics_files)
    if done == 0:
        print(f"{label}: no cells finished yet.")
        return None

    first_mtime = min(p.stat().st_mtime for p in metrics_files)
    last_mtime  = max(p.stat().st_mtime for p in metrics_files)
    now = time.time()

    elapsed = int(now - first_mtime)
    avg     = int(elapsed / done) if done else 0
    since_last = int(now - last_mtime)

    if total:
        pct = 100 * done / total
        remaining = (total - done) * avg
        print(f"Done: {done} / {total}  ({pct:5.1f} %)")
        print(f"  elapsed {_human_secs(elapsed)}  avg {avg}s/cell  "
              f"ETA {_human_secs(remaining)}  "
              f"(last cell finished {_human_secs(since_last)} ago)")
    else:
        print(f"Done: {done} cells")
        print(f"  elapsed {_human_secs(elapsed)}  avg {avg}s/cell  "
              f"(last cell finished {_human_secs(since_last)} ago)")

    if since_last > max(120, 3 * avg) and total and done < total:
        print(f"  ! Warning: no new cell in {_human_secs(since_last)} — "
              f"the sweep may be stalled.")

    return done


def _apply_rules(cells, baseline, rules):
    # Returns {rule_name: ranked_cells}, or None when baseline is missing
    # (deltas can't be evaluated for the "best" rule without it).
    if baseline is None:
        return None

    eps      = rules["tolerance_pp"] / 100.0
    eps_best = rules.get("best_tolerance_pp", rules["tolerance_pp"]) / 100.0
    floor    = rules["fastest_efficiency_floor"]

    def _d(c):
        return (
            c["eff"]  - baseline["eff"],
            c["fake"] - baseline["fake"],
            c["dup"]  - baseline["dup"],
        )

    max_eff = sorted(cells, key=lambda c: (-c["eff"], c["time"]))

    best_feasible = [c for c in cells
                     if (_d(c)[0] >= -eps_best
                         and _d(c)[1] <= eps_best
                         and _d(c)[2] <= eps_best)]
    best_feasible.sort(key=lambda c: (c["time"], -c["eff"]))

    fast_feasible = [c for c in cells if c["eff"] >= floor]
    fast_feasible.sort(key=lambda c: (c["time"], -c["eff"]))

    return {
        "max_efficiency": max_eff,
        "best":           best_feasible,
        "fastest":        fast_feasible,
    }


def _show_topk_rules(cells, baseline, rules, top_k, tag_for):
    if baseline is None:
        # Falls back to by-metric leaderboards when rules can't apply.
        total = len(cells)
        for label, key in (
            ("eff (high)", lambda c: (-c["eff"], c["time"])),
            ("fake (low)", lambda c: (c["fake"], c["time"])),
            ("time (low)", lambda c: (c["time"], -c["eff"])),
        ):
            print(f"\n=== Top {top_k} cells by {label} (partial: {total} cells) ===")
            for c in sorted(cells, key=key)[:top_k]:
                print(f"  {tag_for(c)}  {_fmt_metrics(c, baseline)}")
        return

    eps_pp      = rules["tolerance_pp"]
    eps_pp_best = rules.get("best_tolerance_pp", rules["tolerance_pp"])
    floor       = rules["fastest_efficiency_floor"]
    ranked      = _apply_rules(cells, baseline, rules)
    total       = len(cells)

    if eps_pp_best == 0:
        best_desc = "argmin time, strictly better than Cyl on every metric"
    else:
        best_desc = (f"argmin time, no regression vs Cyl beyond "
                     f"{eps_pp_best:.1f}pp on any metric")

    rule_headers = (
        ("max_efficiency", "argmax eff (no constraints)"),
        ("best",           best_desc),
        ("fastest",        f"argmin time, eff at or above {floor:.2f} "
                           f"(no fake/dup constraints)"),
    )
    for rule_name, rule_desc in rule_headers:
        lst = ranked[rule_name]
        if rule_name == "max_efficiency":
            head = f"=== Top {top_k} {rule_name} (partial: {total} cells) ==="
        else:
            head = (f"=== Top {top_k} {rule_name} "
                    f"(partial: {total} cells, {len(lst)} feasible) ===")
        print(f"\n{head}")
        print(f"    rule: {rule_desc}")
        if not lst:
            print("    (no feasible cells under this rule yet)")
            continue
        for c in lst[:top_k]:
            print(f"  {tag_for(c)}  {_fmt_metrics(c, baseline)}")


def _show_topk_single(grid_dir, metrics_files, baseline, rules, top_k):
    cells = []
    for p in metrics_files:
        n = int(p.stem.split("_run")[1])
        c = _read_cell(grid_dir, n)
        if c is not None:
            cells.append(c)
    _show_topk_rules(cells, baseline, rules, top_k,
                     tag_for=lambda c: f"cell {c['n']:>4}")


def _show_topk_aggregate(grid_dirs, baseline, rules, top_k):
    cells = []
    for d in grid_dirs:
        for p in d.glob("ParamOptimizationMetrics_run*.csv"):
            n = int(p.stem.split("_run")[1])
            c = _read_cell(d, n)
            if c is not None:
                c["axis"] = d.name
                cells.append(c)
    _show_topk_rules(cells, baseline, rules, top_k,
                     tag_for=lambda c: f"{c['axis']}/run{c['n']}".ljust(35))


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "grid_dir", nargs="?",
        help="Sweep dir containing ParamOptimizationMetrics_run<N>.csv. "
             "If omitted, auto-detects the most recent grid.",
    )
    ap.add_argument(
        "--total", type=int, default=None,
        help="Expected total cell count for ETA / percent-complete. "
             "If omitted, percent and ETA are skipped. In --aggregate "
             "mode, this is the total across every axis.",
    )
    ap.add_argument(
        "--top", type=int, default=0,
        help="Print top-K cells per pick_winners rule (max_efficiency, "
             "best, fastest) against the partial data. Default 0 (skip). "
             "Falls back to by-metric rankings if no Cyl baseline is "
             "available.",
    )
    ap.add_argument(
        "--aggregate", "-a", action="store_true",
        help="Aggregate across every 1D-axis sweep dir under "
             "ParameterOptimization/. Skips Baseline / Grid / "
             "Confirmation / legacy_* dirs. Useful while "
             "run_all_1d_sweeps.py is mid-flight.",
    )
    ap.add_argument(
        "--tolerance-pp", type=float, default=None,
        help="Override the tolerance_pp from selection_rules.yaml "
             "(default 0.1 pp).",
    )
    ap.add_argument(
        "--fastest-floor", type=float, default=None,
        help="Override the fastest_efficiency_floor from "
             "selection_rules.yaml (default 0.95).",
    )
    args = ap.parse_args()

    rules = _load_selection_rules()
    if args.tolerance_pp is not None:
        rules["tolerance_pp"] = float(args.tolerance_pp)
    if args.fastest_floor is not None:
        rules["fastest_efficiency_floor"] = float(args.fastest_floor)

    if args.aggregate:
        grid_dirs = _aggregate_grid_dirs()
        if not grid_dirs:
            sys.exit("No 1D-axis sweep dirs found under "
                     "ParameterOptimization/. Pass an explicit path or "
                     "run from the project root.")

        per_dir = []
        all_metrics = []
        for d in grid_dirs:
            ms = list(d.glob("ParamOptimizationMetrics_run*.csv"))
            per_dir.append((d, ms))
            all_metrics.extend(ms)

        print(f"Aggregate across {len(grid_dirs)} axis dirs:")
        for d, ms in per_dir:
            print(f"  {d.name:<30}  {len(ms):>4} cells done")
        print()

        done = _report_progress(all_metrics, args.total, "Aggregate")
        if done is None or args.top <= 0:
            return

        baseline = None
        base_dir = _baseline_dir(grid_dirs[0])
        if base_dir is not None:
            baseline = _read_baseline(base_dir)
            if baseline:
                print(f"\nCyl baseline: eff={baseline['eff']:.4f}  "
                      f"fake={baseline['fake']:.4f}  dup={baseline['dup']:.4f}  "
                      f"time={baseline['time']:.1f}ms")

        _show_topk_aggregate(grid_dirs, baseline, rules, args.top)
        return

    grid_dir = Path(args.grid_dir) if args.grid_dir else _autodetect_grid_dir()
    if grid_dir is None or not grid_dir.is_dir():
        sys.exit("No grid dir found. Pass an explicit path "
                 "or run from the project root.")

    metrics_files = sorted(grid_dir.glob("ParamOptimizationMetrics_run*.csv"))
    print(f"Sweep dir: {grid_dir}")

    done = _report_progress(metrics_files, args.total, str(grid_dir))
    if done is None or args.top <= 0:
        return

    baseline = None
    base_dir = _baseline_dir(grid_dir)
    if base_dir is not None:
        baseline = _read_baseline(base_dir)
        if baseline:
            print(f"\nCyl baseline: eff={baseline['eff']:.4f}  "
                  f"fake={baseline['fake']:.4f}  dup={baseline['dup']:.4f}  "
                  f"time={baseline['time']:.1f}ms")

    _show_topk_single(grid_dir, metrics_files, baseline, rules, args.top)


if __name__ == "__main__":
    main()
