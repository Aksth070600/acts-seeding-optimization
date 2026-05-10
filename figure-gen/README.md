# figure-gen/

Plot and table renderers that read parsed CSVs (and profiler artefacts) from `raw-data/` and write under `figures/`. The chapter tree mirrors `data-gen/`, `raw-data/`, and `figures/`, so each figure script lives at the same relative path as the data-gen script that produces its inputs (see `data-gen/README.md` for the layout).

## helpers

| File | Purpose |
| --- | --- |
| `_common.py`, `_style.py` | Matplotlib rcParams + sizing constants imported by every figure |
| `bootstrap_ci_helper.py` | Bootstrap mean / geometric-mean-ratio CIs used by waterfall + scaling |
| `waterfall_helper.py` | Per-stage CSV parsing + waterfall plotting (Baseline + Seeding3) |
| `codeopts_helpers.py` | Per-variant CSV loaders shared across all CodeOptimizations tables |
| `gperftools_helper.py` | `pprof` wrappers for the Baseline + Seeding3 gperftools figures |
| `heaptrack_summary.py` | Hand-curated heaptrack values (ODD + GNN4ITk per-detector) |
| `heaptrack_table_helper.py` | LaTeX renderer used by both AlgorithmOptimizations and CodeOptimizations heaptrack tables |
| `parameter_scan_plotter.py` | 2-panel 1D-sweep figure helper used by the five ParameterOptimization sweeps |
