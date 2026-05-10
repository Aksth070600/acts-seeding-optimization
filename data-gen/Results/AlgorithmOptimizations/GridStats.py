import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/GridStats")
workflow.copy_dir("Seeding2/GridStats")
workflow.build_environment()

result = workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations/GridStats",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    Parsers=[
        ("StatsParser.py", "SphericalGridStats.csv", 0),
    ],
    LogFileNames=[
        "SphericalGridStats.log",
    ],
    PrepareEnvironment=False,
    Runs=1, 
)

result = workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations/GridStats",
    PythonRunnerArgs=[
        "--version",
        "GridTriplet",
    ],
    Parsers=[
        ("StatsParser.py", "CylindricalGridStats.csv", 0),
    ],
    LogFileNames=[
        "CylindricalGridStats.log",
    ],
    PrepareEnvironment=False,
    Runs=1,
)
