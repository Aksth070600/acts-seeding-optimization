import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, GNN4ITK_DATASET_PATH

p = Pipeline("Datasets")

p.requires(GNN4ITK_DATASET_PATH, "GNN4ITk dataset ROOT file")

p.add("Reading raw data", "data-gen/Datasets/read_dataset.py", output=[
    "raw-data/Datasets/TRKperigee_momentum.npy",
    "raw-data/Datasets/CLhardware.npy",
    "raw-data/Datasets/SPCL2_index.npy",
    "raw-data/Datasets/nPartEVT.npy",
    "raw-data/Datasets/nTRK.npy",
])
p.add("Generating table",              "figure-gen/Datasets/characteristics-table.py")
p.add("Plotting event multiplicities", "figure-gen/Datasets/event-multiplicity.py")
p.add("Plotting track eta",            "figure-gen/Datasets/track-eta.py")
p.add("Plotting track pT",             "figure-gen/Datasets/track-pt.py")
p.add("Plotting track phi",            "figure-gen/Datasets/track-phi.py")
p.add("Plotting pT vs eta",            "figure-gen/Datasets/pt-eta.py")

if __name__ == "__main__":
    p.run()
