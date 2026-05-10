#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
import _common  # noqa: F401

from heaptrack_summary import PIXEL_FUNCTIONS, STRIP_FUNCTIONS, LAST_UPDATED
from heaptrack_table_helper import build_table


OUTPUT_PATH = Path("figures/Results/CodeOptimizations/O4HeaptrackTable.tex")

def main() -> None:
    n = len(PIXEL_FUNCTIONS) + len(STRIP_FUNCTIONS)
    print(f"Rendering CodeOptimizations O4 heaptrack table from "
          f"figure-gen/heaptrack_summary.py (last updated {LAST_UPDATED}, "
          f"{n} entries)")
    table = build_table(
        blocks = [
            ("Pixel", PIXEL_FUNCTIONS),
            ("Strip", STRIP_FUNCTIONS),
        ],
        label_base    = "Baseline",
        label_variant = "O4",
        ratio_label   = "O4 / Baseline",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(table)
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
