#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")

from gperftools_helper import (
    require_pprof,
    run_hotspot_suite, write_hotspots_index,
)

PROF_DIR   = Path("raw-data/Results/Baseline/Gperftools")
OUTPUT_DIR = Path("figures/Results/Detailed/Gperftools/Hotspots")
TXT_DIR    = OUTPUT_DIR / "Annotations"

FILE_STEMS = {
    "Pixel": "PixelSeeding2",
    "Strip": "StripSeeding2",
}

def _find_prof_files(stem: str) -> list[Path]:
    bare     = PROF_DIR / f"{stem}.prof"
    suffixed = sorted(PROF_DIR.glob(f"{stem}_run*.prof"))
    if suffixed:
        return suffixed
    if bare.exists():
        return [bare]
    return []


def main() -> None:
    require_pprof()
    if not PROF_DIR.exists():
        raise FileNotFoundError(f"Profile directory not found: {PROF_DIR}")

    processed: list[tuple[str, str]] = []
    missing: list[str] = []
    for detector, stem in FILE_STEMS.items():
        prof_files = _find_prof_files(stem)
        if not prof_files:
            missing.append(f"{stem}.prof or {stem}_run*.prof")
            continue

        print("\n" + "=" * 60)
        print(f"  {detector} detector")
        print("=" * 60)
        run_hotspot_suite(
            prof_files, OUTPUT_DIR, TXT_DIR,
            file_prefix=f"{detector}_",
        )
        processed.append((f"{detector}_", detector))

    if missing:
        raise FileNotFoundError(
            f"No .prof files found in {PROF_DIR} for: {', '.join(missing)}. "
            f"Run data-gen/Results/Baseline/gperftools.py first."
        )

    write_hotspots_index(
        OUTPUT_DIR, TXT_DIR,
        title="Hotspot annotation outputs", variants=processed,
    )
    print(f"\nDone. Annotated {len(processed)} detector(s).")


if __name__ == "__main__":
    main()
