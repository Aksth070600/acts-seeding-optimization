import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("Seeding3/_baseline")
workflow.copy_dir("Seeding3/Scaling")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/Seeding3/Scaling",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        "--logging-level",
        "2",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    Parsers=[
        ("TimerParser.py", "Seeding3Timing.csv", 0),
        ("WorkloadParser.py", "Seeding3Workload.csv", 0),
    ],
    LogFileNames=[
        "Seeding3Scaling",
    ],
    PrepareEnvironment=False,
)

workflow.copy_required_dirs()
workflow.copy_dir("Seeding2/globalTiming")
workflow.copy_dir("Seeding/globalTiming")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/Seeding3/Scaling",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
        "--logging-level",
        "2",
    ],
    Parsers=[
        ("TimerParser.py", "Seeding2Timing.csv", 0),
        ("WorkloadParser.py", "Seeding2Workload.csv", 0),
    ],
    LogFileNames=[
        "Seeding2Scaling",
    ],
    PrepareEnvironment=False,
)

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/Seeding3/Scaling",
    PythonRunnerArgs=[
        "--version",
        "Default",
        "--logging-level",
        "2",
    ],
    Parsers=[
        ("TimerParser.py", "SeedingTiming.csv", 0),
        ("WorkloadParser.py", "SeedingWorkload.csv", 0),
    ],
    LogFileNames=[
        "SeedingScaling",
    ],
    PrepareEnvironment=False,
)
