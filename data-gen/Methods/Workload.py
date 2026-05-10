import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

result = workflow.run(
    RunnerDir=[
        "Seeding2/globalTiming",
    ],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Methods",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
        "--logging-level",
        "2",
    ],
    Parsers=[
        ("TimerParser.py",    "PixelTiming.csv",   0),
        ("TimerParser.py",    "StripTiming.csv",   1),
        ("WorkloadParser.py", "PixelWorkload.csv", 0),
        ("WorkloadParser.py", "StripWorkload.csv", 1),
    ],
    LogFileNames=[
        "PixelWorkload",
        "StripWorkload",
    ],
    Runs=1,
)
