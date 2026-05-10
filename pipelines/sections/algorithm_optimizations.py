import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline, run_files

p = Pipeline("Results/AlgorithmOptimizations")

# Timing data feeds OptimizedConfigurationsTable's "Speedup vs.\ Cylindrical" row.
_TIMING = "raw-data/Results/AlgorithmOptimizations/Timing"
p.add("Generating Timing data", "data-gen/Results/AlgorithmOptimizations/Timing.py", output=[
    *run_files(_TIMING, "SphericalTiming",   ".csv"),
    *run_files(_TIMING, "CylindricalTiming", ".csv"),
])

p.add("Generating GridStats data", "data-gen/Results/AlgorithmOptimizations/GridStats.py", output=[
    "raw-data/Results/AlgorithmOptimizations/GridStats/SphericalGridStats.csv",
    "raw-data/Results/AlgorithmOptimizations/GridStats/CylindricalGridStats.csv",
])
p.add("Generating GridStats figure", "figure-gen/Results/AlgorithmOptimizations/GridStats.py")

p.add("Generating PhysicsValidation data", "data-gen/Results/AlgorithmOptimizations/PhysicsValidation.py", output=[
    "raw-data/Results/AlgorithmOptimizations/PhysicsValidation/ParamOptimizationMetrics.csv",
])
p.add("Generating ParameterOptimization Baseline",
      "data-gen/Results/AlgorithmOptimizations/ParameterOptimization/Baseline.py", output=[
    "raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Baseline/ParamOptimizationTiming.csv",
    "raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Baseline/ParamOptimizationMetrics.csv",
])
p.add("Generating PhysicsValidation figures", "figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsFigures.py")
p.add("Generating PhysicsValidation table",   "figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsTable.py")

_OPTCFG = "raw-data/Results/AlgorithmOptimizations/OptimizedConfigurations"
p.add("Generating OptimizedConfigurations data",
      "data-gen/Results/AlgorithmOptimizations/OptimizedConfigurations.py", output=[
    *run_files(f"{_OPTCFG}/MaxEfficiency", "Timing", ".csv"),
    f"{_OPTCFG}/MaxEfficiency/Metrics.csv",
    *run_files(f"{_OPTCFG}/Best", "Timing", ".csv"),
    f"{_OPTCFG}/Best/Metrics.csv",
    *run_files(f"{_OPTCFG}/Fastest", "Timing", ".csv"),
    f"{_OPTCFG}/Fastest/Metrics.csv",
])
p.add("Generating OptimizedConfigurations table",
      "figure-gen/Results/AlgorithmOptimizations/OptimizedConfigurationsTable.py")

p.add("Generating Callgrind/Heaptrack data (Spherical)",
      "data-gen/Results/AlgorithmOptimizations/CallgrindHeaptrack.py", output=[
    "raw-data/temp/Results/AlgorithmOptimizations/SphericalCallgrind.log",
    "raw-data/temp/Results/AlgorithmOptimizations/SphericalHeaptrack.log",
])

p.add("Generating Callgrind/Heaptrack data (Cylindrical baseline)",
      "data-gen/Results/AlgorithmOptimizations/CallgrindHeaptrackBaseline.py", output=[
    "raw-data/temp/Results/AlgorithmOptimizations/CylindricalCallgrind.log",
    "raw-data/temp/Results/AlgorithmOptimizations/CylindricalHeaptrack.log",
])
p.add("Generating Callgrind table",  "figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py")
p.add("Generating Heaptrack table", "figure-gen/Results/AlgorithmOptimizations/HeaptrackTables.py",
      output=["figures/Results/AlgorithmOptimizations/A1HeaptrackTable.tex"])

if __name__ == "__main__":
    p.run()
