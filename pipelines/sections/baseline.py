import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, GNN4ITK_DATASET_PATH, run_files

p = Pipeline("Results/Baseline")

p.requires(GNN4ITK_DATASET_PATH, "GNN4ITk dataset ROOT file")

_RCPU = "raw-data/Results/Baseline/RealCPUTime"
p.add("Generating RealCPUTime data", "data-gen/Results/Baseline/TimingTable.py", output=[
    *run_files(_RCPU, "PixelRealCPUTimeSeeding",  ".csv"),
    *run_files(_RCPU, "StripRealCPUTimeSeeding",  ".csv"),
    *run_files(_RCPU, "PixelRealCPUTimeSeeding2", ".csv"),
    *run_files(_RCPU, "StripRealCPUTimeSeeding2", ".csv"),
])
p.add("Generating figure", "figure-gen/Results/Baseline/RealCPUTime.py")

p.add("Generating Workload data", "data-gen/Results/Baseline/Workload.py", output=[
    "raw-data/Results/Baseline/Workload/PixelWorkloadSeeding.csv",
    "raw-data/Results/Baseline/Workload/StripWorkloadSeeding.csv",
    "raw-data/Results/Baseline/Workload/PixelWorkloadSeeding2.csv",
    "raw-data/Results/Baseline/Workload/StripWorkloadSeeding2.csv",
])
p.add("Generating workload figure", "figure-gen/Results/Baseline/Workload.py")

_STAGE_TIMING = "raw-data/Results/Baseline/StageTiming"
_STAGE_TIMING_OUTPUTS = [
    *run_files(_STAGE_TIMING, "PixelSeeding",  ".csv"),
    *run_files(_STAGE_TIMING, "PixelSeeding2", ".csv"),
    *run_files(_STAGE_TIMING, "StripSeeding",  ".csv"),
    *run_files(_STAGE_TIMING, "StripSeeding2", ".csv"),
]
p.add("Generating StageTiming data",
      "data-gen/Results/Baseline/StageTiming.py",
      output=_STAGE_TIMING_OUTPUTS)
p.add("Generating Waterfall figure",
      "figure-gen/Results/Baseline/Waterfall.py",
      requires=_STAGE_TIMING_OUTPUTS)

_SCALE = "raw-data/Results/Baseline/Scaling"
p.add(
    "Generating Scaling data",
    "data-gen/Results/Baseline/Scaling.py",
    output=[
        *run_files(_SCALE, "PixelScalingTiming",   ".csv"),
        *run_files(_SCALE, "PixelScalingWorkload", ".csv"),
        *run_files(_SCALE, "StripScalingTiming",   ".csv"),
        *run_files(_SCALE, "StripScalingWorkload", ".csv"),
    ],
)

# S2 timing+workload comes from Methods upstream.
_METHODS_S2 = [
    *run_files("raw-data/Methods", "PixelTiming",   ".csv"),
    *run_files("raw-data/Methods", "PixelWorkload", ".csv"),
    *run_files("raw-data/Methods", "StripTiming",   ".csv"),
    *run_files("raw-data/Methods", "StripWorkload", ".csv"),
]
p.add("Generating Scaling figures", "figure-gen/Results/Baseline/Scaling.py",
      requires=_METHODS_S2)

_GPERF = "raw-data/Results/Baseline/Gperftools"
_gperf_data = []
for stem in ("PixelSeeding", "PixelSeeding2", "StripSeeding", "StripSeeding2"):
    _gperf_data += run_files(_GPERF, stem, ".prof")
_gperf_figs = [
    "figures/Results/Baseline/Gperftools/Pixel_comparison.tex",
    "figures/Results/Baseline/Gperftools/Strip_comparison.tex",
    "figures/Results/Detailed/Gperftools/Hotspots/Annotations/Pixel_H1_createDoubletsImpl_annotation.txt",
    "figures/Results/Detailed/Gperftools/Hotspots/Annotations/Strip_H1_createDoubletsImpl_annotation.txt",
    "figures/Results/Detailed/Gperftools/Pixel_Seeding2_top20.tex",
    "figures/Results/Detailed/Gperftools/Strip_Seeding2_top20.tex",
    "figures/Results/Detailed/Gperftools/Pixel_Seeding2_flamegraph.svg",
    "figures/Results/Detailed/Gperftools/Strip_Seeding2_flamegraph.svg",
]
_gperf_all = _gperf_data + _gperf_figs

p.add("Generating Gperftools data",
      "data-gen/Results/Baseline/gperftools.py",
      output=_gperf_all)
p.add("Generating Gperftools figures (Baseline)",
      "figure-gen/Results/Baseline/Gperftools.py",
      output=_gperf_all)
p.add("Generating Gperftools hotspot annotations (Detailed)",
      "figure-gen/Results/Detailed/GperftoolsHotspots.py",
      output=_gperf_all)
p.add("Generating Gperftools top-20 + portrait flamegraphs (Detailed)",
      "figure-gen/Results/Detailed/Gperftools.py",
      output=_gperf_all)

if __name__ == "__main__":
    p.run()
