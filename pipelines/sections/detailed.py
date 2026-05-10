import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, GNN4ITK_DATASET_PATH, run_files

p = Pipeline("Results/Detailed")

p.requires(GNN4ITK_DATASET_PATH, "GNN4ITk dataset ROOT file")

# StageTiming data is owned by Baseline; this pipeline only renders.
_STAGE = "raw-data/Results/Baseline/StageTiming"
_STAGE_TIMING_INPUTS = [
    *run_files(_STAGE, "PixelSeeding",  ".csv"),
    *run_files(_STAGE, "StripSeeding",  ".csv"),
    *run_files(_STAGE, "PixelSeeding2", ".csv"),
    *run_files(_STAGE, "StripSeeding2", ".csv"),
]
p.add("Generating StageTiming figure", "figure-gen/Results/Detailed/StageTiming.py",
      requires=_STAGE_TIMING_INPUTS)

if __name__ == "__main__":
    p.run()
