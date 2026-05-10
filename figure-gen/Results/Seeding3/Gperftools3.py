#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
from gperftools_helper import parse_text_report, latex_function_table

PROF_DIR   = Path("raw-data/Results/Seeding3/Gperftools")
OUTPUT_DIR = Path("figures/Results/Seeding3/Gperftools")

SHOW_FROM = {
    "Seeding2": "GridTripletSeedingAlgorithm",
    "Seeding3": "SphericalGridTripletSeedingAlgorithm",
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
                f"{txt} not found -- run the relevant data-gen script: "
                f"data-gen/Results/Seeding3/gperftools.py for Seeding2, "
                f"data-gen/Results/Seeding3/gperftoolsSeeding3.py for Seeding3."
            )
        funcs_by_version[version] = parse_text_report(txt, TOP_N, skip_tokens=skip)

    s2 = funcs_by_version["Seeding2"]
    s3 = funcs_by_version["Seeding3"]
    if not s2 and not s3:
        raise RuntimeError(
            f"Parsed function lists are empty for both Seeding2 and Seeding3 -- "
            f"the cached text reports have no rows matching SHOW_FROM filter "
            f"{SHOW_FROM!r}."
        )
    latex = latex_function_table(
        "Function",
        [("Seeding2", s2), ("Seeding3", s3)],
        TOP_N,
    )
    out = OUTPUT_DIR / "Seeding2_vs_Seeding3_comparison.tex"
    out.write_text(latex)
    print(f"Table saved: {out}")


if __name__ == "__main__":
    main()
