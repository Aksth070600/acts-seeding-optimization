#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "data-gen")
from workflow import default_runs  # noqa: E402

RAW_DIR  = Path("raw-data/Results/Baseline/StageTiming")
SAVE_DIR = Path("figures/Results/Detailed/StageTiming")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

DETECTORS = ["Pixel", "Strip"]
N_RUNS    = default_runs()

TOP_LEVEL_STAGES: list[str] = [
    "Seeding",
    "GridSetup",
    "ConProxSeeds",
    "createSeedsGroup",
]

HOTSPOT_STAGES: list[str] = [
    "MiddleTops",
    "MiddleBottoms",
    "TripletEvaluation",
    "SeedFiltering",
]

STAGES: list[str] = TOP_LEVEL_STAGES + HOTSPOT_STAGES

STAGE_LABELS: dict[str, str] = {
    "Seeding":           r"Seeding",
    "GridSetup":         r"GridSetup",
    "ConProxSeeds":      r"ConvertProxSeeds",
    "createSeedsGroup":  r"createSeedsGroup",
    "MiddleTops":        r"MiddleTops",
    "MiddleBottoms":     r"MiddleBottoms",
    "TripletEvaluation": r"TripletEval",
    "SeedFiltering":     r"SeedFiltering",
}

TIMER_NAMES: dict[str, str] = {
    "Seeding":           "Seeding",
    "GridSetup":         "Seeding-GridSetup",
    "ConProxSeeds":      "Seeding-ConProxSeeds",
    "createSeedsGroup":  "Seeding-createSeedsFromGroups",
    "MiddleTops":        "Seeding-createSeedsFromGroups-MiddleTops",
    "MiddleBottoms":     "Seeding-createSeedsFromGroups-MiddleBottoms",
    "TripletEvaluation": "Seeding-createSeedsFromGroups-TripletEvaluation",
    "SeedFiltering":     "Seeding-createSeedsFromGroups-SeedFiltering",
}

# Inclusive children subtracted to get exclusive time.
CHILDREN: dict[str, list[str]] = {
    "Seeding":          ["GridSetup", "ConProxSeeds", "createSeedsGroup"],
    "createSeedsGroup": ["MiddleTops", "MiddleBottoms", "TripletEvaluation",
                         "SeedFiltering"],
}

# Stages with high per-event call-count variance, prefixed with \approx.
APPROX_CALLS: set[str] = {
    "MiddleTops", "MiddleBottoms", "TripletEvaluation", "SeedFiltering"
}


def load_last_row_per_stage(path: Path) -> dict[str, dict[str, float]]:
    df = pd.read_csv(path)
    result: dict[str, dict[str, float]] = {}
    for name, grp in df.groupby("NAME", sort=False):
        row = grp.loc[grp["COUNT"].idxmax()]
        result[str(name)] = {
            "time_ns": float(row["TIME_NS"]),
            "count":   float(row["COUNT"]),
        }
    return result


def load_detector_runs(detector: str) -> list[dict[str, dict[str, float]]]:
    runs: list[dict] = []
    for i in range(1, N_RUNS + 1):
        path = RAW_DIR / f"{detector}Seeding2_run{i}.csv"
        # data-gen may force Runs=1 (bare name) even when global runs > 1.
        if not path.exists():
            path = RAW_DIR / f"{detector}Seeding2.csv"
        if not path.exists():
            print(f"  WARNING: {path} not found – skipping run {i}.")
            continue
        runs.append(load_last_row_per_stage(path))
        print(f"  Loaded  {path.name}")
    return runs


StageStats = dict[str, dict[str, float]]


def compute_exclusive_ns(raw: dict[str, dict[str, float]], stage: str) -> float:
    inclusive = raw[TIMER_NAMES[stage]]["time_ns"]
    children_sum = sum(
        raw[TIMER_NAMES[child]]["time_ns"]
        for child in CHILDREN.get(stage, [])
    )
    return inclusive - children_sum


def compute_stats(
    runs: list[dict[str, dict[str, float]]],
    stages: list[str],
) -> StageStats:
    accum: dict[str, dict[str, list[float]]] = {
        s: {"pct": [], "ms_per_ev": [], "calls_ev": []} for s in stages
    }

    for raw in runs:
        total_ns = raw["Seeding"]["time_ns"]
        n_events = raw["Seeding"]["count"]

        for stage in stages:
            excl_ns  = compute_exclusive_ns(raw, stage)
            incl_cnt = raw[TIMER_NAMES[stage]]["count"]
            accum[stage]["pct"].append(excl_ns / total_ns * 100.0)
            accum[stage]["ms_per_ev"].append(excl_ns / n_events / 1e6)
            accum[stage]["calls_ev"].append(incl_cnt / n_events)

    out: StageStats = {}
    for stage in stages:
        pct   = np.asarray(accum[stage]["pct"])
        ms    = np.asarray(accum[stage]["ms_per_ev"])
        calls = np.asarray(accum[stage]["calls_ev"])
        out[stage] = {
            "pct_mean":    float(pct.mean())        if pct.size   else float("nan"),
            "pct_std":     float(pct.std(ddof=1))   if pct.size > 1 else 0.0,
            "ms_mean":     float(ms.mean())         if ms.size    else float("nan"),
            "ms_std":      float(ms.std(ddof=1))    if ms.size > 1 else 0.0,
            "calls_mean":  float(calls.mean())      if calls.size else float("nan"),
        }
    return out


