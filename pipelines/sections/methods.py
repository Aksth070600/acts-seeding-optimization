import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, GNN4ITK_DATASET_PATH

p = Pipeline("Methods")

# Methods owns its own timing+workload data so it doesn't depend on Baseline.
p.add("Generating Workload data", "data-gen/Methods/Workload.py",
      requires=GNN4ITK_DATASET_PATH,
      output=[
    "raw-data/Methods/PixelTiming.csv",
    "raw-data/Methods/StripTiming.csv",
    "raw-data/Methods/PixelWorkload.csv",
    "raw-data/Methods/StripWorkload.csv",
])

p.add("Generating WarmUp/Workload figure",
      "figure-gen/Methods/WarmUpWorkload.py",
      requires=GNN4ITK_DATASET_PATH)

if __name__ == "__main__":
    p.run()
