# Cyl baseline + 1D characterisation sweeps + per-axis figures.
# The deeper grid+confirmation pipeline at configs/parameter_optimization/
# is invoked manually (wall-clock heavy, not part of pipelines/all.py).
import sys
from pathlib import Path

import yaml

sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files


_BASE     = "raw-data/Results/AlgorithmOptimizations/ParameterOptimization"
_AXES_DIR = Path("configs/parameter_optimization/axes")


def _sweep_outputs(sweep_name: str, n_cells: int) -> list[str]:
    out: list[str] = []
    for stem in ("ParamOptimizationTiming", "ParamOptimizationMetrics"):
        out += run_files(f"{_BASE}/{sweep_name}", stem, ".csv", n_cells)
    return out


# Skip axes with an empty values list (uncharacterised placeholders).
_AXES: list[tuple[Path, str, int]] = []
for _yml in sorted(_AXES_DIR.glob("*.yaml")):
    with _yml.open() as _f:
        _spec = yaml.safe_load(_f) or {}
    _values = _spec.get("values") or []
    if _values:
        _AXES.append((_yml, _spec["parameter"], len(_values)))


p = Pipeline("Results/AlgorithmOptimizations/ParameterOptimization")

p.add(
    "Generating ParameterOptimization Cylindrical baseline data",
    "data-gen/Results/AlgorithmOptimizations/ParameterOptimization/Baseline.py",
    output=[
        f"{_BASE}/Baseline/ParamOptimizationTiming.csv",
        f"{_BASE}/Baseline/ParamOptimizationMetrics.csv",
    ],
)

for axis_yml, display_name, n_cells in _AXES:
    p.add(
        f"Generating ParameterOptimization {display_name} data",
        "configs/parameter_optimization/run_1d_sweep.py",
        script_args=["--axis", str(axis_yml)],
        output=_sweep_outputs(display_name, n_cells),
    )
    p.add(
        f"Generating {display_name} sweep figure",
        f"figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/{display_name}.py",
        output=[f"figures/Results/AlgorithmOptimizations/ParameterOptimization/{display_name}.pdf"],
    )


if __name__ == "__main__":
    p.run()
