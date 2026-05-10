# environment/

Three shell scripts that bring a fresh machine to the point where `python3 pipelines/all.py` runs. They are thin wrappers around LCG, the ACTS CMake build, and the ACTS Python bindings setup.

## Prerequisites

Before any of these scripts will succeed:

- An Apptainer (Singularity) shell with CVMFS mounted at `/cvmfs/sft.cern.ch/`. The scripts source `/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-el9-gcc13-opt/setup.sh`. If that path does not exist, nothing further will work.
- A local gperftools install at `$HOME/usr/local/`, or a different path provided through the environment variable `ACTS_GPERF_DIR`. Required because ACTS is configured with `-DACTS_ENABLE_CPU_PROFILING=ON`.
- `git-lfs` available on `PATH`. LCG 105 does not ship it, so `setupACTS.sh` installs a static binary into `$HOME/usr/local/bin/` on first run (pinned by `GIT_LFS_VERSION`, overridable with `GIT_LFS_PREFIX`) and registers the LFS filters before cloning. The binary persists across shells. (LFS-tracked content lives in the OpenDataDetector submodule — most importantly `data/odd-material-maps.root`. Without LFS the file checks out as a 133-byte pointer stub and ACTS aborts at runtime.)

## Python dependencies

Python dependencies that pip can install are pinned in the repository-root `requirements.txt`. Inside an LCG shell most of them are already available, with two exceptions (`mplhep` and `boost_histogram`, used only by the physics-validation figure scripts) which always need a separate install:

```bash
pip install -r requirements.txt
# or, if LCG is already sourced and only the non-LCG bits are needed:
pip install mplhep boost_histogram
```

`ROOT` (PyROOT) is provided by LCG. The `acts` Python bindings are produced by the ACTS build performed by `setupACTS.sh`. Neither is pip-installable.

## The three scripts

| Script | Purpose | Invocation |
| --- | --- | --- |
| `setupACTS.sh` | One-time clone, configure, and build of ACTS into `<repo>/ACTS/source/`. Defaults to ACTS `v44.0.0`. Safe to re-run; the `git clone` step is skipped if the source tree already exists. | `bash environment/setupACTS.sh` |
| `setup.sh` | Per-shell setup. Sources LCG 105, activates the ACTS Python bindings, configures OpenDataDetector and gperftools paths, and verifies that `import acts` succeeds. **Must be sourced**, not executed. | `source environment/setup.sh` |
| `build.sh` | Incremental rebuild against the existing ACTS build directory. The data-gen workflow calls this automatically after copying overrides; it can also be invoked by hand after editing files in `acts-overrides/`. | `bash environment/build.sh` (or `source environment/build.sh`) |

## Typical first-time workflow

```bash
# Once per machine
bash environment/setupACTS.sh            # 15-30 min for the full ACTS build

# Once per shell
source environment/setup.sh

# After editing acts-overrides/ by hand
bash utils/CopyDir.sh <variant>
bash environment/build.sh                # incremental rebuild

# Normal use (the pipelines call build.sh on your behalf)
python3 pipelines/all.py
```

## Environment variables

| Variable | Read by | Default | Purpose |
| --- | --- | --- | --- |
| `ACTS_VERSION` | `setupACTS.sh` | `v44.0.0` | ACTS git tag to check out on first install |
| `ACTS_BUILD_JOBS` | `setupACTS.sh`, `build.sh` | `nproc` | `-j` value passed to CMake |
| `ACTS_GPERF_DIR` | `setupACTS.sh`, `setup.sh` | `$HOME/usr/local` | gperftools install prefix |
| `GIT_LFS_VERSION` | `setupACTS.sh` | `v3.5.1` | git-lfs release tag installed if not present |
| `GIT_LFS_PREFIX` | `setupACTS.sh` | `$HOME/usr/local/bin` | Directory for the auto-installed git-lfs binary |
| `PPROF_BIN` | `figure-gen/gperftools_helper.py` | `<repo>/../go/bin/pprof`, then `$HOME/go/bin/pprof` | Path to the Go pprof binary |
| `FLAMEGRAPH_DIR` | `figure-gen/gperftools_helper.py` | `<repo>/../FlameGraph`, then `$HOME/FlameGraph` | Directory containing `flamegraph.pl` and `stackcollapse-go.pl` |

## Note on `setup.sh`
If `source environment/setup.sh` reports `ACTS Python bindings verification failed`, the standard fix is to run `source environment/build.sh`. The verification failure indicates that the ACTS build is stale or did not finish.
