#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")

from codeopts_helpers import load_physics_metrics, SAVE_DIR, save_tex

METRIC_ROWS = [
    ("Efficiency",      "seeding_particle_efficiency"),
    ("Fake ratio",      "seeding_particle_fake_ratio"),
    ("Duplicate ratio", "seeding_particle_duplicate_ratio"),
]


def _fmt(x: float) -> str:
    return f"{x:.5f}"


def _sign_fmt(x: float) -> str:
    sign = "+" if x >= 0 else "-"
    return f"{sign}{abs(x):.5f}"


def build_table(variant: str) -> str:
    baseline = load_physics_metrics("Baseline")
    opt      = load_physics_metrics(variant)

    lines: list[str] = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        rf"Metric & Baseline & {variant} & $\Delta$ \\",
        r"\midrule",
    ]
    zebra = False
    for metric_name, key in METRIC_ROWS:
        b = float(baseline[key])
        o = float(opt[key])
        if zebra:
            lines.append(r"\rowcolor{gray!15}")
        lines.append(
            f"{metric_name} & {_fmt(b)} & {_fmt(o)} & ${_sign_fmt(o - b)}$ \\\\"
        )
        zebra = not zebra
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant", required=True, choices=["O1", "O1-2", "O2", "O3", "O4"],
        help="Optimisation level to compare against the clean Baseline.",
    )
    args = parser.parse_args()

    output = SAVE_DIR / f"{args.variant}PhysicsTable.tex"
    save_tex(output, build_table(args.variant))
    print(f"Saved table to {output}")


if __name__ == "__main__":
    main()
