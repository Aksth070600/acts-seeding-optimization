"""Stage 3 of the parameter-optimisation pipeline: joint grid search.

Reads
  configs/parameter_optimization/grid.yaml   — joint-search intervals
  configs/parameter_optimization/anchor.yaml — defaults for non-axis params

Writes
  raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Grid/
    ParamOptimizationTiming_run<i>.csv   (per-cell, canonical)
    ParamOptimizationMetrics_run<i>.csv  (per-cell, canonical)
    results.csv                          (derived summary; schema:
                                          cell_id, <one column per
                                          swept axis>, eff, fake, dup,
                                          time_ms, n_events)

The ``run_confirmation.py`` step reads ``results.csv``.

Usage::

    python3 configs/parameter_optimization/run_grid.py
"""
from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    REPO,
    load_anchor, load_grid, make_workflow, render_overrides,
)

sys.path.append(str(REPO / "figure-gen"))
from parameter_scan_plotter import load_sweep_grids  # noqa: E402


DATA_DIR_REL = "Results/AlgorithmOptimizations/ParameterOptimization/Grid"

# Top-level grid.yaml keys that are metadata, not axes.
META_KEYS = {"events", "notes"}


def _enumerate_cells(grid: dict, anchor: dict) -> tuple[list[dict], list[str]]:
    """Cartesian product of the grid axes; non-grid params held at
    their anchor values. Returns (cells, ordered axis-key list)."""
    grid_keys = [k for k in grid.keys() if k not in META_KEYS]
    value_lists = [grid[k] for k in grid_keys]
    cells: list[dict] = []
    for combo in product(*value_lists):
        cell = dict(anchor)
        cell.update(dict(zip(grid_keys, combo)))
        cells.append(cell)
    return cells, grid_keys


def _value_to_str(v) -> str:
    if isinstance(v, (list, tuple)):
        return f"[{v[0]}, {v[1]}]"
    return str(v)


def _write_results_csv(out_dir: Path, cells: list[dict], grid_keys: list[str],
                       events: int) -> None:
    grids = load_sweep_grids(out_dir, n_cells=len(cells))
    rows: dict = {"cell_id": list(range(1, len(cells) + 1))}
    for k in grid_keys:
        rows[k] = [_value_to_str(c[k]) for c in cells]
    rows["eff"]      = grids["eff"]
    rows["fake"]     = grids["fake"]
    rows["dup"]      = grids["dup"]
    rows["time_ms"]  = grids["time"]
    rows["n_events"] = [events] * len(cells)
    pd.DataFrame(rows).to_csv(out_dir / "results.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.parse_args()

    grid   = load_grid()
    anchor = load_anchor()
    events = int(grid.get("events", 5))

    cells, grid_keys = _enumerate_cells(grid, anchor)
    sweep_values = [render_overrides(c) for c in cells]

    print(f"run_grid: {len(cells)} cells × {events} events  "
          f"(axes: {', '.join(grid_keys)})")

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
        LogFileNames=["Grid.log"],
        Sweep={"--parameters": sweep_values},
        PrepareEnvironment=False,
    )

    out_dir = REPO / "raw-data" / DATA_DIR_REL
    _write_results_csv(out_dir, cells, grid_keys, events)
    print(f"Wrote {out_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
