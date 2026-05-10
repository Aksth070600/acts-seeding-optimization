import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        "--events",
        "3",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    LogFileNames=[
        "SphericalCallgrind.log",
    ],
    Profiler="callgrind",
    ProfilerArgs=[
        "--collect-atstart=no",
        "--toggle-collect=*SphericalGridTripletSeedingAlgorithm::execute*",
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
        "SphericalGridTriplet",
        "--events",
        "3",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    LogFileNames=[
        "SphericalHeaptrack.log",
    ],
    Profiler="heaptrack",
    PrepareEnvironment=False,
    Runs=1,
)

