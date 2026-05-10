import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

workflow.run(
    RunnerDir=["Seeding/StageTiming"],
    PythonRunners=["PixelSeeding.py", "StripSeeding.py"],
    DataDir="Results/Baseline/StageTiming",
    PythonRunnerArgs=["--version", "Default"],
    Parsers=[
        ("TimerParser.py", "PixelSeeding.csv", 0),
        ("TimerParser.py", "StripSeeding.csv", 1),
    ],
    LogFileNames=["PixelSeeding", "StripSeeding"],
)

workflow.run(
    RunnerDir=["Seeding2/StageTiming"],
    PythonRunners=["PixelSeeding.py", "StripSeeding.py"],
    DataDir="Results/Baseline/StageTiming",
    PythonRunnerArgs=["--version", "GridTriplet"],
    Parsers=[
        ("TimerParser.py", "PixelSeeding2.csv", 0),
        ("TimerParser.py", "StripSeeding2.csv", 1),
    ],
    LogFileNames=["PixelSeeding2", "StripSeeding2"],
)
