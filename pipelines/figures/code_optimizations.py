import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline

p = Pipeline("Figures: Results/CodeOptimizations")

METRICS_SCRIPT = "figure-gen/Results/CodeOptimizations/MetricsTable.py"

for level in ("O1", "O1-2", "O2", "O3", "O4"):
    d = f"figure-gen/Results/CodeOptimizations/{level}"
    p.add(f"{level}: Performance table", f"{d}/PerformanceTable.py",
          output=[f"figures/Results/CodeOptimizations/{level}PerformanceTable.tex"])
    p.add(f"{level}: Metrics table",     METRICS_SCRIPT,
          script_args=["--variant", level],
          output=[f"figures/Results/CodeOptimizations/{level}PhysicsTable.tex"])
    if level == "O4":
        p.add("O4: Heaptrack table", f"{d}/HeaptrackTable.py",
              output=["figures/Results/CodeOptimizations/O4HeaptrackTable.tex"])

if __name__ == "__main__":
    p.run()
