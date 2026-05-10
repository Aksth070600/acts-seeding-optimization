#!/usr/bin/env python3

# Top-20 hotspot table + portrait flamegraph per detector for the
# Detailed chapter. Reuses .prof files from data-gen/Results/Baseline/gperftools.py.
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")

from gperftools_helper import (
    require_pprof,
    write_text_report, parse_text_report,
    write_flamegraph,
    latex_function_table, verify_tex_against_report,
)

PROF_DIR   = Path("raw-data/Results/Baseline/Gperftools")
OUTPUT_DIR = Path("figures/Results/Detailed/Gperftools")
TXT_DIR    = OUTPUT_DIR / "txt_reports"

SHOW_FROM = "GridTripletSeedingAlgorithm"
TOP_N     = 20

# Memory-primitive symbols that surface as top-N rows without algorithmic
# insight; filtered from the rendered table but kept in the .prof/.txt.
LIBC_NOISE = (
    "__memmove",
    "__memset",
    "__memcpy",
    "__strncpy",
    "__strncmp",
)

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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TXT_DIR.mkdir(parents=True, exist_ok=True)

    skip = (SHOW_FROM,) + LIBC_NOISE
    written: list[Path] = []
    missing: list[str] = []

    for det, stem in FILE_STEMS.items():
        prof_files = _find_prof_files(stem)
        if not prof_files:
            missing.append(f"{stem}.prof or {stem}_run*.prof")
            continue

        print("\n" + "=" * 60)
        print(f"  {det} Seeding2  (TOP_N={TOP_N})")
        print("=" * 60)

        txt   = write_text_report(prof_files,
                                  TXT_DIR / f"{det}_Seeding2_report.txt",
                                  SHOW_FROM)
        funcs = parse_text_report(txt, TOP_N, skip_tokens=skip)
        if not funcs:
            raise RuntimeError(
                f"{det}: parsed function list is empty -- pprof report "
                f"has no rows matching SHOW_FROM={SHOW_FROM!r}. The "
                f".prof files may be empty or the focus name may have "
                f"changed."
            )
        sections = [(None, funcs)]
        latex = latex_function_table(f"{det} Seeding2 (top {TOP_N})",
                                     sections, TOP_N, numbered=True)
        out_tex = OUTPUT_DIR / f"{det}_Seeding2_top{TOP_N}.tex"
        out_tex.write_text(latex)
        verify_tex_against_report(out_tex, sections)
        written.append(out_tex)
        print(f"  Table saved (verified): {out_tex}")

        # Portrait flamegraph for sidewaysfigure layout.
        out_svg = OUTPUT_DIR / f"{det}_Seeding2_flamegraph.svg"
        write_flamegraph(prof_files, out_svg, SHOW_FROM, title="",
                         width=1200, height_per_frame=32, fontsize=13)
        written.append(out_svg)

    if missing:
        raise FileNotFoundError(
            f"No .prof files found in {PROF_DIR} for: {', '.join(missing)}. "
            f"Run data-gen/Results/Baseline/gperftools.py first."
        )

    print(f"\nDone. Wrote {len(written)} artefacts.")


if __name__ == "__main__":
    main()
