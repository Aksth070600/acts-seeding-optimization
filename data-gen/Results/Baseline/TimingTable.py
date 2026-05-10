import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

result = workflow.run(
    RunnerDir=[
        "Seeding/globalTiming",
    ],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/Baseline/RealCPUTime",
    PythonRunnerArgs=[
        "--version",
        "Default",
    ],
    Parsers=[
        ("TimerParser.py", "PixelRealCPUTimeSeeding.csv", 0),
        ("TimerParser.py", "StripRealCPUTimeSeeding.csv", 1),
    ],
    LogFileNames=[
        "PixelRealCPUTimeSeeding",
        "StripRealCPUTimeSeeding",
    ],
)

result = workflow.run(
    RunnerDir=[
        "Seeding2/globalTiming",
    ],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/Baseline/RealCPUTime",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("TimerParser.py", "PixelRealCPUTimeSeeding2.csv", 0),
        ("TimerParser.py", "StripRealCPUTimeSeeding2.csv", 1),
    ],
    LogFileNames=[
        "PixelRealCPUTimeSeeding2",
        "StripRealCPUTimeSeeding2",
    ],
)