def fmt_pct(mean: float, std: float) -> str:
    return rf"${mean:.1f} \pm {std:.1f}$"


def fmt_ms(mean: float, std: float) -> str:
    if mean >= 10:
        return rf"${mean:.1f} \pm {std:.1f}$"
    else:
        return rf"${mean:.2f} \pm {std:.2f}$"


def fmt_calls(mean: float, approx: bool = False) -> str:
    if mean >= 10_000:
        val = f"{mean:,.0f}".replace(",", "{,}")
    elif mean >= 100:
        val = f"{mean:.0f}"
    elif mean >= 1:
        val = f"{mean:.0f}"
    else:
        val = f"{mean:.3f}"
    return (rf"$\approx$\,{val}") if approx else val


def build_tabular(
    pixel_stats: StageStats,
    strip_stats: StageStats,
    top_level: list[str],
    hotspots: list[str],
) -> str:
    lines: list[str] = []

    lines += [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{l rrr rrr}",
        r"    \toprule",
        (
            r"     & \multicolumn{3}{c}{\textbf{Pixel detector}}"
            r" & \multicolumn{3}{c}{\textbf{Strip detector}} \\"
        ),
        r"    \cmidrule(lr){2-4} \cmidrule(lr){5-7}",
        (
            r"    \textbf{Stage}"
            r" & \textbf{Excl.\ time} & \textbf{Time/evt} & \textbf{Calls/evt}"
            r" & \textbf{Excl.\ time} & \textbf{Time/evt} & \textbf{Calls/evt} \\"
        ),
        (
            r"     & [\%] & [ms] &"
            r" & [\%] & [ms] & \\"
        ),
        r"    \midrule",
    ]

    def emit_rows(stages: list[str], start_zebra: bool) -> None:
        zebra = start_zebra
        for stage in stages:
            label   = STAGE_LABELS.get(stage, stage)
            approx  = stage in APPROX_CALLS

            p = pixel_stats[stage]
            s = strip_stats[stage]

            if zebra:
                lines.append(r"    \rowcolor{gray!15}")

            lines.append(
                rf"    {label}"
                rf" & {fmt_pct(p['pct_mean'], p['pct_std'])}"
                rf" & {fmt_ms(p['ms_mean'], p['ms_std'])}"
                rf" & {fmt_calls(p['calls_mean'], approx)}"
                rf" & {fmt_pct(s['pct_mean'], s['pct_std'])}"
                rf" & {fmt_ms(s['ms_mean'], s['ms_std'])}"
                rf" & {fmt_calls(s['calls_mean'], approx)}"
                rf" \\"
            )

            zebra = not zebra

    lines.append(r"    \rowcolor{gray!25}")
    lines.append(r"    \multicolumn{7}{l}{\textbf{Top-level dispatch}} \\")
    emit_rows(top_level, start_zebra=False)

    lines.append(r"    \rowcolor{gray!25}")
    lines.append(r"    \multicolumn{7}{l}{\textbf{Inner-loop hotspots}} \\")
    emit_rows(hotspots, start_zebra=False)

    lines += [
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
    ]

    return "\n".join(lines)


def print_summary(detector: str, stats: StageStats, stages: list[str]) -> None:
    print(f"\n  {'Stage':<25} {'Excl. [%]':>14} {'Time/evt [ms]':>18} {'Calls/ev':>12}")
    print(f"  {'-' * 72}")
    for stage in stages:
        s = stats[stage]
        label = STAGE_LABELS.get(stage, stage)
        print(
            f"  {label:<25}"
            f" {s['pct_mean']:12.2f} %"
            f" {s['ms_mean']:14.2f} ± {s['ms_std']:.2f}"
            f" {s['calls_mean']:12.2f}"
        )


def main() -> None:
    print("=" * 72)
    print("Generating combined LaTeX timing breakdown table (exclusive times)")
    print("=" * 72)

    all_stats: dict[str, StageStats] = {}

    for detector in DETECTORS:
        print(f"\n[{detector} Detector]")
        runs = load_detector_runs(detector)
        if not runs:
            print("  No data found – skipping.")
            continue
        stats = compute_stats(runs, STAGES)
        all_stats[detector] = stats
        print_summary(detector, stats, STAGES)

    print()

    if not all(d in all_stats for d in DETECTORS):
        missing = [d for d in DETECTORS if d not in all_stats]
        print(f"ERROR: missing data for {missing}. Cannot build combined table.")
        return

    tabular = build_tabular(
        all_stats["Pixel"], all_stats["Strip"],
        TOP_LEVEL_STAGES, HOTSPOT_STAGES,
    )

    out_path = SAVE_DIR / "timing_table.tex"
    out_path.write_text(tabular + "\n", encoding="utf-8")

    print("=" * 72)
    print(f"Saved --> {out_path}")
    print(f"Include with: \\input{{Figures/Results/StageTiming/timing_table}}")
    print("=" * 72)


if __name__ == "__main__":
    main()
