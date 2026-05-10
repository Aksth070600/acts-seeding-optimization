import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
        "--events",
        "3",
    ],
    LogFileNames=[
        "CylindricalCallgrind.log",
    ],
    Profiler="callgrind",
    ProfilerArgs=[
        "--collect-atstart=no",
        "--toggle-collect=*GridTripletSeedingAlgorithm::execute*",
    ],
    PrepareEnvironment=False,
    Runs=1,  
)

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
        "--events",
        "3",
    ],
    LogFileNames=[
        "CylindricalHeaptrack.log",
    ],
    Profiler="heaptrack",
    PrepareEnvironment=False,
    Runs=1, 
)
