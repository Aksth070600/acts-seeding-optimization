import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("Seeding3/_baseline")
workflow.copy_dir("Seeding3/Workload")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/Seeding3/Workload",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    Parsers=[
        ("StatsParser.py", "WorkloadSeeding3.csv", 0),
    ],
    LogFileNames=[
        "WorkloadSeeding3",
    ],
    PrepareEnvironment=False,
    Runs=1,
)

workflow.copy_required_dirs()
workflow.copy_dir("Seeding2/Workload")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/Seeding3/Workload",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("StatsParser.py", "WorkloadSeeding2.csv", 0),
    ],
    LogFileNames=[
        "WorkloadSeeding2",
    ],
    PrepareEnvironment=False,
    Runs=1,
)

