#!/usr/bin/env python3

from __future__ import annotations

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

sys.path.insert(0, "figure-gen")
import _common
from waterfall_helper import (
    extract_stages,
    parse_waterfall_csv,
    plot_waterfall_on_axis,
    print_stage_summary,
)

RAW_DIR  = Path("raw-data/Results/Seeding3/Waterfall")
SAVE_DIR = Path("figures/Results/Seeding3/Waterfall")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

METHODS = ["Seeding", "Seeding2", "Seeding3"]

COMPARISONS: list[tuple[str, str, str]] = [
    ("Seeding2", "Seeding3", "Seeding2 vs Seeding3 (this thesis)"),
    ("Seeding",  "Seeding3", "Seeding vs Seeding3 (aggregate)"),
]

STAGES = [
    "Seeding",          
    "GridSetup",
    "ConvProxSeeds",
    "createSeedsGroup", 
    "MiddleTops",
    "MiddleBottoms",
    "TripletEvaluation",
    "SeedFiltering",
]

STAGE_LABELS = {
    "Seeding":            "Seeding (other)",
    "GridSetup":          "GridSetup",
    "ConvProxSeeds":      "ConvertProxSeeds",
    "createSeedsGroup":   "createSeedsGroup",
    "MiddleTops":         "MiddleTops",
    "MiddleBottoms":      "MiddleBottoms",
    "TripletEvaluation":  "TripletEval",
    "SeedFiltering":      "SeedFiltering",
}

_COMMON_TIMERS = {
    "total":             ["Seeding"],
    "GridSetup":         ["Seeding-GridSetup"],
    "ConvProxSeeds":     ["Seeding-ConProxSeeds"],
    "createSeedsGroup":  ["Seeding-createSeedsFromGroups"],
    "MiddleTops":        ["Seeding-createSeedsFromGroups-MiddleTops"],
    "MiddleBottoms":     ["Seeding-createSeedsFromGroups-MiddleBottoms"],
    "TripletEvaluation": ["Seeding-createSeedsFromGroups-TripletEvaluation"],
    "SeedFiltering":     ["Seeding-createSeedsFromGroups-SeedFiltering"],
}

STAGE_TIMERS: dict[str, dict[str, list[str]]] = {
    "Seeding": {
        **_COMMON_TIMERS,
        "SeedFiltering": [
            "Seeding-createSeedsFromGroups-SeedFiltering",
            "SeedFiltering",
        ],
    },
    "Seeding2": _COMMON_TIMERS,
    "Seeding3": _COMMON_TIMERS,
}

GROUP_CHILDREN = ["MiddleTops", "MiddleBottoms", "TripletEvaluation", "SeedFiltering"]

LEGEND_ELEMENTS = [
    mpatches.Patch(facecolor="#4472C4", edgecolor="black", label="Baseline"),
    mpatches.Patch(facecolor="#51CF66", edgecolor="black", label="Seeding3 faster"),
    mpatches.Patch(facecolor="#FF6B6B", edgecolor="black", label="Seeding3 slower"),
    mpatches.Patch(facecolor="#1F4E79", edgecolor="black", label="Seeding3 (final)"),
]

def _log_speedup(label: str, stats: dict) -> None:
    sp = stats["speedup"]
    if sp["ratio"] >= 1.0:
        print(f"  [{label}] Speedup:  {sp['ratio']:.3f}x "
              f"[{sp['ci_low']:.3f}x, {sp['ci_high']:.3f}x]")
    else:
        slowdown = 1.0 / sp["ratio"]
        print(f"  [{label}] Slowdown: {slowdown:.3f}x "
              f"[{1/sp['ci_high']:.3f}x, {1/sp['ci_low']:.3f}x]")

def main() -> None:
    print("=" * 70)
    print("Creating Seeding3 Waterfall Graphs")
    print("=" * 70 + "\n")

    loaded: dict[str, dict] = {}

    for method in METHODS:
        path = RAW_DIR / f"Waterfall{method}.csv"
        try:
            raw = parse_waterfall_csv(path)
        except (FileNotFoundError, ValueError) as exc:
            print(f"  WARNING: {exc}")
            continue

        loaded[method] = extract_stages(
            raw,
            stage_timers   = STAGE_TIMERS[method],
            group_children = GROUP_CHILDREN,
            residual_stage = "Seeding",
        )
        n_ev    = len(raw.get("Seeding", []))
        mean_ms = loaded[method]["total"].mean() / 1e6
        print(f"  {method:10s}: {n_ev} events, "
              f"mean execute = {mean_ms:.1f} ms/event")

    print()

    panels: list[tuple[str, str, str]] = [
        (m1, m2, title)
        for (m1, m2, title) in COMPARISONS
        if m1 in loaded and m2 in loaded
    ]

    if not panels:
        print("No data loaded for any comparison -- exiting.")
        return

    for m1, m2, title in panels:
        print(f"{m1} vs {m2}")
        print_stage_summary(
            loaded[m1], loaded[m2],
            STAGES, method1=m1, method2=m2,
        )
        print()

    n_panels = len(panels)
    fig, axes = plt.subplots(n_panels, 1, figsize=(7.5, 3.2 * n_panels), sharey=True)

    if n_panels == 1:
        axes = [axes]

    for ax, (m1, m2, title) in zip(axes, panels):
        stats = plot_waterfall_on_axis(
            ax,
            s1            = loaded[m1],
            s2            = loaded[m2],
            stages        = STAGES,
            stage_labels  = STAGE_LABELS,
            method1       = m1,
            method2       = m2,
        )
        _log_speedup(f"{m1} vs {m2}", stats)

    fig.legend(
        handles=LEGEND_ELEMENTS,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.04),
        ncol=4,
        fontsize=11,
        edgecolor="black",
        framealpha=0.9,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.92], h_pad=3.0)

    out = SAVE_DIR / "WaterfallSeeding3.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved --> {out}")

    print("\n" + "=" * 70)
    print("Waterfall graph created successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
