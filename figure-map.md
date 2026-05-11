# Thesis figure map

Each row maps a thesis figure or table to the script that produces it. The data-gen path is omitted: every `figure-gen/<path>.py` reads from the matching `data-gen/<path>.py`

## Datasets

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 4.1 | Dataset summary (events, particles, hits) | `figure-gen/Datasets/characteristics-table.py` |
| Figure 4.1 | Per-event multiplicity histograms | `figure-gen/Datasets/event-multiplicity.py` |
| Figure 4.2 | Truth $p_T$ vs $\eta$ scatter | `figure-gen/Datasets/pt-eta.py` |
| Figure 4.2 | Track $p_T$ distribution | `figure-gen/Datasets/track-pt.py` |
| Figure 4.2 | Track $\eta$ distribution | `figure-gen/Datasets/track-eta.py` |
| Figure 4.2 | Track $\phi$ distribution | `figure-gen/Datasets/track-phi.py` |

## Methodology

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Figure 5.2 | Per-event running-mean residual after workload correction (illustrates cache warm-up) | `figure-gen/Methods/WarmUpWorkload.py` |

## Baseline — Cylindrical S1 vs GridTriplet S2

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 6.1 | Real-CPU-time per detector for S1 and S2 | `figure-gen/Results/Baseline/RealCPUTime.py` |
| Table 6.2 | Workload counts per detector for S1 and S2 | `figure-gen/Results/Baseline/Workload.py` |
| Figure 6.1 | Per-stage timing waterfall, S1 vs S2 | `figure-gen/Results/Baseline/Waterfall.py` |
| Figure 6.3 + Table 6.5 | Time per event vs spacepoint count, S1 vs S2 | `figure-gen/Results/Baseline/Scaling.py` |
| Figure 6.2 (+ B.1, B.4 flamegraphs; B.2, B.3, B.5, B.6 callgraphs in appendix) | gperftools annotated comparison (S1 vs S2) | `figure-gen/Results/Baseline/Gperftools.py` |

## Detailed profiling — GridTriplet S2

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 6.6 | Per-stage exclusive timing breakdown (GridTriplet) | `figure-gen/Results/Detailed/StageTiming.py` |
| Figure 6.4 (+ B.4 in appendix) | gperftools hotspot annotations (per detector and stage) | `figure-gen/Results/Detailed/GperftoolsHotspots.py` |
| Tables 6.7, 6.8 | gperftools top-20 hotspots (Pixel/Strip Seeding2) | `figure-gen/Results/Detailed/Gperftools.py` |
| Figure B.20 | gperftools portrait flamegraph (Pixel/Strip Seeding2) | `figure-gen/Results/Detailed/Gperftools.py` |

## Code optimisations — O1 → O4 chain

`MetricsTable.py` is parameterised: `python3 figure-gen/Results/CodeOptimizations/MetricsTable.py --variant <O1|O1-2|O2|O3|O4>`.

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 6.10 | O1 performance summary (timing + callgrind side-by-side) | `figure-gen/Results/CodeOptimizations/O1/PerformanceTable.py` |
| Table 6.11 | O1 physics metrics ($\Delta$ vs Baseline) | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O1` |
| Table 6.19 | O1+O2 performance summary | `figure-gen/Results/CodeOptimizations/O1-2/PerformanceTable.py` |
| Table 6.20 | O1+O2 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O1-2` |
| Table 6.12 | O2 performance summary | `figure-gen/Results/CodeOptimizations/O2/PerformanceTable.py` |
| Table 6.13 | O2 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O2` |
| Table 6.14 | O3 performance summary | `figure-gen/Results/CodeOptimizations/O3/PerformanceTable.py` |
| Table 6.15 | O3 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O3` |
| Table 6.17 | O4 performance summary | `figure-gen/Results/CodeOptimizations/O4/PerformanceTable.py` |
| Table 6.18 | O4 physics metrics | `figure-gen/Results/CodeOptimizations/MetricsTable.py --variant O4` |
| Table 6.16 | O4 heaptrack table (Seeding2 B$_0$ vs O4, Pixel + Strip) | `figure-gen/Results/CodeOptimizations/O4/HeaptrackTable.py` |

## Algorithm optimisation — Spherical A1

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 6.22 | Grid-cell statistics (Cylindrical vs Spherical) | `figure-gen/Results/AlgorithmOptimizations/GridStats.py` |
| Table 6.23 | Callgrind summary (B$_0$ vs A1) | `figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py` (writes `A1CallgrindSummary.tex`) |
| Table 6.24 | Callgrind per-function breakdown (B$_0$ vs A1) | `figure-gen/Results/AlgorithmOptimizations/CallgrindTables.py` (writes `A1CallgrindFunctions.tex`) |
| Table 6.25 | Heaptrack table (B$_0$ vs A1, ODD) | `figure-gen/Results/AlgorithmOptimizations/HeaptrackTables.py` |
| Table ?.? | Physics metrics ($\Delta$ vs B$_0$) | `figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsTable.py` |
| Figure 6.5 (+ B.7–B.10 in appendix) | Physics metric distributions ($\eta$, $p_T$) | `figure-gen/Results/AlgorithmOptimizations/PhysicsValidation/MetricsFigures.py` |
| Table 6.21 | Operating-points summary (Cyl B$_0$ vs Best / Fastest) | `figure-gen/Results/AlgorithmOptimizations/OptimizedConfigurationsTable.py` |

### Parameter optimisation (sub-section)

Five 1D sweeps; each varies one knob over the range in
`configs/parameter_optimization.yaml` ``sweeps_1d`` and pins the others at
the SphericalGridTriplet C++ defaults in `configs/spherical_defaults.yaml`.

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Figure B.11 | $\Delta\eta_\mathrm{max}$ sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/DeltaEtaMax.py` |
| Figure B.14 | phiBinDeflectionCoverage sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/PhiBinDeflectionCoverage.py` |
| Figure B.12 | etaBinNeighborsBottom sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/EtaBinNeighborsBottom.py` |
| Figure B.13 | etaBinNeighborsTop sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/EtaBinNeighborsTop.py` |
| Figure B.17 | maxSeedsPerSpM sweep | `figure-gen/Results/AlgorithmOptimizations/ParameterOptimization/MaxSeedsPerSpM.py` |

## Three-way comparison — S1 vs S2 vs S3 (Spherical)

| Thesis ref | What it shows | Script |
| --- | --- | --- |
| Table 6.26 | Real-CPU-time, three-way | `figure-gen/Results/Seeding3/RealCPUTime.py` |
| Table 6.27 | Workload counts, three-way | `figure-gen/Results/Seeding3/Workload.py` |
| Figure 6.6 | Per-stage timing waterfall, three-way | `figure-gen/Results/Seeding3/Waterfall.py` |
| Figure 6.7 + Table 6.28 | Time per event vs spacepoints, three-way | `figure-gen/Results/Seeding3/Scaling.py` |
| Figures B.19, B.20, B.22, B.23 | gperftools comparison (S1 + S2) | `figure-gen/Results/Seeding3/Gperftools.py` |
| Figures B.21, B.24 + Table B.1 | gperftools comparison (S3 alone) | `figure-gen/Results/Seeding3/Gperftools3.py` |
