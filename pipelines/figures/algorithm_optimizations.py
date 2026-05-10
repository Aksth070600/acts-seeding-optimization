import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline

p = Pipeline("Figures: Results/AlgorithmOptimizations")

p.add("GridStats table",           "figure-gen/Results/AlgorithmOptimizations/GridStats.py")
p.add("Callgrind tables",          "figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py")
p.add("Heaptrack table",           "figure-gen/Results/AlgorithmOptimizations/HeaptrackTables.py",
      output=["figures/Results/AlgorithmOptimizations/A1HeaptrackTable.tex"])
p.add("PhysicsValidation figures", "figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsFigures.py")
p.add("PhysicsValidation table",   "figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsTable.py")
p.add("OptimizedConfigurations table",
      "figure-gen/Results/AlgorithmOptimizations/OptimizedConfigurationsTable.py",
      output=["figures/Results/AlgorithmOptimizations/OptimizedConfigurationsTable.tex"])

if __name__ == "__main__":
    p.run()
