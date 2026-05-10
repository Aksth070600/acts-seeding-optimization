#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")

from gperftools_helper import (
    require_pprof,
    write_text_report, parse_text_report,
    write_flamegraph, write_callgraph,
    latex_function_table, verify_tex_against_report,
)

PROF_DIR   = Path("raw-data/Results/Baseline/Gperftools")
OUTPUT_DIR = Path("figures/Results/Baseline/Gperftools")
TXT_DIR    = OUTPUT_DIR / "txt_reports"

SHOW_FROM = {
    "Seeding":  "SeedingAlgorithm",
    "Seeding2": "GridTripletSeedingAlgorithm",
}
TOP_N = 10

# Memory-primitive symbols filtered from the table; kept in .prof/.txt.
LIBC_NOISE = (
    "__memmove",
    "__memset",
    "__memcpy",
    "__strncpy",
    "__strncmp",
)

FILE_STEMS = {
    ("Pixel", "Seeding"):  "PixelSeeding",
    ("Strip", "Seeding"):  "StripSeeding",
    ("Pixel", "Seeding2"): "PixelSeeding2",
    ("Strip", "Seeding2"): "StripSeeding2",
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

    skip = tuple(SHOW_FROM.values()) + LIBC_NOISE
    funcs_by_key: dict[tuple[str, str], list] = {}
    txt_by_key:   dict[tuple[str, str], Path] = {}
    missing: list[str] = []

    for (det, ver), stem in FILE_STEMS.items():
        prof_files = _find_prof_files(stem)
        if not prof_files:
            missing.append(f"{stem}.prof or {stem}_run*.prof")
            continue
        focus = SHOW_FROM[ver]
        txt = write_text_report(prof_files, TXT_DIR / f"{det}_{ver}_report.txt", focus)
        funcs_by_key[(det, ver)] = parse_text_report(txt, TOP_N, skip_tokens=skip)
        txt_by_key[(det, ver)]   = txt
        write_flamegraph(prof_files, OUTPUT_DIR / f"{det}_{ver}_flamegraph.svg",
                         focus, title="")
        write_callgraph(prof_files, OUTPUT_DIR / f"{det}_{ver}_callgraph.pdf", focus)

    if missing:
        raise FileNotFoundError(
            f"No .prof files found in {PROF_DIR} for: {', '.join(missing)}. "
            f"Run data-gen/Results/Baseline/gperftools.py first."
        )

    written: list[Path] = []
    for det in ("Pixel", "Strip"):
        s1 = funcs_by_key.get((det, "Seeding"), [])
        s2 = funcs_by_key.get((det, "Seeding2"), [])
        if not s1 and not s2:
            raise RuntimeError(
                f"{det}: parsed function lists are empty for both Seeding and "
                f"Seeding2 — pprof report has no rows matching SHOW_FROM filter "
                f"{SHOW_FROM!r}. The .prof files may be empty or the focus "
                f"function names may have changed."
            )
        sections = [("Seeding", s1), ("Seeding2", s2)]
        latex = latex_function_table(f"{det} Detector", sections, TOP_N)
        out = OUTPUT_DIR / f"{det}_comparison.tex"
        out.write_text(latex)
        verify_tex_against_report(out, sections)
        written.append(out)
        print(f"Table saved (verified): {out}")

    print(f"\nDone. Wrote {len(written)} tables.")


if __name__ == "__main__":
    main()
