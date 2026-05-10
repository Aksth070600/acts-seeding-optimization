import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

# Baseline only generates the S1 (Default / SeedingAlgorithm) timing+workload
# pair here. The S2 (GridTriplet) pair is generated upstream by
# data-gen/Methods/Workload.py and lives at raw-data/Methods/{Pixel,Strip}{Timing,Workload}.csv.
workflow = DataGenWorkflow()

workflow.run(
    RunnerDir=["Seeding/globalTiming"],
    PythonRunners=["PixelSeeding.py", "StripSeeding.py"],
    DataDir="Results/Baseline/Scaling",
    PythonRunnerArgs=["--version", "Default", "--logging-level", "2"],
    Parsers=[
        ("TimerParser.py", "PixelScalingTiming.csv", 0),
        ("TimerParser.py", "StripScalingTiming.csv", 1),
        ("WorkloadParser.py", "PixelScalingWorkload.csv", 0),
        ("WorkloadParser.py", "StripScalingWorkload.csv", 1),
    ],
    LogFileNames=[
        "PixelScalingSeeding",
        "StripScalingSeeding",
    ],
)
