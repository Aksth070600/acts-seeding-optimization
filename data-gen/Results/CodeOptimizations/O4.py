import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()

workflow.copy_required_dirs()
workflow.copy_dir("CodeOptimizations/O4/_baseline")
workflow.copy_dir("CodeOptimizations/O4/globalTiming")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=["oddData.py"],
    DataDir="Results/CodeOptimizations/O4/clean",
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
    DataDir="Results/CodeOptimizations/O4/clean",
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

workflow.copy_required_dirs()
workflow.copy_dir("CodeOptimizations/O4/localTiming/createDoubletsImpl")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/CodeOptimizations/O4/clean",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("TimerParser.py", "PixelSeedingLocalTime1.csv", 0),
        ("TimerParser.py", "StripSeedingLocalTime1.csv", 1),
    ],
    LogFileNames=[
        "PixelSeedingLocalTime1",
        "StripSeedingLocalTime1",
    ],
    PrepareEnvironment=False,
)

workflow.copy_required_dirs()
workflow.copy_dir("CodeOptimizations/O4/_baseline")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/CodeOptimizations/O4/clean",
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

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "PixelSeeding.py",
        "StripSeeding.py",
    ],
    DataDir="Results/CodeOptimizations/O4/clean",
    PythonRunnerArgs=["--version", "GridTriplet", "--events", "3"],
    LogFileNames=[
        "PixelSeeding2Heaptrack",
        "StripSeeding2Heaptrack",
    ],
    Runs=1,
    Profiler="heaptrack",
    PrepareEnvironment=False,
)
