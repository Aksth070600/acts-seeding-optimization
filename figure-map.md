# Thesis figure map

Each row maps a thesis figure or table to the script that produces it. The data-gen path is omitted: every `figure-gen/<path>.py` reads from the matching `data-gen/<path>.py`

## Datasets

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table ?.? | Dataset summary (events, particles, hits) | `figure-gen/Datasets/characteristics-table.py` |
| Figure ?.? | Per-event multiplicity histograms | `figure-gen/Datasets/event-multiplicity.py` |
| Figure ?.? | Truth $p_T$ vs $\eta$ scatter | `figure-gen/Datasets/pt-eta.py` |
| Figure ?.? | Track $p_T$ distribution | `figure-gen/Datasets/track-pt.py` |
| Figure ?.? | Track $\eta$ distribution | `figure-gen/Datasets/track-eta.py` |
| Figure ?.? | Track $\phi$ distribution | `figure-gen/Datasets/track-phi.py` |

## Methodology

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Figure ?.? | Per-event running-mean residual after workload correction (illustrates cache warm-up) | `figure-gen/Methods/WarmUpWorkload.py` |

## Baseline — Cylindrical S1 vs GridTriplet S2

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table ?.? | Real-CPU-time per detector for S1 and S2 | `figure-gen/Results/Baseline/RealCPUTime.py` |
| Table ?.? | Workload counts per detector for S1 and S2 | `figure-gen/Results/Baseline/Workload.py` |
| Figure ?.? | Per-stage timing waterfall, S1 vs S2 | `figure-gen/Results/Baseline/Waterfall.py` |
| Figure ?.? | Time per event vs spacepoint count, S1 vs S2 | `figure-gen/Results/Baseline/Scaling.py` |
| Figure ?.? | gperftools annotated comparison (S1 vs S2) | `figure-gen/Results/Baseline/Gperftools.py` |

## Detailed profiling — GridTriplet S2

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table ?.? | Per-stage exclusive timing breakdown (GridTriplet) | `figure-gen/Results/Detailed/StageTiming.py` |
| Figure ?.? | gperftools hotspot annotations (per detector and stage) | `figure-gen/Results/Detailed/GperftoolsHotspots.py` |
| Table ?.? | gperftools top-20 hotspots (Pixel/Strip Seeding2) | `figure-gen/Results/Detailed/Gperftools.py` |
| Figure ?.? | gperftools portrait flamegraph (Pixel/Strip Seeding2) | `figure-gen/Results/Detailed/Gperftools.py` |

## Code optimisations — O1 → O4 chain

`MetricsTable.py` is parameterised: `python3 figure-gen/Results/CodeOptimizations/MetricsTable.py --variant <O1|O1-2|O2|O3|O4>`.

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table ?.? | O1 performance summary (timing + callgrind side-by-side) | `figure-gen/Results/CodeOptimizations/O1/PerformanceTable.py` |
| Table ?.? | O1 physics metrics ($\Delta$ vs Baseline) | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O1` |
| Table ?.? | O1+O2 performance summary | `figure-gen/Results/CodeOptimizations/O1-2/PerformanceTable.py` |
| Table ?.? | O1+O2 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O1-2` |
| Table ?.? | O2 performance summary | `figure-gen/Results/CodeOptimizations/O2/PerformanceTable.py` |
| Table ?.? | O2 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O2` |
| Table ?.? | O3 performance summary | `figure-gen/Results/CodeOptimizations/O3/PerformanceTable.py` |
| Table ?.? | O3 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O3` |
| Table ?.? | O4 performance summary | `figure-gen/Results/CodeOptimizations/O4/PerformanceTable.py` |
| Table ?.? | O4 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O4` |
| Table ?.? | O4 heaptrack table (Seeding2 B$_0$ vs O4, Pixel + Strip) | `figure-gen/Results/CodeOptimizations/O4/HeaptrackTable.py` |

## Algorithm optimisation — Spherical A1

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Figure ?.? | Grid-cell statistics (Cylindrical vs Spherical) | `figure-gen/Results/AlgorithmOptimizations/GridStats.py` |
| Table ?.? | Callgrind summary (B$_0$ vs A1) | `figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py` (writes `A1CallgrindSummary.tex`) |
| Table ?.? | Callgrind per-function breakdown (B$_0$ vs A1) | `figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py` (writes `A1CallgrindFunctions.tex`) |
| Table ?.? | Heaptrack table (B$_0$ vs A1, ODD) | `figure-gen/Results/AlgorithmOptimizations/HeaptrackTables.py` |
| Table ?.? | Physics metrics ($\Delta$ vs B$_0$) | `figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsTable.py` |
| Figure ?.? | Physics metric distributions ($\eta$, $p_T$) | `figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsFigures.py` |
| Table ?.? | Operating-points summary (Cyl B$_0$ vs Best / Fastest) | `figure-gen/Results/AlgorithmOptimizations/OptimizedConfigurationsTable.py` |

### Parameter optimisation (sub-section)

Five 1D sweeps; each varies one knob over the range in
`configs/parameter_optimization.yaml` ``sweeps_1d`` and pins the others at
the SphericalGridTriplet C++ defaults in `configs/spherical_defaults.yaml`.

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Figure ?.? | $\Delta\eta_\mathrm{max}$ sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/DeltaEtaMax.py` |
| Figure ?.? | phiBinDeflectionCoverage sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/PhiBinDeflectionCoverage.py` |
| Figure ?.? | etaBinNeighborsBottom sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/EtaBinNeighborsBottom.py` |
| Figure ?.? | etaBinNeighborsTop sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/EtaBinNeighborsTop.py` |
| Figure ?.? | maxSeedsPerSpM sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/MaxSeedsPerSpM.py` |

## Three-way comparison — S1 vs S2 vs S3 (Spherical)

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table ?.? | Real-CPU-time, three-way | `figure-gen/Results/Seeding3/RealCPUTime.py` |
| Table ?.? | Workload counts, three-way | `figure-gen/Results/Seeding3/Workload.py` |
| Figure ?.? | Per-stage timing waterfall, three-way | `figure-gen/Results/Seeding3/Waterfall.py` |
| Figure ?.? | Time per event vs spacepoints, three-way | `figure-gen/Results/Seeding3/Scaling.py` |
| Figure ?.? | gperftools comparison (S1 + S2) | `figure-gen/Results/Seeding3/Gperftools.py` |
| Figure ?.? | gperftools comparison (S3 alone) | `figure-gen/Results/Seeding3/Gperftools3.py` |
