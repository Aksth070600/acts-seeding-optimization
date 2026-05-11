#!/usr/bin/env python3

import math
from pathlib import Path

RAW_DIR = Path("raw-data/Results/Baseline/Workload")
SAVE_DIR = Path("figures/Results/Baseline/Workload")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

METHODS     = ["Seeding", "Seeding2"]
GEOMS       = ["Pixel", "Strip"]
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


def load_stats(geom: str, method: str) -> dict:
    path = RAW_DIR / f"{geom}Workload{method}.csv"
    return add_derived_fields(parse_stats_csv(path))

MISSING = r"---"

def _nan(v: float) -> bool:
    return isinstance(v, float) and math.isnan(v)


def fi(v: float) -> str:
    if _nan(v):
        return MISSING
    return f"{int(round(v)):,}".replace(",", "{,}")


def ff(v: float, d: int = 2) -> str:
    return MISSING if _nan(v) else f"{v:.{d}f}"


def fmt_rel_diff(v1: float, v2: float) -> str:
    if _nan(v1) or _nan(v2) or v1 == 0:
        return MISSING
    pct = (v2 - v1) / v1 * 100
    if pct > 0:
        return rf"$+{pct:.1f}\%$"
    elif pct < 0:
        return rf"${pct:.1f}\%$"
    else:
        return rf"$\phantom{{-}}0.0\%$"

def get(stats: dict, name: str, field: str = 'mean') -> float:
    if name not in stats:
        return float('nan')
    return float(stats[name][field])


def total_bins_per_event(stats: dict) -> float:
    phi   = stats.get('grid_phi_bins', {}).get('mean')
    axis2 = (stats.get('grid_z_bins', {}).get('mean')
             or stats.get('grid_eta_bins', {}).get('mean'))
    r     = stats.get('grid_r_bins', {}).get('mean')
    if phi and axis2 and r:
        return phi * axis2 * r
    return get(stats, 'num_bins', 'count_per_event')


def empty_bins_pct(stats: dict) -> float:
    total = total_bins_per_event(stats)
    occupied = get(stats, 'occupied_bins', 'count_per_event')
    if _nan(total) or _nan(occupied) or total == 0:
        return float('nan')
    return (1.0 - occupied / total) * 100.0


STAGES = [
    ("Grid", [
        ("Total bins",                total_bins_per_event,                                       fi),
        ("Occupied bins",             lambda s: get(s, 'occupied_bins', 'count_per_event'),       fi),
        (r"Empty bins [\%]",          empty_bins_pct,                                             lambda v: ff(v, 2)),
        ("Mean SPs per occupied bin", lambda s: get(s, 'sp_per_bin', 'total_per_occupied'),       lambda v: ff(v, 2)),
    ]),
    ("Doublets", [
        ("Bottom candidates",         lambda s: get(s, 'bottom_candidates', 'total_per_event'),   fi),
        ("Top candidates",            lambda s: get(s, 'top_candidates', 'total_per_event'),      fi),
    ]),
    ("Triplets", [
        ("Created triplets",          lambda s: get(s, 'triplets_evaluated', 'total_per_event'),  fi),
    ]),
    ("Output", [
        ("Total seeds",               lambda s: get(s, 'total_seeds', 'total_per_event'),         fi),
    ]),
]


def build_geometry_rows(s1: dict, s2: dict, start_zebra: bool = False) -> list[str]:
    rows = []
    zebra = start_zebra

    for stage_label, metrics in STAGES:
        for i, (metric, value_fn, fmt_val) in enumerate(metrics):
            v1 = value_fn(s1)
            v2 = value_fn(s2)

            stage_cell = stage_label if i == 0 else ""

            if zebra:
                rows.append(r"\rowcolor{gray!15}")

            rows.append(
                f"{stage_cell} & {metric} & {fmt_val(v1)} & {fmt_val(v2)}"
                f" & {fmt_rel_diff(v1, v2)} \\\\"
            )

            zebra = not zebra

    return rows


def build_table(all_stats: dict) -> str:
    L = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        (r"\textbf{Stage} & \textbf{Metric}"
         r" & \textbf{\texttt{Seeding}} & \textbf{\texttt{Seeding2}}"
         r" & \textbf{Rel.\ diff.} \\"),
        r"\midrule",
    ]

    for gi, geom in enumerate(GEOMS):
        s1 = all_stats[geom]["Seeding"]
        s2 = all_stats[geom]["Seeding2"]
        glabel = "Pixel detector" if geom == "Pixel" else "Strip detector"

        L.append(r"\rowcolor{gray!25}")
        L.append(rf"\multicolumn{{5}}{{l}}{{\textbf{{{glabel}}}}} \\")

        L.extend(build_geometry_rows(s1, s2, start_zebra=False))

        if gi < len(GEOMS) - 1:
            L.append(r"\midrule")

    L += [
        r"\bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]

    return "\n".join(L)


def main():
    all_stats = {
        geom: {method: load_stats(geom, method) for method in METHODS}
        for geom in GEOMS
    }

    latex = build_table(all_stats)
    OUTPUT_FILE.write_text(latex)
    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
