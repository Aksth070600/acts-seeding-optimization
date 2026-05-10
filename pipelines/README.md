# pipelines/

Driver scripts that sequence `data-gen/*.py` and `figure-gen/*.py` for each thesis chapter. Every pipeline uses the `Pipeline` class from `pipeline.py`, which skips a step when all of its declared output files already exist, so re-running a pipeline only redoes work whose output is missing. The skip-check looks for the correct number of run files; if `configs/config.yaml` `events` or `runs` change, delete the affected `raw-data/` subtree manually before re-running.

- `sections/<chapter>.py` — runs both data-gen and figure-gen.
- `figures/<chapter>.py` — runs only figure-gen against existing `raw-data/`. Use after editing a plot style or helper.

## Chapters

| Pipeline (in `sections/` and `figures/`) | Dataset | Output |
| --- | --- | --- |
| `datasets.py` | GNN4Itk | `raw-data/Datasets/`. Input-dataset characterisation |
| `methods.py` | GNN4Itk | `raw-data/Methods/`. Warm-up running-mean figure |
| `baseline.py` | GNN4Itk | `raw-data/Results/Baseline/`. CPU time, workload, waterfall, scaling, gperftools (S1+S2) |
| `detailed.py` | GNN4Itk | `raw-data/Results/Detailed/`. Stage timing, callgrind, gperftools, heaptrack (S2 deep dive) |
| `code_optimizations.py` | GNN4Itk + ODD | `raw-data/Results/CodeOptimizations/`. Timing on GNN4Itk, physics on ODD |
| `seeding3.py` | ODD | `raw-data/Results/Seeding3/`. Three-way S1 / S2 / S3 comparison |
| `algorithm_optimizations.py` | ODD | `raw-data/Results/AlgorithmOptimizations/`. Timing, GridStats, physics validation, callgrind/heaptrack, OptimizedConfigurations summary |
| `parameter_optimization.py` | ODD | `raw-data/Results/AlgorithmOptimizations/ParameterOptimization/`. Cyl baseline + five 1D parameter sweeps (`deltaEtaMax`, `phiBinDeflectionCoverage`, `etaBinNeighborsBottom`, `etaBinNeighborsTop`, `maxSeedsPerSpM`) anchored at the SphericalGridTriplet C++ defaults, plus the corresponding 1D-sweep figures. The full search pipeline (coarse / refined grids, picker, Confirmation) lives at `configs/parameter_optimization/` — see that folder's README for the funnel that picks the Best / Fastest operating points committed in `configs/seeding3_*.yaml` |

GNN4Itk pipelines gate themselves with `p.requires(GNN4ITK_DATASET_PATH)` and self-skip when the dump (`/storage/shared/ACTS/user.avallier.38040858.EXT0._000074.Dump_GNN4Itk.root`) isn't readable. ODD pipelines run on any host with the Apptainer environment via CVMFS.

## Convenience drivers

```bash
python3 pipelines/all.py          # data + figures, every pipeline reachable in this environment
python3 pipelines/figures_all.py  # figures only, against whatever raw-data/ already exists
```

`all.py` probes for the GNN4Itk dump and adapts: with the dump it runs every chapter; without it, only the ODD chapters.

## Output

- Parsed CSVs / metric files / profiler artefacts (`.prof`, `.callgrind`, `.heaptrack`) — under `raw-data/<Section>/…`.
- Per-runner stdout/stderr — under `raw-data/temp/<Section>/…`. Ephemeral, regenerated each run.
- Rendered figures — under `figures/<Section>/…`.

Everything under `raw-data/` and `figures/` is gitignored.

## Layout

```
pipelines/
├── pipeline.py                          # Pipeline class (driver)
├── all.py                               # data + figures, GNN4Itk-aware
├── figures_all.py                       # figures only, raw-data-aware
│
├── sections/<chapter>.py × 8            # data-gen + figure-gen per chapter
└── figures/<chapter>.py  × 8            # figures-only counterpart
```

Run all commands from the repository root.
