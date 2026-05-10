import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Results/Seeding3")

_RCPU3 = "raw-data/Results/Seeding3/RealCPUTime"
p.add("Generating RealCPUTime data", "data-gen/Results/Seeding3/TimingTable.py", output=[
    *run_files(_RCPU3, "RealCPUTimeSeeding",  ".csv"),
    *run_files(_RCPU3, "RealCPUTimeSeeding2", ".csv"),
    *run_files(_RCPU3, "RealCPUTimeSeeding3", ".csv"),
])
p.add("Generating RealCPUTime figure", "figure-gen/Results/Seeding3/RealCPUTime.py")

p.add("Generating Workload data", "data-gen/Results/Seeding3/Workload.py", output=[
    "raw-data/Results/Seeding3/Workload/WorkloadSeeding.csv",
    "raw-data/Results/Seeding3/Workload/WorkloadSeeding2.csv",
    "raw-data/Results/Seeding3/Workload/WorkloadSeeding3.csv",
])
p.add("Generating Workload figure", "figure-gen/Results/Seeding3/Workload.py")

p.add("Generating Waterfall data", "data-gen/Results/Seeding3/Waterfall.py", output=[
    "raw-data/Results/Seeding3/Waterfall/WaterfallSeeding.csv",
    "raw-data/Results/Seeding3/Waterfall/WaterfallSeeding2.csv",
    "raw-data/Results/Seeding3/Waterfall/WaterfallSeeding3.csv",
])
p.add("Generating Waterfall figure", "figure-gen/Results/Seeding3/Waterfall.py")

_SCALE3 = "raw-data/Results/Seeding3/Scaling"
p.add("Generating Scaling data", "data-gen/Results/Seeding3/Scaling.py", output=[
    *run_files(_SCALE3, "SeedingTiming",    ".csv"),
    *run_files(_SCALE3, "SeedingWorkload",  ".csv"),
    *run_files(_SCALE3, "Seeding2Timing",   ".csv"),
    *run_files(_SCALE3, "Seeding2Workload", ".csv"),
    *run_files(_SCALE3, "Seeding3Timing",   ".csv"),
    *run_files(_SCALE3, "Seeding3Workload", ".csv"),
])
p.add("Generating Scaling figure", "figure-gen/Results/Seeding3/Scaling.py")

_GPERF3     = "raw-data/Results/Seeding3/Gperftools"
_GPERF3_FIG = "figures/Results/Seeding3/Gperftools"

p.add("Generating Gperftools data + reports (S1+S2)",
      "data-gen/Results/Seeding3/gperftools.py", output=[
    *run_files(_GPERF3, "GperftoolsSeeding",  ".prof"),
    *run_files(_GPERF3, "GperftoolsSeeding2", ".prof"),
    f"{_GPERF3}/Seeding_report.txt",
    f"{_GPERF3}/Seeding2_report.txt",
    f"{_GPERF3_FIG}/Seeding_flamegraph.svg",
    f"{_GPERF3_FIG}/Seeding2_flamegraph.svg",
    f"{_GPERF3_FIG}/Seeding_callgraph.pdf",
    f"{_GPERF3_FIG}/Seeding2_callgraph.pdf",
])
p.add("Generating Gperftools comparison table (S1+S2)",
      "figure-gen/Results/Seeding3/Gperftools.py",
      output=[f"{_GPERF3_FIG}/Seeding_vs_Seeding2_comparison.tex"])

p.add("Generating Gperftools data + reports (S3)",
      "data-gen/Results/Seeding3/gperftoolsSeeding3.py", output=[
    *run_files(_GPERF3, "GperftoolsSeeding3", ".prof"),
    f"{_GPERF3}/Seeding3_report.txt",
    f"{_GPERF3_FIG}/Seeding3_flamegraph.svg",
    f"{_GPERF3_FIG}/Seeding3_callgraph.pdf",
])
p.add("Generating Gperftools comparison table (S3)",
      "figure-gen/Results/Seeding3/Gperftools3.py",
      output=[f"{_GPERF3_FIG}/Seeding2_vs_Seeding3_comparison.tex"])

if __name__ == "__main__":
    p.run()
