import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

result = workflow.run(
    RunnerDir=[
        "Seeding/Workload",
    ],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/Baseline/Workload",
    PythonRunnerArgs=[
        "--version",
        "Default",
    ],
    Parsers=[
        ("StatsParser.py", "PixelWorkloadSeeding.csv", 0),
        ("StatsParser.py", "StripWorkloadSeeding.csv", 1),
    ],
    LogFileNames=[
        "PixelWorkloadSeeding",
        "StripWorkloadSeeding",
    ],
    Runs=1,
)

result = workflow.run(
    RunnerDir=[
        "Seeding2/Workload",
    ],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/Baseline/Workload",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("StatsParser.py", "PixelWorkloadSeeding2.csv", 0),
        ("StatsParser.py", "StripWorkloadSeeding2.csv", 1),
    ],
    LogFileNames=[
        "PixelWorkloadSeeding2",
        "StripWorkloadSeeding2",
    ],
    Runs=1,
)
