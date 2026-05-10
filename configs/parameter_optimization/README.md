# SphericalGridTriplet parameter-optimisation pipeline

A staged, declarative search for the SphericalGridTriplet seeder's
operating points. Configs in this folder describe **what** is being
optimised; the runner scripts in this folder execute the **how**.
This file is the authoritative reference for the procedure.

## 1. Overview

The pipeline has four stages, each producing a well-defined artefact
the next stage consumes:

```
   Stage 1 — 1D characterisation       (run_1d_sweep.py / run_all_1d_sweeps.py)
       │     anchor + one swept axis
       │     →  raw-data/.../<Axis>/results.csv
       ▼
   Stage 2 — Grid interval definition  (manual: edit grid.yaml)
       │     active intervals derived from the 1D response curves;
       │     saturated values excluded; rationale in grid.yaml notes
       ▼
   Stage 3 — Joint grid search         (run_grid.py)
       │     Cartesian product of grid.yaml axes at events=5
       │     →  raw-data/.../Grid/results.csv
       ▼
   Stage 4 — Confirmation + winners    (run_confirmation.py / pick_winners.py)
             top-K candidates per rule reran at events=50; the strict
             selection rules then choose one winner per category
             →  configs/parameter_optimization/winners/<rule>.yaml
```

The four selection categories are:

| Rule | Definition |
|---|---|
| `max_efficiency` | argmax `eff` (no constraints); tiebreak min time |
| `best`           | argmin `time` over { Δeff ≥ -ε, Δfake ≤ ε, Δdup ≤ ε }; tiebreak max `eff` |
| `fastest`        | argmin `time` over { eff ≥ floor, Δfake ≤ ε, Δdup ≤ ε }; tiebreak max `eff` |

Δ is measured against the Cylindrical-grid baseline. ε defaults to
`tolerance_pp = 0.1` and `floor = 0.95`; both live in
`selection_rules.yaml`. Rule shapes are stable and live in
`pick_winners.py` — only the tolerances move.

## 2. Quickstart: re-running the existing eight-axis optimisation

The committed `winners/*.yaml` operating points came from the historical
RefinedGrid run; the configs in this folder reproduce that run. The
eight axes are: `DeltaEtaMax`, `PhiBinDeflectionCoverage`,
`EtaBinNeighborsBottom`, `EtaBinNeighborsTop`, `MaxSeedsPerSpM`,
`ImpactMax`, `CompatSeedLimit`, `DeltaRMax`. (`sigmaScattering` is
held fixed in `anchor.yaml`.)

```bash
# 0. one-time: the Cylindrical baseline (every Δ is computed against this)
python3 data-gen/Results/AlgorithmOptimizations/ParameterOptimization/Baseline.py

# 1. Stage 1 — 1D characterisation, one axis at a time
python3 configs/parameter_optimization/run_all_1d_sweeps.py
#   or one axis at a time:
#   python3 configs/parameter_optimization/run_1d_sweep.py \
#       --axis configs/parameter_optimization/axes/DeltaEtaMax.yaml

# 2. Stage 2 — derive grid.yaml intervals from the 1D results
#   (manual; see "Deriving the grid" below).

# 3. Stage 3 — joint grid search
python3 configs/parameter_optimization/run_grid.py     # ~8.9 h at 864 cells × 5 events

# 4. Stage 4a — confirmation reruns at events=50
python3 configs/parameter_optimization/run_confirmation.py [--top 5]

# 4b. Stage 4b — apply the strict rules + write winners
python3 configs/parameter_optimization/pick_winners.py
```

To monitor a long sweep without waiting:

```bash
python3 utils/check_progress.py --top 5
```

## 3. Adding a new parameter

The pipeline is parameter-agnostic — adding a knob is a config-only
operation. Concretely:

1. **Add the parameter to `anchor.yaml`** at its runner-default value
   (the untuned starting point).
2. **Create `axes/<NewParameter>.yaml`** mirroring an existing file:

   ```yaml
   parameter: NewParameter        # PascalCase, matches the filename
   events: 5
   values: [<sweep range>]
   notes: |
     Rationale for the range.
   ```

   For neighbor-style axes (per-eta-bin pairs), use `[lo, hi]` pairs
   in `values` instead of scalars (see
   `axes/EtaBinNeighborsBottom.yaml` for the pattern).
3. **Register the runner key** in `_common.AXIS_NAMES` so the runner
   knows the camelCase form of the new PascalCase display name.
4. **Run the 1D characterisation**:
   `run_1d_sweep.py --axis configs/parameter_optimization/axes/NewParameter.yaml`.
5. **Inspect** `raw-data/.../NewParameter/results.csv`. If the
   parameter produces a meaningful response (eff/fake/dup/time
   variation outside the events=5 noise floor), continue; otherwise
   leave it at its anchor value and stop here.
6. **Add an active interval to `grid.yaml`**. Use the subset of
   1D-sweep values where the response is largest, plus a margin.
   Document the rationale in the file's `notes:` block.
7. **Re-run** `run_grid.py`, `run_confirmation.py`,
   `pick_winners.py`. The runners pick up the new axis automatically
   from the YAMLs.

`grid.yaml` is **derived** from the 1D sweeps. Do not edit it
without first inspecting the 1D response curves the new entry is
supposed to summarise.

## 4. Removing a parameter from the joint search

