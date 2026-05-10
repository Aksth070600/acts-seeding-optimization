import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/globalTiming")
workflow.build_environment()

result = workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations/Timing",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    Parsers=[
        ("TimerParser.py", "SphericalTiming.csv", 0),
    ],
    LogFileNames=[
        "SphericalTiming.log",
    ],
    PrepareEnvironment=False,
)

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("Seeding2/globalTiming")
workflow.build_environment()

result = workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations/Timing",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("TimerParser.py", "CylindricalTiming.csv", 0),
    ],
    LogFileNames=[
        "CylindricalTiming.log",
    ],
    PrepareEnvironment=False,
)
