import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.build_environment()

result = workflow.run(
    RunnerDir=[],
    PythonRunners=[
        "oddData.py",
    ],
    DataDir="Results/AlgorithmOptimizations/PhysicsValidation",
    PythonRunnerArgs=[
        "--version",
        "SphericalGridTriplet",
        "--output-dir",
        "raw-data/Results/AlgorithmOptimizations/PhysicsValidation",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    Parsers=[
        ("MetricsParser.py", "ParamOptimizationMetrics.csv", 0),
    ],
    LogFileNames=[
        "ParameterOptimizationExample.log",
    ],
    PrepareEnvironment=False,
    Runs=1,
)
