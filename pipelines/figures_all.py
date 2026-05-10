import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import ROOT_DIR
from figures import (
    datasets, methods, baseline, detailed,
    code_optimizations,
    seeding3, algorithm_optimizations, parameter_optimization,
)


CANDIDATES = [
    ("Datasets",               "raw-data/Datasets",                       datasets.p),
    ("Methods",                "raw-data/Methods",                        methods.p),
    ("Baseline",               "raw-data/Results/Baseline",               baseline.p),
    ("Detailed",               "raw-data/Results/Detailed",               detailed.p),
    ("CodeOptimizations",      "raw-data/Results/CodeOptimizations",      code_optimizations.p),
    ("Seeding3",               "raw-data/Results/Seeding3",               seeding3.p),
    ("AlgorithmOptimizations", "raw-data/Results/AlgorithmOptimizations", algorithm_optimizations.p),
    ("ParameterOptimization",  "raw-data/Results/AlgorithmOptimizations/ParameterOptimization",
                                                                          parameter_optimization.p),
]


def has_raw_data(rel_path: str) -> bool:
    full = ROOT_DIR / rel_path
    return full.is_dir() and any(full.iterdir())


if __name__ == "__main__":
    print()
    PIPELINES = []
    for label, sentinel, pipeline in CANDIDATES:
        if has_raw_data(sentinel):
            print(f"[figures_all.py] ✓ {label:<25s} raw-data present")
            PIPELINES.append(pipeline)
        else:
            print(f"[figures_all.py] ⏭ {label:<25s} no raw-data at {sentinel}")

    if not PIPELINES:
        print("\n[figures_all.py] No raw-data found for any section.")
        print("[figures_all.py] Run a data-gen pipeline first (e.g. pipelines/all.py).")
        sys.exit(1)

    ok = True
    for pipeline in PIPELINES:
        if not pipeline.run():
            ok = False
            break
    sys.exit(0 if ok else 1)
