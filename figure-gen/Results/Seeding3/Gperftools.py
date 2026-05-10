#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
from gperftools_helper import parse_text_report, latex_function_table

PROF_DIR   = Path("raw-data/Results/Seeding3/Gperftools")
OUTPUT_DIR = Path("figures/Results/Seeding3/Gperftools")

SHOW_FROM = {
    "Seeding":  "SeedingAlgorithm",
    "Seeding2": "GridTripletSeedingAlgorithm",
}
TOP_N = 10


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    skip = tuple(SHOW_FROM.values())

    funcs_by_version: dict[str, list] = {}
    for version in SHOW_FROM:
        txt = PROF_DIR / f"{version}_report.txt"
        if not txt.exists():
            raise FileNotFoundError(
                f"{txt} not found -- run data-gen/Results/Seeding3/gperftools.py "
                f"to produce the symbolized reports (this script no longer calls "
                f"pprof itself; the data step does it while the binary is fresh)."
            )
        funcs_by_version[version] = parse_text_report(txt, TOP_N, skip_tokens=skip)

    s1 = funcs_by_version["Seeding"]
    s2 = funcs_by_version["Seeding2"]
    if not s1 and not s2:
        raise RuntimeError(
            f"Parsed function lists are empty for both Seeding and Seeding2 -- "
            f"the cached text reports have no rows matching SHOW_FROM filter "
            f"{SHOW_FROM!r}. The .prof files may be empty or the focus function "
            f"names may have changed."
        )
    latex = latex_function_table(
        "Function",
        [("Seeding", s1), ("Seeding2", s2)],
        TOP_N,
    )
    out = OUTPUT_DIR / "Seeding_vs_Seeding2_comparison.tex"
    out.write_text(latex)
    print(f"Table saved: {out}")


if __name__ == "__main__":
    main()
