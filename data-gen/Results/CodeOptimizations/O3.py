import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

workflow.copy_required_dirs()
workflow.copy_dir("CodeOptimizations/O3/_baseline")
workflow.copy_dir("Seeding2/globalTiming")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=["oddData.py"],
    DataDir="Results/CodeOptimizations/O3/clean",
    PythonRunnerArgs=["--version", "GridTriplet"],
    Parsers=[
        ("MetricsParser.py", "Seeding2PhysicsMetrics.csv", 0),
    ],
    LogFileNames=[
        "Seeding2PhysicsMetrics",
    ],
    Runs=1,
    tempOutputDir="temps",
    PrepareEnvironment=False,
)

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/CodeOptimizations/O3/clean",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("TimerParser.py", "PixelSeedingGlobalTime.csv", 0),
        ("TimerParser.py", "StripSeedingGlobalTime.csv", 1),
    ],
    LogFileNames=[
        "PixelSeedingGlobalTime",
        "StripSeedingGlobalTime",
    ],
    PrepareEnvironment=False,
)

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/CodeOptimizations/O3/clean",
    PythonRunnerArgs=["--version", "GridTriplet", "--events", "3"],
    LogFileNames=[
        "PixelSeeding2Callgrind",
        "StripSeeding2Callgrind",
    ],
    Runs=1,
    Profiler="callgrind",
    ProfilerArgs=[
        "--collect-atstart=no",
        "--toggle-collect=*GridTripletSeedingAlgorithm::execute*",
    ],
    PrepareEnvironment=False,
)