Two cases:

- **Stop sweeping it but keep the algorithm using it.** Delete the
  parameter's entry from `grid.yaml`. It will be held at its
  `anchor.yaml` value during grid runs. The corresponding
  `axes/<P>.yaml` can be kept for characterisation purposes or
  deleted; neither breaks the pipeline.
- **Drop it entirely from the algorithm.** Remove from
  `anchor.yaml`, remove `axes/<P>.yaml`, remove from
  `_common.AXIS_NAMES`, then verify the runner accepts the reduced
  parameter set.

## 5. Deriving the grid

The intervals in `grid.yaml` are the active ranges identified in the
1D sweeps — the values that produced meaningful response, plus
margin. Saturated values are excluded; values below the events=5
noise floor are excluded.

The current `grid.yaml` is inherited from the historical RefinedGrid
run (864 cells) so the pipeline reproduces immediately. Where the 1D
sweep showed saturation, the corresponding axis is held at a
**single** value in `grid.yaml` (e.g. `phiBinDeflectionCoverage: [8]`)
rather than dropped, so the iteration order and cell count remain
explicit.

When new 1D sweeps run from the current `anchor.yaml`, regenerate
`grid.yaml` by:

1. Inspecting each `raw-data/.../<Axis>/results.csv`.
2. Picking the values that span the response curve's active region.
3. Writing `notes:` summarising why each axis has its current values.

## 6. Selection rules

The three selection rules are defined in
`selection_rules.yaml`; the rule shapes (constraint conjunctions) are
stable and live in `pick_winners.py`. The YAML carries only the
numerical knobs and human-readable descriptions:

```yaml
tolerance_pp: 0.1
fastest_efficiency_floor: 0.95

baseline:
  source: raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Baseline
  description: Cylindrical-grid baseline at runner defaults

rules:
  max_efficiency:  { description: "Highest efficiency, no constraints. ..." }
  best:            { description: "Lowest time subject to no-regress on every metric ..." }
  fastest:         { description: "Lowest time subject to absolute efficiency floor ..." }
```

The descriptions are intended to match the Methods chapter's formal
definitions verbatim so the chapter and the config cannot drift.

## 7. What is not in this pipeline

- **Additive over-marginals prediction.** The "extrapolate from the
  five 1D sweeps and pick the predicted top cell" model is not part
  of selection. The methodology selects winners from measured joint
  responses, never from additive predictions.

## Notes

### Legacy 1D sweep CSVs

The per-axis CSVs currently at
`raw-data/Results/AlgorithmOptimizations/ParameterOptimization/<Axis>/`
were produced from a previous anchor configuration (before the
restructure committed `anchor.yaml` at runner defaults). Before any
new 1D sweeps run from the new anchor, archive the existing
directories to
`raw-data/Results/AlgorithmOptimizations/ParameterOptimization/legacy_1d_sweeps_pre_restructure/<Axis>/`
to avoid co-mingling pre- and post-restructure results. The thesis
figure scripts continue to read the legacy data from the original
locations until then; once new sweeps run, they will overwrite those
locations with measurements from the new anchor.

### `winners/`

`pick_winners.py` writes the three operating points directly to
`winners/{max_efficiency,best,fastest}.yaml`. Every Seeding3 +
AlgorithmOptimizations runner (and the presentation) reads those files
via `parameter_args("parameter_optimization/winners/<rule>")` — there
is no intermediate `seeding3_*.yaml` copy any more.

### `configs/parameter_optimization.yaml`

A pre-restructure file at `configs/parameter_optimization.yaml` carries
a `sweeps_1d:` block with the per-axis value lists. The thesis figure
scripts (which are out of scope for this restructure) still read it
via `load_config("parameter_optimization")` to size their cell count.
The new pipeline sources axes from `axes/*.yaml`. The two files'
value lists are in sync for the five axes that exist in both;
diverging is harmless until a future commit retires
`parameter_optimization.yaml`.

## File index

```
configs/parameter_optimization/
├── README.md                  ← this file
├── anchor.yaml                ← shared default configuration
├── axes/                      ← one file per swept parameter
│   ├── DeltaEtaMax.yaml
│   ├── PhiBinDeflectionCoverage.yaml
│   ├── EtaBinNeighborsBottom.yaml
│   ├── EtaBinNeighborsTop.yaml
│   ├── MaxSeedsPerSpM.yaml
│   ├── ImpactMax.yaml         ← TODO: 1D range
│   ├── CompatSeedLimit.yaml   ← TODO: 1D range
│   └── DeltaRMax.yaml         ← TODO: 1D range
├── grid.yaml                  ← joint-search intervals (Stage 2)
├── selection_rules.yaml       ← tolerance + floor + descriptions
├── confirmation.yaml          ← events=50
├── winners/                   ← populated by pick_winners.py
├── _common.py                 ← shared helpers
├── run_1d_sweep.py            ← Stage 1 (one axis)
├── run_all_1d_sweeps.py       ← Stage 1 wrapper
├── run_grid.py                ← Stage 3
├── run_confirmation.py        ← Stage 4a
└── pick_winners.py            ← Stage 4b
```

The Cyl baseline runner stays under
`data-gen/Results/AlgorithmOptimizations/ParameterOptimization/Baseline.py`
because its CSV feeds the thesis 1D-sweep figures directly.
