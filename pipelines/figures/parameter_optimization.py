import sys
from pathlib import Path

import yaml

sys.path.insert(0, "pipelines")
from pipeline import Pipeline


_AXES_DIR = Path("configs/parameter_optimization/axes")
OUT_DIR = "figures/Results/AlgorithmOptimizations/ParameterOptimization"


# Skip axes with an empty values list (uncharacterised placeholders).
_AXES: list[str] = []
for _yml in sorted(_AXES_DIR.glob("*.yaml")):
    with _yml.open() as _f:
        _spec = yaml.safe_load(_f) or {}
    if _spec.get("values"):
        _AXES.append(_spec["parameter"])


p = Pipeline("Figures: Results/AlgorithmOptimizations/ParameterOptimization")

for display_name in _AXES:
    p.add(
        f"{display_name} sweep figure",
        f"figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/{display_name}.py",
        output=[f"{OUT_DIR}/{display_name}.pdf"],
    )


if __name__ == "__main__":
    p.run()
