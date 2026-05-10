"""Stage 1 of the parameter-optimisation pipeline: 1D characterisation
sweep over a single parameter.

Reads
  configs/parameter_optimization/anchor.yaml   — shared default config
  configs/parameter_optimization/axes/<P>.yaml — sweep axis spec

Writes
  raw-data/Results/AlgorithmOptimizations/ParameterOptimization/<P>/
    ParamOptimizationTiming_run<i>.csv   (per-cell, canonical)
    ParamOptimizationMetrics_run<i>.csv  (per-cell, canonical)
    results.csv                          (derived summary; schema:
                                          value, eff, fake, dup,
                                          time_ms, time_norm, n_events)

Usage::

    python3 configs/parameter_optimization/run_1d_sweep.py \\
        --axis configs/parameter_optimization/axes/DeltaEtaMax.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    AXIS_NAMES, REPO,
    load_anchor, load_axis, make_workflow, render_overrides,
)

sys.path.append(str(REPO / "figure-gen"))
from parameter_scan_plotter import load_sweep_grids  # noqa: E402


DATA_BASE_REL = "Results/AlgorithmOptimizations/ParameterOptimization"


def _build_sweep_values(anchor: dict, axis_key: str, values: list) -> list[str]:
    """One ``--parameters`` string per swept value. Non-axis parameters
    held at their anchor values."""
    out: list[str] = []
    for v in values:
        cell = dict(anchor)
        cell[axis_key] = v
        out.append(render_overrides(cell))
    return out


def _value_to_str(v) -> str:
    """Display form for the results.csv ``value`` column. Lists/tuples
    serialize as ``[lo, hi]`` so the column survives a round-trip
    through pandas."""
    if isinstance(v, (list, tuple)):
        return f"[{v[0]}, {v[1]}]"
    return str(v)


def _write_results_csv(out_dir: Path, values: list, events: int) -> None:
    """Aggregate the per-cell CSV pair into a single summary."""
    grids = load_sweep_grids(out_dir, n_cells=len(values))
    time = grids["time"]
    time_norm = (time / time.max()) if time.max() > 0 else time
    df = pd.DataFrame({
        "value":     [_value_to_str(v) for v in values],
        "eff":       grids["eff"],
        "fake":      grids["fake"],
        "dup":       grids["dup"],
        "time_ms":   time,
        "time_norm": time_norm,
        "n_events":  [events] * len(values),
    })
    df.to_csv(out_dir / "results.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--axis", required=True, type=Path,
        help="Path to an axes/<P>.yaml file.",
    )
    args = ap.parse_args()

    spec = load_axis(args.axis)
    display_name = spec.get("parameter")
    if display_name not in AXIS_NAMES:
        raise ValueError(
            f"{args.axis}: unknown 'parameter' field {display_name!r}. "
            f"Expected one of {sorted(AXIS_NAMES)}."
        )
    axis_key = AXIS_NAMES[display_name]
    values = spec.get("values") or []
    events = int(spec.get("events", 5))

    if not values:
        raise ValueError(
            f"{args.axis}: 'values' list is empty (TODO placeholder). "
            "Define a sweep range before invoking run_1d_sweep."
        )

    anchor = load_anchor()
    sweep_values = _build_sweep_values(anchor, axis_key, values)
    data_dir_rel = f"{DATA_BASE_REL}/{display_name}"

    print(f"run_1d_sweep: {display_name} × {len(values)} cells × "
          f"{events} events")

    workflow = make_workflow()
    workflow.run(
        RunnerDir=[],
        PythonRunners=["oddData.py"],
        DataDir=data_dir_rel,
        tempOutputDir="temp",
        PythonRunnerArgs=[
            "--version", "SphericalGridTriplet",
            "--events", str(events),
        ],
        Parsers=[
            ("TimerParser.py",   "ParamOptimizationTiming.csv",  0),
            ("MetricsParser.py", "ParamOptimizationMetrics.csv", 0),
        ],
        LogFileNames=[f"{display_name}.log"],
        Sweep={"--parameters": sweep_values},
        PrepareEnvironment=False,
    )

    out_dir = REPO / "raw-data" / data_dir_rel
    _write_results_csv(out_dir, values, events)
    print(f"Wrote {out_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
