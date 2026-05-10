#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
import _common  # noqa: F401  --  applies shared rcParams

from heaptrack_summary import ODD_FUNCTIONS, LAST_UPDATED
from heaptrack_table_helper import build_table


OUTPUT_PATH = Path("figures/Results/AlgorithmOptimizations/A1HeaptrackTable.tex")


def main() -> None:
    print(f"Rendering AlgorithmOptimizations heaptrack table from "
          f"figure-gen/heaptrack_summary.py "
          f"(last updated {LAST_UPDATED}, {len(ODD_FUNCTIONS)} functions)")
    table = build_table(
        blocks        = [("", ODD_FUNCTIONS)],
        label_base    = "Cylindrical",
        label_variant = "Spherical",
        ratio_label   = "Spherical / Cylindrical",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(table)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
