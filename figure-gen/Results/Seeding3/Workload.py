#!/usr/bin/env python3

import math
from pathlib import Path

RAW_DIR = Path("raw-data/Results/Seeding3/Workload")
SAVE_DIR = Path("figures/Results/Seeding3/Workload")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

METHODS     = ["Seeding2", "Seeding3"]
OUTPUT_FILE = SAVE_DIR / "WorkloadTable.tex"


def parse_stats_csv(path: Path) -> dict:
    stats = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',', 4)
            if len(parts) < 3:
                continue
            name = parts[0].strip()
            try:
                total = int(parts[1])
                count = int(parts[2])
            except ValueError:
                continue
            stats[name] = {
                'total': total,
                'count': count,
                'mean':  total / count if count > 0 else 0.0,
            }
    return stats


def add_derived_fields(stats: dict) -> dict:
    # total_seeds is emitted exactly once per event, so its count = n_events.
    n_events = stats.get('total_seeds', {}).get('count', 0)
    occupied = stats.get('occupied_bins', {}).get('count', 0)

    for m in stats.values():
        if n_events > 0:
            m['count_per_event'] = m['count'] / n_events
            m['total_per_event'] = m['total'] / n_events
        else:
            m['count_per_event'] = float('nan')
            m['total_per_event'] = float('nan')

    if 'sp_per_bin' in stats:
        sp = stats['sp_per_bin']
        sp['total_per_occupied'] = (
            sp['total'] / occupied if occupied > 0 else float('nan')
        )
    return stats


def load_stats(method: str) -> dict:
    path = RAW_DIR / f"Workload{method}.csv"
    return add_derived_fields(parse_stats_csv(path))

MISSING = r"\text{--}"

def _nan(v: float) -> bool:
    return isinstance(v, float) and math.isnan(v)

def fi(v: float) -> str:
    if _nan(v):
        return MISSING
    return rf"${int(round(v)):,}$".replace(",", r"\,")

def ff(v: float, d: int = 2) -> str:
    if _nan(v):
        return MISSING
    return rf"${v:.{d}f}$"

def fmt_rel_diff(v1: float, v2: float) -> str:
    if _nan(v1) or _nan(v2) or v1 == 0:
        return MISSING
    pct = (v2 - v1) / v1 * 100
    if abs(pct) < 0.05:
        return r"$\phantom{-}0.0\%$"
    sign = "+" if pct >= 0 else ""
    if sign == "+":
        return rf"${sign}{pct:.1f}\%$"
    return rf"${pct:.1f}\%$"

def get(stats: dict, name: str, field: str = 'mean') -> float:
    if name not in stats:
        return float('nan')
    return float(stats[name][field])


def total_bins_per_event(stats: dict) -> float:
    # Full grid cardinality (nPhi * nAxis2 * nR) from per-axis STATS counters.
    # Falls back to num_bins.count_per_event for CSVs missing those counters.
    phi   = stats.get('grid_phi_bins', {}).get('mean')
    axis2 = (stats.get('grid_z_bins', {}).get('mean')
             or stats.get('grid_eta_bins', {}).get('mean'))
    r     = stats.get('grid_r_bins', {}).get('mean')
    if phi and axis2 and r:
        return phi * axis2 * r
    return get(stats, 'num_bins', 'count_per_event')


def axis2_bins(stats: dict) -> float:
    v = (stats.get('grid_z_bins', {}).get('mean')
         or stats.get('grid_eta_bins', {}).get('mean'))
    return float(v) if v else float('nan')


def empty_bins_pct(stats: dict) -> float:
    total = total_bins_per_event(stats)
    occupied = get(stats, 'occupied_bins', 'count_per_event')
    if _nan(total) or _nan(occupied) or total == 0:
        return float('nan')
    return (1.0 - occupied / total) * 100.0


def data_row(
    stage: str,
    metric: str,
    v1: float,
    v2: float,
    fmt_val,
    zebra: bool,
) -> str:
    rel_diff = fmt_rel_diff(v1, v2)
    prefix = r"    \rowcolor{gray!15}" + "\n    " if zebra else "    "
    return (
        rf"{prefix}{stage} & {metric} & {fmt_val(v1)} & {fmt_val(v2)}"
        rf" & {rel_diff} \\"
    )


def build_rows(s2: dict, s3: dict) -> list[str]:
    entries = [
        ("Grid",
         "Total bins",
         total_bins_per_event(s2),
         total_bins_per_event(s3),
         fi),
        (None,
         r"$n_\phi$ bins",
         get(s2, 'grid_phi_bins', 'mean'),
         get(s3, 'grid_phi_bins', 'mean'),
         fi),
        (None,
         r"$n_{z/\eta}$ bins",
         axis2_bins(s2),
         axis2_bins(s3),
         fi),
        (None,
         r"$n_r$ bins",
         get(s2, 'grid_r_bins', 'mean'),
         get(s3, 'grid_r_bins', 'mean'),
         fi),
        (None,
         "Occupied bins",
         get(s2, 'occupied_bins', 'count_per_event'),
         get(s3, 'occupied_bins', 'count_per_event'),
         fi),
        (None,
         r"Empty bins [\%]",
         empty_bins_pct(s2),
         empty_bins_pct(s3),
         lambda v: ff(v, 2)),
        (None,
         "Mean SPs per occupied bin",
         get(s2, 'sp_per_bin', 'total_per_occupied'),
         get(s3, 'sp_per_bin', 'total_per_occupied'),
         lambda v: ff(v, 2)),

        ("Doublets",
         "Bottom doublet candidates",
         get(s2, 'bottom_candidates', 'total_per_event'),
         get(s3, 'bottom_candidates', 'total_per_event'),
         fi),
        (None,
         "Top doublet candidates",
         get(s2, 'top_candidates', 'total_per_event'),
         get(s3, 'top_candidates', 'total_per_event'),
         fi),

        ("Triplets",
         "Created triplets",
         get(s2, 'triplets_evaluated', 'total_per_event'),
         get(s3, 'triplets_evaluated', 'total_per_event'),
         fi),

        ("Output",
         "Total seeds",
         get(s2, 'total_seeds', 'total_per_event'),
         get(s3, 'total_seeds', 'total_per_event'),
         fi),
    ]

    rows = []
    for idx, (stage, metric, v1, v2, fmt_val) in enumerate(entries):
        stage_cell = stage if stage else ""
        rows.append(
            data_row(stage_cell, metric, v1, v2, fmt_val, zebra=(idx % 2 == 1))
        )
    return rows


def build_table(all_stats: dict) -> str:
    s2 = all_stats["Seeding2"]
    s3 = all_stats["Seeding3"]

    L = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"    \toprule",
        (
            r"    \textbf{Stage} & \textbf{Metric}"
            r" & \textbf{\texttt{Seeding2}} & \textbf{\texttt{Seeding3}}"
            r" & \textbf{Rel.\ diff.} \\"
        ),
        r"    \midrule",
    ]

    L.extend(build_rows(s2, s3))

    L += [
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]
    return "\n".join(L)


def main():
    all_stats = {method: load_stats(method) for method in METHODS}
    latex = build_table(all_stats)
    OUTPUT_FILE.write_text(latex)
    print(f"Written to {OUTPUT_FILE}")
    print()
    print(latex)


if __name__ == "__main__":
    main()
