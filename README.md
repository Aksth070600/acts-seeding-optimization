# Performance Optimization of the ACTS Track Seeding Algorithm

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX) <!-- Replace XXXXXXX with the concept DOI Zenodo assigns after the first release is archived. -->
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)

**Status:** Frozen at the `v1.0` release accompanying the thesis submission (Spring 2026). This snapshot is archived on Zenodo (see DOI badge above). No further commits are planned; any post-submission corrections will be made via new tagged releases.

This repository contains the setup, code, and scripts used to produce the results in the master's thesis

**"Optimization of the computing performance of the inner detector track seeding algorithm used by ATLAS for High Luminosity LHC data"**
by **Thomas Aksdal**, University of Oslo (Spring 2026).

It enables reproduction of:

- the profiling workflow (gperftools, callgrind, heaptrack);
- the proposed Spherical algorithm change and the O1–O4 code-level optimisations on top of the Cylindrical baseline;
- the physics validation (seeding efficiency, fake ratio, duplicate ratio);
- every figure and table in the thesis (see `figure-map.md`).

> Absolute runtimes depend on host hardware. The aim is to reproduce trends, relative speedups, and physics behaviour and not identical wall-clock timings.

---

## Repository structure

```text
├── environment/        # ACTS build + per-shell setup scripts
├── acts-overrides/     # ACTS source modifications
├── configs/            # YAML parameter sets and sweep grids
├── data-gen/           # Scripts that invoke ACTS and write raw-data/
├── raw-data/           # Parsed CSVs and profiler artefacts (gitignored)
├── figure-gen/         # Scripts that consume raw-data/ and write figures/
├── figures/            # Final PDFs and LaTeX tables
├── pipelines/          # Driver scripts that sequence data-gen + figure-gen
└── utils/              # CopyDir.sh and the log parsers
```

`data-gen/`, `figure-gen/`, `raw-data/`, and `figures/` mirror each other: `data-gen/Results/<Chapter>/<Figure>.py` produces CSVs under `raw-data/Results/<Chapter>/`, which `figure-gen/Results/<Chapter>/<Figure>.py` consumes to write `figures/Results/<Chapter>/<Figure>.{pdf,tex}`. The directory tree is the figure-to-script map.

Each first-level directory carries its own `README.md`, start there for details:

| For… | Read |
| --- | --- |
| Build environment, ACTS version | `environment/README.md` |
| ACTS source overrides + variant overview | `acts-overrides/README.md` |
| YAML parameter configs | `configs/README.md` |
| Data-gen scripts | `data-gen/README.md` |
| Figure-gen helpers | `figure-gen/README.md` |
| Pipeline orchestration (`all.py`, `figures_all.py`) | `pipelines/README.md` |
| Log parsers and `CopyDir.sh` | `utils/README.md` |
| Thesis-figure / table → script map | `figure-map.md` |

---

## Getting started

ACTS v44.0.0 is built from source. Full details in `environment/README.md`; the short version:

```bash
# Prereqs: Apptainer with CVMFS, gperftools at $HOME/usr/local.

git clone <this-repo> acts-seeding-optimization
cd acts-seeding-optimization
bash environment/setupACTS.sh        # one-time. Clones ACTS, configures CMake, builds.
source environment/setup.sh          # per-shell. Sources LCG 105 + ACTS Python bindings + gperftools.
```

Then reproduce everything reachable in the current environment:

```bash
python3 pipelines/all.py             # data + figures, GNN4Itk-aware
python3 pipelines/figures_all.py     # figures only, against existing raw-data/
```

Single-chapter pipelines live under `pipelines/sections/<chapter>.py` (data-gen + figure-gen) and `pipelines/figures/<chapter>.py` (figure-only). All re-runs are cheap thanks to `Pipeline`'s skip-if-output-exists logic, see `pipelines/README.md`.

### Datasets

- **OpenDataDetector (ODD)** — open, bundled with ACTS via CVMFS. ODD-only chapters reproduce on any host with the Apptainer environment.
- **GNN4Itk** — ATLAS Athena dump, access-restricted. Chapters that depend on it self-skip when it isn't readable.

---

## Citation

If you use this repository or build on this work, please cite:

### Master's Thesis

```bibtex
@mastersthesis{Aksdal2026ACTSTrackSeeding,
  author       = {Aksdal, Thomas},
  title        = {Optimization of the Computing Performance of the Inner Detector Track Seeding Algorithm Used by ATLAS for High Luminosity LHC Data},
  school       = {University of Oslo},
  year         = {2026},
  type         = {Master's Thesis},
  address      = {Oslo, Norway}
}
```

### This Repository

```bibtex
@software{Aksdal2026ACTSTrackSeedingSoftware,
  author    = {Aksdal, Thomas},
  title     = {Performance Optimization of the ACTS Track Seeding Algorithm},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/thomaaks/acts-seeding-optimization} 
}
```

---

## License and contact

BSD 3-Clause License. ACTS itself is distributed under its original license; nothing here alters that.

GitHub issues / PRs are preferred for repository questions; **thomaaks@uio.no** otherwise. ACTS-specific issues should go to the [ACTS project](https://github.com/acts-project/acts) directly.
