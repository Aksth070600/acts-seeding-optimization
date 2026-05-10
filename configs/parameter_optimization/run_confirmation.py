"""Stage 4 of the parameter-optimisation pipeline: events=50
Confirmation of the top grid candidates.

Combines two responsibilities into a single step:

  1. Read the grid measurements (events=5) and apply the three
     selection rules to identify top-K candidates per rule.
  2. Re-run those candidates at the confirmation event count
     (default 50) so the strict rules can later be applied to
     high-statistics measurements.

Reads
  raw-data/.../ParameterOptimization/Grid/results.csv   — grid output
  raw-data/.../ParameterOptimization/Baseline/          — Cyl baseline
  configs/parameter_optimization/grid.yaml              — grid axis order
  configs/parameter_optimization/anchor.yaml            — non-axis defaults
  configs/parameter_optimization/selection_rules.yaml   — tolerance, floor
  configs/parameter_optimization/confirmation.yaml      — events count

Writes
  raw-data/.../ParameterOptimization/Confirmation/
    ParamOptimizationTiming_run<i>.csv  (per-cell, canonical)
    ParamOptimizationMetrics_run<i>.csv (per-cell, canonical)
    candidates.yaml                     (params per cell, keyed by the
                                         proposing rule + run order)
    results.csv                         (derived summary; same schema
                                         as Grid/results.csv)

``pick_winners.py`` reads these to apply the strict rules.

Usage::

    python3 configs/parameter_optimization/run_confirmation.py [--top 5]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.append(str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO,
    load_anchor, load_confirmation, load_grid, load_selection_rules,
    make_workflow, render_overrides,
)

sys.path.append(str(REPO / "figure-gen"))
from parameter_scan_plotter import load_baseline, load_sweep_grids  # noqa: E402


RAW_DIR      = REPO / "raw-data" / "Results" / "AlgorithmOptimizations" / "ParameterOptimization"
GRID_DIR     = RAW_DIR / "Grid"
BASELINE_DIR = RAW_DIR / "Baseline"
CONFIRM_DIR  = RAW_DIR / "Confirmation"
DATA_DIR_REL = "Results/AlgorithmOptimizations/ParameterOptimization/Confirmation"

META_KEYS = {"events", "notes"}


def _read_grid_measurements() -> tuple[list[dict], list[str]]:
    """Load Grid/results.csv into rows with the same shape ``_apply_rules``
    expects. Returns (rows, ordered axis-key list)."""
    csv_path = GRID_DIR / "results.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found — run run_grid.py first."
        )
    df = pd.read_csv(csv_path)
    grid = load_grid()
    axis_keys = [k for k in grid.keys() if k not in META_KEYS]
    rows: list[dict] = []
    for _, r in df.iterrows():
        rows.append({
            "cell_id": int(r["cell_id"]),
            "params":  {k: r[k] for k in axis_keys},
            "abs": {
                "eff":  float(r["eff"]),
                "fake": float(r["fake"]),
                "dup":  float(r["dup"]),
                "time": float(r["time_ms"]),
            },
        })
    return rows, axis_keys


def _select_candidates(rows: list[dict], base: dict, rules: dict,
                       top_n: int) -> dict[str, list[dict]]:
    """Apply each rule's selection to the grid rows and take top-N.

    The eff thresholds for ``best`` and ``fastest`` are tightened at
    this stage by ``events5_eff_bias_pp`` to compensate for the known
    events=5 → events=50 eff drop (events=5 overestimates by ~0.7 pp).
    Without this, the events=5 propose step lets through cells that
    pick_winners later rejects under strict events=50 rules.
    """
    eps         = float(rules["tolerance_pp"]) / 100.0
    eps_best    = float(rules.get("best_tolerance_pp", rules["tolerance_pp"])) / 100.0
    floor       = float(rules["fastest_efficiency_floor"])
    bias        = float(rules.get("events5_eff_bias_pp", 0.0)) / 100.0

    def _delta(r):
        return {
            "d_eff":  r["abs"]["eff"]  - base["eff"],
            "d_fake": r["abs"]["fake"] - base["fake"],
            "d_dup":  r["abs"]["dup"]  - base["dup"],
        }

    me = sorted(rows, key=lambda r: (-r["abs"]["eff"], r["abs"]["time"]))[:top_n]

    # best: strictly better at events=50 → events=5 Δeff must exceed the
    # strict threshold by the bias amount. With the committed defaults
    # (best_tolerance_pp=0, bias=0.7 pp) the events=5 cutoff is
    # Δeff ≥ +0.7 pp; cells need to beat Cyl by that margin at events=5
    # to be likely to still beat it at events=50.
    best_feasible = [r for r in rows
                     if (_delta(r)["d_eff"]  >= -eps_best + bias
                         and _delta(r)["d_fake"] <=  eps_best
                         and _delta(r)["d_dup"]  <=  eps_best)]
    best = sorted(best_feasible,
                  key=lambda r: (r["abs"]["time"], -r["abs"]["eff"]))[:top_n]

    # fastest: argmin time over eff ≥ floor only. No fake/dup
    # constraints — those are the "best" rule's job. The events=5
    # propose cutoff is floor + bias so cells likely to clear floor
    # at events=50 survive bias-correction.
    fast_feasible = [r for r in rows
                     if r["abs"]["eff"] >= floor + bias]
    fast = sorted(fast_feasible,
                  key=lambda r: (r["abs"]["time"], -r["abs"]["eff"]))[:top_n]

    return {"max_efficiency": me, "best": best, "fastest": fast}


def _parse_csv_value(v):
    """Reverse of run_grid._value_to_str: '[-1, 1]' → [-1, 1];
    '0.5' → 0.5; '5' → 5."""
    s = str(v).strip()
    if s.startswith("["):
        inner = s[1:-1]
        a, b = (x.strip() for x in inner.split(","))
        return [int(a), int(b)]
    if "." in s:
        return float(s)
    try:
        return int(s)
    except ValueError:
        return s


def _params_for_runner(row: dict, anchor: dict) -> dict:
    """Reconstruct the runner-ready cell dict from a grid row."""
    cell = dict(anchor)
    for k, v in row["params"].items():
        cell[k] = _parse_csv_value(v)
    return cell


def _serialize_candidate(row: dict) -> dict:
    """Plain-Python dict for the candidates.yaml entry."""
    out: dict = {}
    for k, v in row["params"].items():
        parsed = _parse_csv_value(v)
        if isinstance(parsed, list):
            out[k] = list(parsed)
        else:
            out[k] = parsed
    out["_grid_measured"] = {
        "eff":  float(row["abs"]["eff"]),
        "fake": float(row["abs"]["fake"]),
        "dup":  float(row["abs"]["dup"]),
        "time": float(row["abs"]["time"]),
    }
    out["_grid_cell_id"] = int(row["cell_id"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--top", type=int, default=5,
        help="Top-K candidates per rule (default 5 → up to 15 "
             "confirmation runs across the three categories).",
    )
    args = ap.parse_args()

    base   = load_baseline(BASELINE_DIR)
    rows, axis_keys = _read_grid_measurements()
    rules  = load_selection_rules()
    confirm = load_confirmation()
    events = int(confirm.get("events", 50))
    anchor = load_anchor()

    selected = _select_candidates(rows, base, rules, args.top)
    all_cands: list[dict] = []
    for rule in ("max_efficiency", "best", "fastest"):
        all_cands.extend(selected[rule])

    if not all_cands:
        raise RuntimeError(
            "No candidates feasible under any rule — relax the rule "
            "tolerances or extend the grid."
        )

    sweep_values = [render_overrides(_params_for_runner(r, anchor))
                    for r in all_cands]
    print(f"run_confirmation: {len(all_cands)} candidates × {events} events "
          f"(top {args.top}/rule)")

    CONFIRM_DIR.mkdir(parents=True, exist_ok=True)
    cands_yaml = {
        rule: [_serialize_candidate(r) for r in selected[rule]]
        for rule in ("max_efficiency", "best", "fastest")
    }
    (CONFIRM_DIR / "candidates.yaml").write_text(
        yaml.safe_dump(cands_yaml, sort_keys=False)
    )

    workflow = make_workflow()
    workflow.run(
        RunnerDir=[],
        PythonRunners=["oddData.py"],
        DataDir=DATA_DIR_REL,
        tempOutputDir="temp",
        PythonRunnerArgs=[
            "--version", "SphericalGridTriplet",
            "--events", str(events),
        ],
        Parsers=[
            ("TimerParser.py",   "ParamOptimizationTiming.csv",  0),
            ("MetricsParser.py", "ParamOptimizationMetrics.csv", 0),
        ],
        LogFileNames=["Confirmation.log"],
        Sweep={"--parameters": sweep_values},
        PrepareEnvironment=False,
    )

    grids = load_sweep_grids(CONFIRM_DIR, n_cells=len(all_cands))
    rows_out: dict = {"cell_id": list(range(1, len(all_cands) + 1))}
    for k in axis_keys:
        rows_out[k] = [str(r["params"][k]) for r in all_cands]
    rows_out["eff"]      = grids["eff"]
    rows_out["fake"]     = grids["fake"]
    rows_out["dup"]      = grids["dup"]
    rows_out["time_ms"]  = grids["time"]
    rows_out["n_events"] = [events] * len(all_cands)
    pd.DataFrame(rows_out).to_csv(CONFIRM_DIR / "results.csv", index=False)
    print(f"Wrote {CONFIRM_DIR / 'results.csv'} and candidates.yaml")


if __name__ == "__main__":
    main()
