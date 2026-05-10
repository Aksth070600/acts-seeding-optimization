# data-gen/

Runner scripts that invoke ACTS via the `DataGenWorkflow` class in `workflow.py` and write parsed CSVs (and profiler artefacts) under `raw-data/`. Each script is a thin overhead file: it picks a set of `acts-overrides/` variants to layer on top of ACTS, picks a runner (`oddData.py`, `PixelSeeding.py`, or `StripSeeding.py`), and points the workflow at the relevant log parsers.

## Layout

```
data-gen/
├── workflow.py            # DataGenWorkflow + load_config + parameter_args
├── Datasets/              # input-dataset characterisation
├── Methods/               # methodology figures
└── Results/               # the thesis result chapters
    ├── Baseline/                           # S1 vs S2 comparison
    ├── Detailed/                           # S2 deep profiling
    ├── CodeOptimizations/                  # O1 → O4 chain
    ├── Seeding3/                           # S1 vs S2 vs S3 three-way comparison
    └── AlgorithmOptimizations/             # A1
        └── ParameterOptimization/          # Cyl baseline + 1D sweeps
```

The grid-search orchestration on top of these data scripts (coarse /
refined grids, picker, Confirmation) lives at
`configs/parameter_optimization/` — see that folder's README.

The directory tree mirrors `figure-gen/`, `raw-data/`, and `figures/`, so each chapter's data-gen, figure-gen, raw output, and rendered figure live at parallel paths.

## How a script looks

```python
from workflow import DataGenWorkflow, parameter_args

workflow = DataGenWorkflow()
workflow.copy_required_dirs()                                     
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/globalTiming")
workflow.build_environment()

workflow.run(
    PythonRunners=["oddData.py"],
    DataDir="Results/<Chapter>/<Subdir>",
    PythonRunnerArgs=["--version", "SphericalGridTriplet", *parameter_args("parameter_optimization/winners/best")],
    Parsers=[
        ("TimerParser.py",   "Timing.csv",  0),
        ("MetricsParser.py", "Metrics.csv", 0),
    ],
    LogFileNames=["chapter.log"],
)
```

`workflow.run()` does the per-cell loop, runs ACTS, runs each parser on the log, and writes the parsed CSVs under `raw-data/<DataDir>/`. When `Sweep={"--parameters": [...]}` is provided, each entry produces one cell (`_run1.csv`, `_run2.csv`, …) on top of `PythonRunnerArgs`.
