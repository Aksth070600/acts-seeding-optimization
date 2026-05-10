import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Figures: Methods")

_METHODS = "raw-data/Methods"
_WARMUP_INPUTS = [
    *run_files(_METHODS, "PixelTiming",   ".csv"),
    *run_files(_METHODS, "StripTiming",   ".csv"),
    *run_files(_METHODS, "PixelWorkload", ".csv"),
    *run_files(_METHODS, "StripWorkload", ".csv"),
]

p.add("WarmUp/Workload running-mean plot", "figure-gen/Methods/WarmUpWorkload.py",
      requires=_WARMUP_INPUTS,
      output=["figures/Methods/WarmUp_RunningMean.pdf"])

if __name__ == "__main__":
    p.run()
