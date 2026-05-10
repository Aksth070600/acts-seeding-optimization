import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline

p = Pipeline("Figures: Datasets")

p.requires("raw-data/Datasets", "raw-data/Datasets directory")

p.add("Characteristics table",  "figure-gen/Datasets/characteristics-table.py", output=["figures/Datasets/table_dataset_characteristics.tex"])
p.add("Event multiplicity plot", "figure-gen/Datasets/event-multiplicity.py",   output=["figures/Datasets/event_multiplicity.pdf"])
p.add("Track eta plot",          "figure-gen/Datasets/track-eta.py",            output=["figures/Datasets/track_eta.pdf"])
p.add("Track phi plot",          "figure-gen/Datasets/track-phi.py",            output=["figures/Datasets/track_phi.pdf"])
p.add("Track pT plot",           "figure-gen/Datasets/track-pt.py",             output=["figures/Datasets/track_pt.pdf"])
p.add("pT vs eta plot",          "figure-gen/Datasets/pt-eta.py",               output=["figures/Datasets/pT_vs_eta.pdf"])

if __name__ == "__main__":
    p.run()
