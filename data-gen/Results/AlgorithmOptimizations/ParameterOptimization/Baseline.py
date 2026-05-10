# Cylindrical-grid baseline run; every Δ-vs-Cyl number in the picker
# comes from this CSV pair.
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[3]))
from workflow import DataGenWorkflow  # noqa: E402

workflow = DataGenWorkflow()

workflow.copy_required_dirs()
workflow.copy_dir("Seeding2/globalTiming")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=["oddData.py"],
    DataDir="Results/AlgorithmOptimizations/ParameterOptimization/Baseline",
    PythonRunnerArgs=[
        "--version", "GridTriplet",
        "--output-dir", "raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Baseline",
    ],
    Parsers=[
        ("TimerParser.py",   "ParamOptimizationTiming.csv",  0),
        ("MetricsParser.py", "ParamOptimizationMetrics.csv", 0),
    ],
    LogFileNames=["Baseline.log"],
    PrepareEnvironment=False,
    Runs=1,
)
