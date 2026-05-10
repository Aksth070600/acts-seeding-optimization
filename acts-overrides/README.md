# acts-overrides/

Source-level patches applied on top of `ACTS/source/` before each benchmark build. Each subdirectory is a named *variant*; `utils/CopyDir.sh <variant>` copies every file in the variant directory into ACTS at the corresponding path.

The destination path is encoded in the file's basename: every `/` in the destination becomes `_`. So `Core_src_Seeding2_DoubletSeedFinder.cpp` lands at `ACTS/source/Core/src/Seeding2/DoubletSeedFinder.cpp`.

## How variants are used

`DataGenWorkflow.run()` calls `utils/CopyDir.sh` in this order before each build:

1. `clean/` — always first. Restores the ACTS files to the baseline for the files any variant might patch.
2. `runners/` — always second. Adds the Python Script that runs the Seeding Algorithm (`PixelSeeding.py`, `StripSeeding.py`, `oddData.py`, `common.py`) and the `timer-helper.h` / `stats-helper.h` headers.
3. Each entry in the data-gen script's `RunnerDir` parameter, in order, added on top.

Then `environment/build.sh` rebuilds ACTS. Each step is a plain copy, so later variants overwrite earlier ones.

**WARNING:** `clean/` must contain every file that any variant ever touches. Otherwise switching from one variant to another (which always begins with a fresh `clean/` copy) would silently inherit the previous variant's patch.

## Variant Overview

```
acts-overrides/
├── clean/                 # Baseline ACTS source for every patched file
├── runners/               # Python Runner Scripts + C/C++ helper headers
│
├── Seeding/               # Algorithm S1 (--version Default)
│   ├── globalTiming/      #   TIMER("Seeding") wrap on execute()
│   ├── StageTiming/       #   per-stage TIMER calls (waterfall)
│   └── Workload/          #   STATS counters
│
├── Seeding2/              # Algorithm S2 (--version GridTriplet)
│   ├── globalTiming/
│   ├── StageTiming/
│   ├── Workload/
│   ├── GridStats/         #   per-grid-cell STATS counters
│   └── Callgrind/         #   CALLGRIND_* hooks
│
├── Seeding3/              # Algorithm S3 (--version SphericalGridTriplet)
│   ├── _baseline/         #   un-instrumented Doublet+TripletSeedFinder (shared)
│   ├── Scaling/           #   global TIMER (events-vs-time scaling figure)
│   ├── StageTiming/       #   per-stage TIMER (waterfall)
│   └── Workload/          #   STATS counters
│
├── CodeOptimizations/     # Code Level Optimizations on top of S2
│   ├── _baseline/                       #   pre-optimisation S2 reference
│   │   └── localTiming/<function>/      #     wrapped around <function>
│   ├── O1/   { _baseline/, localTiming/<function>/ }
│   ├── O1-2/ { _baseline/, localTiming/<function>/ }
│   ├── O2/   { _baseline/, localTiming/<function>/ }
│   ├── O3/   { _baseline/ }
│   └── O4/   { _baseline/, globalTiming/, localTiming/<function>/ }
│
└── AlgorithmOptimizations/
    └── Phi-Eta-R-Binning/                # S3 binning studies
        ├── _baseline/                    #   Spherical Seeding Implementation
        ├── globalTiming/                 #   TIMER("Seeding") wrap on execute()
        └── GridStats/                    #   per-grid-cell STATS counters
```

## What `_baseline/` means

A `_baseline/` subdirectory holds the un-instrumented version of its parent variant as they are before any specific timer / stats / callgrind wrapping is added on top. 

`_baseline` is always a variant *container directory*.

## Adding a new override

1. Pick the variant directory the new override extends, or create one.
2. Encode the destination path inside `ACTS/source/` by replacing every `/` with `_`. For example, `ACTS/source/Core/src/Foo.cpp` becomes `Core_src_Foo.cpp`. Place the file in the variant directory at that name.
3. Confirm the basename has no underscore (rename the source file if it does), and that no directory in the destination path contains one.
4. If this is the first variant to touch the file, add the upstream ACTS copy to `clean/` under the same encoded name. Without this, a later experiment that doesn't re-patch the file will silently inherit your change.
5. Reference the new variant from a data-gen script's `RunnerDir=[…]` argument or `workflow.copy_dir(…)` call.
