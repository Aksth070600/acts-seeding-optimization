#!/usr/bin/env python3

import pandas as pd
from pathlib import Path

baseline_path = Path("raw-data/Results/AlgorithmOptimizations/ParameterOptimization/Baseline/ParamOptimizationMetrics.csv")
data_path = Path("raw-data/Results/AlgorithmOptimizations/PhysicsValidation/ParamOptimizationMetrics.csv")

output_path = Path("figures/Results/AlgorithmOptimizations/PhysicsTable.tex")

baseline = pd.read_csv(baseline_path).iloc[0]
data = pd.read_csv(data_path).iloc[0]


def fmt(x: float) -> str:
    return f"{x:.5f}"


def delta(a: float, b: float) -> float:
    return b - a


def sign_fmt(x: float) -> str:
    sign = "+" if x >= 0 else "-"
    return f"{sign}{abs(x):.5f}"


def row(metric_name: str, key: str, zebra: bool) -> str:
    b = float(baseline[key])
    o = float(data[key])
    d = delta(b, o)

    prefix = "\\rowcolor{gray!15}\n" if zebra else ""
    return prefix + (
        f"{metric_name} & {fmt(b)} & {fmt(o)} & ${sign_fmt(d)}$ \\\\"
    )


table = r"""\renewcommand{\arraystretch}{1.4}
\begin{tabular}{lccc}
\toprule
Metric & Cylindrical & Spherical & $\Delta$ \\
\midrule
"""

table += row("Efficiency",      "seeding_particle_efficiency",      zebra=False) + "\n"
table += row("Fake ratio",      "seeding_particle_fake_ratio",      zebra=True ) + "\n"
table += row("Duplicate ratio", "seeding_particle_duplicate_ratio", zebra=False) + "\n"

table += r"""\bottomrule
\end{tabular}
"""

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(table)

print(f"Saved table to {output_path}")
