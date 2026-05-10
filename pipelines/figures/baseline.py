import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Figures: Results/Baseline")

p.add("RealCPUTime table", "figure-gen/Results/Baseline/RealCPUTime.py",
      output=["figures/Results/Baseline/RealCPUTime/BaselinePerformanceTable.tex"])

p.add("Workload table", "figure-gen/Results/Baseline/Workload.py",
      output=["figures/Results/Baseline/Workload/WorkloadTable.tex"])

_STAGE_TIMING = "raw-data/Results/Baseline/StageTiming"
_WATERFALL_INPUTS = [
    *run_files(_STAGE_TIMING, "PixelSeeding",  ".csv"),
    *run_files(_STAGE_TIMING, "PixelSeeding2", ".csv"),
    *run_files(_STAGE_TIMING, "StripSeeding",  ".csv"),
    *run_files(_STAGE_TIMING, "StripSeeding2", ".csv"),
]
p.add("Waterfall figure", "figure-gen/Results/Baseline/Waterfall.py",
      requires=_WATERFALL_INPUTS)

# S2 timing+workload comes from Methods upstream.
_METHODS_S2 = [
    *run_files("raw-data/Methods", "PixelTiming",   ".csv"),
    *run_files("raw-data/Methods", "PixelWorkload", ".csv"),
    *run_files("raw-data/Methods", "StripTiming",   ".csv"),
    *run_files("raw-data/Methods", "StripWorkload", ".csv"),
]
p.add("Scaling figures",  "figure-gen/Results/Baseline/Scaling.py",
      requires=_METHODS_S2)

# pprof needs the live ACTS binary; always_run.
p.add("Gperftools figures (Baseline)", "figure-gen/Results/Baseline/Gperftools.py",
      output=[
          "figures/Results/Baseline/Gperftools/Pixel_comparison.tex",
          "figures/Results/Baseline/Gperftools/Strip_comparison.tex",
      ],
      always_run=True)
p.add("Gperftools hotspot annotations (Detailed)",
      "figure-gen/Results/Detailed/GperftoolsHotspots.py",
      output=[
          "figures/Results/Detailed/Gperftools/Hotspots/Annotations/Pixel_H1_createDoubletsImpl_annotation.txt",
          "figures/Results/Detailed/Gperftools/Hotspots/Annotations/Strip_H1_createDoubletsImpl_annotation.txt",
      ],
      always_run=True)
p.add("Gperftools top-20 + portrait flamegraphs (Detailed)",
      "figure-gen/Results/Detailed/Gperftools.py",
      output=[
          "figures/Results/Detailed/Gperftools/Pixel_Seeding2_top20.tex",
          "figures/Results/Detailed/Gperftools/Strip_Seeding2_top20.tex",
          "figures/Results/Detailed/Gperftools/Pixel_Seeding2_flamegraph.svg",
          "figures/Results/Detailed/Gperftools/Strip_Seeding2_flamegraph.svg",
      ],
      always_run=True)

if __name__ == "__main__":
    p.run()
