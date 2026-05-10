#!/usr/bin/env python3

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "data-gen"))
sys.path.insert(0, str(REPO / "figure-gen"))

from workflow import load_config                     
from parameter_scan_plotter import ( 
    load_baseline, load_sweep_grids, plot_parameter_scan,
)

DATA_DIR = REPO / "raw-data" / "Results" / "AlgorithmOptimizations" / "ParameterOptimization" / "MaxSeedsPerSpM"
BASE_DIR = REPO / "raw-data" / "Results" / "AlgorithmOptimizations" / "ParameterOptimization" / "Baseline"
OUTPUT   = REPO / "figures" / "Results" / "AlgorithmOptimizations" / "ParameterOptimization" / "MaxSeedsPerSpM.pdf"

VALUES = load_config("parameter_optimization")["sweeps_1d"]["maxSeedsPerSpM"]


def main() -> None:
    grids = load_sweep_grids(DATA_DIR, n_cells=len(VALUES))
    base  = load_baseline(BASE_DIR)
    plot_parameter_scan(
        parameter_values = VALUES,
        eff   = grids["eff"],
        fake  = grids["fake"],
        dup   = grids["dup"],
        time_ms = grids["time"],
        parameter_label = "maxSeedsPerSpM",
        title = "Seed-finding performance vs. max seeds per middle space-point",
        output_path = OUTPUT,
        baseline = base,
        anchor_x = 5,
    )
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
