import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Figures: Results/Detailed")

# StageTiming CSVs live under Baseline (it owns the data-gen step).
_STAGE = "raw-data/Results/Baseline/StageTiming"
_STAGE_TIMING_INPUTS = [
    *run_files(_STAGE, "PixelSeeding",  ".csv"),
    *run_files(_STAGE, "StripSeeding",  ".csv"),
    *run_files(_STAGE, "PixelSeeding2", ".csv"),
    *run_files(_STAGE, "StripSeeding2", ".csv"),
]
p.add("StageTiming table", "figure-gen/Results/Detailed/StageTiming.py",
      requires=_STAGE_TIMING_INPUTS,
      output=["figures/Results/Detailed/StageTiming/timing_table.tex"])

# GperftoolsHotspots is registered in pipelines/sections/baseline.py
# (must run immediately after the matching ACTS build).

if __name__ == "__main__":
    p.run()
