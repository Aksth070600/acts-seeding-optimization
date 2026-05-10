import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Results/CodeOptimizations")

def _common_globaltime(variant_dir):
    base = f"raw-data/Results/CodeOptimizations/{variant_dir}"
    return [*run_files(base, "PixelSeedingGlobalTime", ".csv"),
            *run_files(base, "StripSeedingGlobalTime", ".csv")]

def _localtime(variant_dir, idx):
    base = f"raw-data/Results/CodeOptimizations/{variant_dir}"
    return [*run_files(base, f"PixelSeedingLocalTime{idx}", ".csv"),
            *run_files(base, f"StripSeedingLocalTime{idx}", ".csv")]

def _callgrind_logs(variant_dir):
    base = f"raw-data/temp/Results/CodeOptimizations/{variant_dir}"
    return [f"{base}/PixelSeeding2Callgrind.log", f"{base}/StripSeeding2Callgrind.log"]

def _heaptrack_logs(variant_dir):
    base = f"raw-data/temp/Results/CodeOptimizations/{variant_dir}"
    return [f"{base}/PixelSeeding2Heaptrack.log", f"{base}/StripSeeding2Heaptrack.log"]


METRICS_SCRIPT = "figure-gen/Results/CodeOptimizations/MetricsTable.py"

p.add("Generating data for CodeOptimizations/clean", "data-gen/Results/CodeOptimizations/clean.py", output=[
    "raw-data/Results/CodeOptimizations/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("clean"),
    *_localtime("clean", 1),
    *_localtime("clean", 2),
    *_callgrind_logs("clean"),
    *_heaptrack_logs("clean"),
])

p.add("Generating data for CodeOptimizations/O1", "data-gen/Results/CodeOptimizations/O1.py", output=[
    "raw-data/Results/CodeOptimizations/O1/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("O1/clean"),
    *_localtime("O1/clean", 1),
    *_localtime("O1/clean", 2),
    *_callgrind_logs("O1/clean"),
])
p.add("Generating CodeOptimizations/O1 figures",
      "figure-gen/Results/CodeOptimizations/O1/PerformanceTable.py")
p.add("Generating CodeOptimizations/O1 metrics table",
      METRICS_SCRIPT, script_args=["--variant", "O1"],
      output=["figures/Results/CodeOptimizations/O1PhysicsTable.tex"])

p.add("Generating data for CodeOptimizations/O1-2", "data-gen/Results/CodeOptimizations/O1-2.py", output=[
    "raw-data/Results/CodeOptimizations/O1-2/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("O1-2/clean"),
    *_localtime("O1-2/clean", 1),
    *_localtime("O1-2/clean", 2),
    *_callgrind_logs("O1-2/clean"),
])
p.add("Generating CodeOptimizations/O1-2 figures",
      "figure-gen/Results/CodeOptimizations/O1-2/PerformanceTable.py")
p.add("Generating CodeOptimizations/O1-2 metrics table",
      METRICS_SCRIPT, script_args=["--variant", "O1-2"],
      output=["figures/Results/CodeOptimizations/O1-2PhysicsTable.tex"])

p.add("Generating data for CodeOptimizations/O2", "data-gen/Results/CodeOptimizations/O2.py", output=[
    "raw-data/Results/CodeOptimizations/O2/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("O2/clean"),
    *_localtime("O2/clean", 1),
    *_callgrind_logs("O2/clean"),
])
p.add("Generating CodeOptimizations/O2 figures",
      "figure-gen/Results/CodeOptimizations/O2/PerformanceTable.py")
p.add("Generating CodeOptimizations/O2 metrics table",
      METRICS_SCRIPT, script_args=["--variant", "O2"],
      output=["figures/Results/CodeOptimizations/O2PhysicsTable.tex"])

p.add("Generating data for CodeOptimizations/O3", "data-gen/Results/CodeOptimizations/O3.py", output=[
    "raw-data/Results/CodeOptimizations/O3/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("O3/clean"),
    *_callgrind_logs("O3/clean"),
])
p.add("Generating CodeOptimizations/O3 figures",
      "figure-gen/Results/CodeOptimizations/O3/PerformanceTable.py")
p.add("Generating CodeOptimizations/O3 metrics table",
      METRICS_SCRIPT, script_args=["--variant", "O3"],
      output=["figures/Results/CodeOptimizations/O3PhysicsTable.tex"])

p.add("Generating data for CodeOptimizations/O4", "data-gen/Results/CodeOptimizations/O4.py", output=[
    "raw-data/Results/CodeOptimizations/O4/clean/Seeding2PhysicsMetrics.csv",
    *_common_globaltime("O4/clean"),
    *_localtime("O4/clean", 1),
    *_callgrind_logs("O4/clean"),
    *_heaptrack_logs("O4/clean"),
])
p.add("Generating CodeOptimizations/O4 figures",
      "figure-gen/Results/CodeOptimizations/O4/PerformanceTable.py")
p.add("Generating CodeOptimizations/O4 metrics table",
      METRICS_SCRIPT, script_args=["--variant", "O4"],
      output=["figures/Results/CodeOptimizations/O4PhysicsTable.tex"])
p.add("Generating CodeOptimizations/O4 heaptrack table",
      "figure-gen/Results/CodeOptimizations/O4/HeaptrackTable.py",
      output=["figures/Results/CodeOptimizations/O4HeaptrackTable.tex"])

if __name__ == "__main__":
    p.run()
