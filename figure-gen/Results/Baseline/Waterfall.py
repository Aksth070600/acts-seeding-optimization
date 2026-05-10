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

RAW_DIR  = Path("raw-data/Results/Baseline/StageTiming")
SAVE_DIR = Path("figures/Results/Baseline/Waterfall")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

DETECTORS = ["Pixel", "Strip"]
METHODS   = ["Seeding", "Seeding2"]

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

STAGE_TIMERS: dict[str, dict[str, list[str]]] = {
    "Seeding": {
        "total":             ["Seeding"],
        "GridSetup":         ["Seeding-GridSetup"],
        "ConvProxSeeds":     ["Seeding-ConProxSeeds"],
        "createSeedsGroup":  ["Seeding-createSeedsFromGroups"],
        "MiddleTops":        ["Seeding-createSeedsFromGroups-MiddleTops"],
        "MiddleBottoms":     ["Seeding-createSeedsFromGroups-MiddleBottoms"],
        "TripletEvaluation": ["Seeding-createSeedsFromGroups-TripletEvaluation"],
        "SeedFiltering":     ["Seeding-createSeedsFromGroups-SeedFiltering",
                              "SeedFiltering"],
    },
    "Seeding2": {
        "total":             ["Seeding"],
        "GridSetup":         ["Seeding-GridSetup"],
        "ConvProxSeeds":     ["Seeding-ConProxSeeds"],
        "createSeedsGroup":  ["Seeding-createSeedsFromGroups"],
        "MiddleTops":        ["Seeding-createSeedsFromGroups-MiddleTops"],
        "MiddleBottoms":     ["Seeding-createSeedsFromGroups-MiddleBottoms"],
        "TripletEvaluation": ["Seeding-createSeedsFromGroups-TripletEvaluation"],
        "SeedFiltering":     ["Seeding-createSeedsFromGroups-SeedFiltering"],
    },
}

GROUP_CHILDREN = ["MiddleTops", "MiddleBottoms", "TripletEvaluation", "SeedFiltering"]

LEGEND_ELEMENTS = [
    mpatches.Patch(facecolor="#4472C4", edgecolor="black", label="Seeding (baseline)"),
    mpatches.Patch(facecolor="#51CF66", edgecolor="black", label="Seeding2 faster"),
    mpatches.Patch(facecolor="#FF6B6B", edgecolor="black", label="Seeding2 slower"),
    mpatches.Patch(facecolor="#1F4E79", edgecolor="black", label="Seeding2 (final)"),
]

def main() -> None:
    print("=" * 70)
    print("Creating Waterfall Graphs: Seeding vs Seeding2")
    print("=" * 70 + "\n")

    all_stages: dict[str, dict[str, dict]] = {}

    for detector in DETECTORS:
        print(f"[{detector}]")
        det_stages: dict[str, dict] = {}

        for method in METHODS:
            path = RAW_DIR / f"{detector}{method}_run1.csv"
            if not path.exists():
                path = RAW_DIR / f"{detector}{method}.csv"
            try:
                raw = parse_waterfall_csv(path)
            except (FileNotFoundError, ValueError) as exc:
                print(f"  WARNING: {exc}")
                continue

            det_stages[method] = extract_stages(
                raw,
                stage_timers   = STAGE_TIMERS[method],
                group_children = GROUP_CHILDREN,
                residual_stage = "Seeding",
            )
            n_ev    = len(raw.get("Seeding", []))
            mean_ms = det_stages[method]["total"].mean() / 1e6
            print(f"  {method:10s}: {n_ev} events, "
                  f"mean execute = {mean_ms:.1f} ms/event")

        if not all(m in det_stages for m in METHODS):
            print(f"  Skipping {detector}: missing data.\n")
            continue

        print()
        print_stage_summary(
            det_stages["Seeding"], det_stages["Seeding2"],
            STAGES, method1="Seeding", method2="Seeding2",
        )

        all_stages[detector] = det_stages

    if not all_stages:
        print("No data loaded for any detector -- exiting.")
        return

    n_panels = len(all_stages)
    fig, axes = plt.subplots(n_panels, 1, figsize=(7.5, 3.2 * n_panels), sharey=True)

    if n_panels == 1:
        axes = [axes]

    for ax, (detector, det_stages) in zip(axes, all_stages.items()):
        stats = plot_waterfall_on_axis(
            ax,
            s1            = det_stages["Seeding"],
            s2            = det_stages["Seeding2"],
            stages        = STAGES,
            stage_labels  = STAGE_LABELS,
            method1       = "Seeding",
            method2       = "Seeding2",
        )

        sp = stats["speedup"]
        if sp["ratio"] >= 1.0:
            print(f"  [{detector}] Speedup:  {sp['ratio']:.3f}x "
                  f"[{sp['ci_low']:.3f}x, {sp['ci_high']:.3f}x]")
        else:
            slowdown = 1.0 / sp["ratio"]
            print(f"  [{detector}] Slowdown: {slowdown:.3f}x "
                  f"[{1/sp['ci_high']:.3f}x, {1/sp['ci_low']:.3f}x]")

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

    out = SAVE_DIR / "WaterfallComparison.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved --> {out}")

    print("\n" + "=" * 70)
    print("Waterfall graph created successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
