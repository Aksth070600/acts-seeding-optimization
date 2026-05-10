import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline

p = Pipeline("Figures: Heaptrack tables")

p.add("AlgorithmOptimizations heaptrack table",
      "figure-gen/Results/AlgorithmOptimizations/HeaptrackTables.py")
p.add("CodeOptimizations O4 heaptrack table",
      "figure-gen/Results/CodeOptimizations/O4/HeaptrackTable.py")

if __name__ == "__main__":
    p.run()
