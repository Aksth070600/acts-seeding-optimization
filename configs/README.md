# configs/

YAML data loaded via `load_config(name)` from `data-gen/workflow.py`. Subpaths
work, e.g. `load_config("parameter_optimization/winners/best")`.

| File | Purpose |
| --- | --- |
| `config.yaml` | `events` and `runs` auto-injected into every data-gen run. |
| `parameter_optimization.yaml` | Value ranges for the eight 1D sweeps. Read by both data-gen and figure-gen so axes stay in sync. |
| `spherical_defaults.yaml` | C++ defaults of `SphericalGridTripletSeedingAlgorithm::Config`. Anchor for the 1D sweeps. |
| `parameter_optimization/winners/max_efficiency.yaml` | MaxEfficiency operating point (argmax eff). Passed to `SphericalGridTriplet` via `--parameters`. |
| `parameter_optimization/winners/best.yaml` | Best operating point (no-regress). Same shape. |
| `parameter_optimization/winners/fastest.yaml` | Fastest operating point (eff floor 0.95). Same shape. |

The three winners are produced by `parameter_optimization/pick_winners.py`
and consumed directly by every Seeding3 + AlgorithmOptimizations runner
— there is no intermediate `seeding3_*.yaml` copy.
