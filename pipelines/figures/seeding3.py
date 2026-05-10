import sys
sys.path.insert(0, "pipelines")
from pipeline import Pipeline

p = Pipeline("Figures: Results/Seeding3")

p.add("RealCPUTime table", "figure-gen/Results/Seeding3/RealCPUTime.py",
      output=["figures/Results/Seeding3/RealCPUTime/Seeding3PerformanceTable.tex"])
p.add("Workload table", "figure-gen/Results/Seeding3/Workload.py",
      output=["figures/Results/Seeding3/Workload/WorkloadTable.tex"])
p.add("Waterfall figure",                "figure-gen/Results/Seeding3/Waterfall.py")
p.add("Scaling figure",                  "figure-gen/Results/Seeding3/Scaling.py")

# pprof needs the live ACTS binary; always_run.
p.add("Gperftools figures (S1+S2)",      "figure-gen/Results/Seeding3/Gperftools.py",
      output=["figures/Results/Seeding3/Gperftools/Seeding_vs_Seeding2_comparison.tex"],
      always_run=True)
p.add("Gperftools figures (S3)",         "figure-gen/Results/Seeding3/Gperftools3.py",
      output=["figures/Results/Seeding3/Gperftools/Seeding2_vs_Seeding3_comparison.tex"],
      always_run=True)

if __name__ == "__main__":
    p.run()
