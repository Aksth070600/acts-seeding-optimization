import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

DATA_BASE = "Results/AlgorithmOptimizations/OptimizedConfigurations"

CONFIGS = [
    ("MaxEfficiency", "parameter_optimization/winners/max_efficiency"),
    ("Best",          "parameter_optimization/winners/best"),
    ("Fastest",       "parameter_optimization/winners/fastest"),
]

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/globalTiming")
workflow.build_environment()

for label, config_name in CONFIGS:
    data_dir = f"{DATA_BASE}/{label}"

    workflow.run(
        RunnerDir=[],
        PythonRunners=["oddData.py"],
        DataDir=data_dir,
        PythonRunnerArgs=[
            "--version", "SphericalGridTriplet",
            *parameter_args(config_name),
        ],
        Parsers=[
            ("TimerParser.py", "Timing.csv", 0),
        ],
        LogFileNames=[f"{label}Timing.log"],
        PrepareEnvironment=False,
        tempOutputDir="temp",
    )

    workflow.run(
        RunnerDir=[],
        PythonRunners=["oddData.py"],
        DataDir=data_dir,
        PythonRunnerArgs=[
            "--version", "SphericalGridTriplet",
            "--output-dir", f"raw-data/{data_dir}",
            *parameter_args(config_name),
        ],
        Parsers=[
            ("MetricsParser.py", "Metrics.csv", 0),
        ],
        LogFileNames=[f"{label}Metrics.log"],
        PrepareEnvironment=False,
        Runs=1, 
    )
