#!/usr/bin/env python3

import csv
import math
from pathlib import Path

ROOT    = Path(__file__).resolve().parents[3]
CYL_CSV = ROOT / "raw-data/Results/AlgorithmOptimizations/GridStats/CylindricalGridStats.csv"
SPH_CSV = ROOT / "raw-data/Results/AlgorithmOptimizations/GridStats/SphericalGridStats.csv"
OUT_TEX = ROOT / "figures/Results/AlgorithmOptimizations/GridStatsTable.tex"

def parse_vc(s: str) -> dict:
    result = {}
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        v, c = part.split(":")
        result[int(v.strip())] = int(c.strip())
    return result


def diff_vc(prev, curr):
    out = {}
    for k in set(prev) | set(curr):
        d = curr.get(k, 0) - prev.get(k, 0)
        if d > 0:
            out[k] = d
    return out


def read_per_event(csv_path):
    cum = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            name = row["NAME"].strip()
            cum.setdefault(name, []).append({
                "total": int(row["TOTAL"]),
                "count": int(row["COUNT"]),
                "vc":    parse_vc(row["VALUE_COUNT"]),
            })

    per_event = {}
    for name, rows in cum.items():
        events = []
        for i, row in enumerate(rows):
            if i == 0:
                events.append({
                    "total": row["total"],
                    "count": row["count"],
                    "vc":    dict(row["vc"]),
                })
            else:
                prev = rows[i - 1]
                events.append({
                    "total": row["total"] - prev["total"],
                    "count": row["count"] - prev["count"],
                    "vc":    diff_vc(prev["vc"], row["vc"]),
                })
        per_event[name] = events

    n = len(next(iter(per_event.values())))
    print(f"  → {n} events, {len(per_event)} metrics")
    return per_event


def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def aggregate(per_event):
    sp_inserted_ev = per_event["sp_inserted"]
    bin_occ_ev     = per_event["bin_occupancy"]
    seeds_total_ev = per_event["seeds_total"]

    def _mean_over_populated(vc):
        total = sum(v * c for v, c in vc.items())
        populated = sum(c for v, c in vc.items() if v > 0)
        return total / populated if populated else float("nan")

    def _axis_mean(name):
        rows = per_event.get(name)
        if not rows:
            return None
        return _mean([e["total"] for e in rows])

    sps_per_event      = [e["total"]                     for e in sp_inserted_ev]
    populated_per_ev   = [e["count"] - e["vc"].get(0, 0) for e in bin_occ_ev]
    seeds_per_event    = [e["total"]                     for e in seeds_total_ev]
    sps_per_pop_bin_ev = [_mean_over_populated(e["vc"])  for e in bin_occ_ev]

    # Spherical emits grid_eta_bins, Cylindrical emits grid_z_bins.
    phi_mean   = _axis_mean("grid_phi_bins")
    axis2_mean = _axis_mean("grid_eta_bins") or _axis_mean("grid_z_bins")
    r_mean     = _axis_mean("grid_r_bins")

    # Full grid cardinality from per-axis stats; bin_occupancy.count
    # only covers populated bins after the binnedGroup C++ change.
    if phi_mean is not None and axis2_mean is not None and r_mean is not None:
        bins_per_event_mean = phi_mean * axis2_mean * r_mean
    else:
        bins_per_event_mean = _mean([e["count"] for e in bin_occ_ev])

    return {
        "sps_per_event":        _mean(sps_per_event),
        "phi_bins":             phi_mean,
        "axis2_bins":           axis2_mean,
        "r_bins":               r_mean,
        "bins_per_event":       bins_per_event_mean,
        "populated_bins":       _mean(populated_per_ev),
        "mean_sps_per_pop_bin": _mean(sps_per_pop_bin_ev),
        "seeds_per_event":      _mean(seeds_per_event),
        "n_events":             len(sp_inserted_ev),
    }


DASH = r"\textemdash{}"


def _int_cell(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", "{,}")


def _f2(x: float) -> str:
    return DASH if math.isnan(x) else f"{x:.2f}"


def _signed_int(d: int) -> str:
    return f"${d:+,}$".replace(",", "{,}")


def _signed_f2(d: float) -> str:
    return DASH if math.isnan(d) else f"${d:+.2f}$"


def _pct_diff(cyl: float, sph: float, *, decimals: int = 1) -> str:
    if cyl == 0 or math.isnan(cyl) or math.isnan(sph):
        return DASH
    pct = 100.0 * (sph - cyl) / cyl
    return f"${pct:+.{decimals}f}\\%$"


def _row_int(label, c_raw, s_raw):
    if c_raw is None or s_raw is None:
        return (label, DASH, DASH, DASH, DASH)
    c, s = int(round(c_raw)), int(round(s_raw))
    return (label, _int_cell(c), _int_cell(s),
            _signed_int(s - c), _pct_diff(c_raw, s_raw))


def _row_f2(label, c, s):
    if c is None or s is None:
        return (label, DASH, DASH, DASH, DASH)
    return (label, _f2(c), _f2(s),
            _signed_f2(s - c), _pct_diff(c, s))


def build_tabular(cyl_ev: dict, sph_ev: dict) -> str:
    c = aggregate(cyl_ev)
    s = aggregate(sph_ev)

    rows = [
        _row_int("Space points / event",       c["sps_per_event"],       s["sps_per_event"]),
        _row_int(r"$\phi$ bins",               c["phi_bins"],            s["phi_bins"]),
        _row_int(r"$\eta$ / $z$ bins",         c["axis2_bins"],          s["axis2_bins"]),
        _row_int("$r$ bins",                   c["r_bins"],              s["r_bins"]),
        _row_int("Bins / event",               c["bins_per_event"],      s["bins_per_event"]),
        _row_int("Populated bins / event",     c["populated_bins"],      s["populated_bins"]),
        _row_f2 ("Mean SPs per populated bin", c["mean_sps_per_pop_bin"], s["mean_sps_per_pop_bin"]),
        _row_int("Seeds / event",              c["seeds_per_event"],     s["seeds_per_event"]),
    ]

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\begin{tabular}{lrrrr}",
        r"    \toprule",
        (r"    \textbf{Metric (per event)}"
         r" & \textbf{Cylindrical}"
         r" & \textbf{Spherical}"
         r" & \textbf{Abs.\ diff.}"
         r" & \textbf{\% diff.} \\"),
        r"    \midrule",
    ]
    for i, (label, cv, sv, abs_diff, pct_diff) in enumerate(rows):
        if i % 2 == 0:
            lines.append(r"    \rowcolor{gray!15}")
        lines.append(rf"    {label} & {cv} & {sv} & {abs_diff} & {pct_diff} \\")
    lines += [
        r"    \bottomrule",
        r"\end{tabular}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    print(f"Reading Cylindrical:\n  {CYL_CSV}")
    cyl_ev = read_per_event(CYL_CSV)

    print(f"Reading Spherical:\n  {SPH_CSV}")
    sph_ev = read_per_event(SPH_CSV)

    tabular = build_tabular(cyl_ev, sph_ev)

    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.write_text(tabular)
    print(f"\nWritten to:\n  {OUT_TEX}")


if __name__ == "__main__":
    main()
