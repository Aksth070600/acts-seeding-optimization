import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

workflow.run(
    RunnerDir=["clean"],
    PythonRunners=["PixelSeeding.py", "StripSeeding.py"],
    DataDir="Results/Baseline/Gperftools",
    PythonRunnerArgs=["--version", "Default"],
    LogFileNames=[
        "PixelSeeding",
        "StripSeeding",
    ],
    Profiler="gperftools",
)

workflow.run(
    RunnerDir=["clean"],
    PythonRunners=["PixelSeeding.py", "StripSeeding.py"],
    DataDir="Results/Baseline/Gperftools",
    PythonRunnerArgs=["--version", "GridTriplet"],
    LogFileNames=[
        "PixelSeeding2",
        "StripSeeding2",
    ],
    Profiler="gperftools",
)
