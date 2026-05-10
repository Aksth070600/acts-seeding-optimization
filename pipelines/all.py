# Probes for the GNN4Itk dump and runs all pipelines if present, otherwise
# only the ODD-driven Spherical ones (the GNN4Itk-gated ones self-skip).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import GNN4ITK_DATASET_PATH
from sections import (
    datasets, methods, baseline, detailed,
    code_optimizations,
    seeding3, algorithm_optimizations, parameter_optimization,
)


have_gnn4itk = GNN4ITK_DATASET_PATH.exists()

print()
if have_gnn4itk:
    print(f"[all.py] GNN4Itk dump detected at {GNN4ITK_DATASET_PATH}")
    print("[all.py] Running GNN4Itk + open-data Spherical pipelines.")
    PIPELINES = [
        datasets.p,
        methods.p,
        baseline.p,
        detailed.p,
        code_optimizations.p,
        seeding3.p,
        algorithm_optimizations.p,
        parameter_optimization.p,
    ]
else:
    print(f"[all.py] GNN4Itk dump NOT found at {GNN4ITK_DATASET_PATH}")
    print("[all.py] Running open-data Spherical pipelines only.")
    PIPELINES = [
        seeding3.p,
        algorithm_optimizations.p,
        parameter_optimization.p,
    ]

if __name__ == "__main__":
    ok = True
    for pipeline in PIPELINES:
        if not pipeline.run():
            ok = False
            break
    sys.exit(0 if ok else 1)
