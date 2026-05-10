#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
import _common
from bootstrap_ci_helper import (
    bootstrap_geometric_mean_ratio_from_event_means,
    bootstrap_mean,
)

__all__ = [
    "RawTimerData", "StageData", "StageDelta", "SpeedupResult",
    "WaterfallColors", "DEFAULT_COLORS",
    "parse_waterfall_csv",
    "sum_timers", "extract_stages",
    "compute_stage_delta", "compute_all_stage_deltas",
    "compute_overall_speedup",
    "plot_waterfall_on_axis",
    "add_waterfall_legend",
    "print_stage_summary",
]

BOOTSTRAP_SAMPLES = 10_000
ANCHOR_TIMER      = "Seeding"

RawTimerData = dict[str, np.ndarray]
StageData = dict[str, np.ndarray]


class StageDelta(TypedDict):
    mean:       float
    ci_low:     float
    ci_high:    float
    half_width: float
    mean_ms:    float


class SpeedupResult(TypedDict):
    ratio:     float
    ci_low:    float
    ci_high:   float


class WaterfallColors(TypedDict):
    baseline: str
    faster:   str
    slower:   str
    final:    str


DEFAULT_COLORS: WaterfallColors = {
    "baseline": "#4472C4",
    "faster":   "#51CF66",
    "slower":   "#FF6B6B",
    "final":    "#1F4E79",
}


def parse_waterfall_csv(path: Path | str) -> RawTimerData:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Timer CSV not found: {path}")

    df = pd.read_csv(path)

    n_snapshots = int((df["NAME"] == ANCHOR_TIMER).sum())
    if n_snapshots == 0:
        raise ValueError(
            f"Anchor timer '{ANCHOR_TIMER}' not found in {path}.\n"
            "Check that the CSV was produced with the correct timer names."
        )

    result: RawTimerData = {}
    for name, grp in df.groupby("NAME"):
        cumul = (
            grp.sort_values("TIME_NS")["TIME_NS"]
            .to_numpy(dtype=float)
        )
        if len(cumul) > n_snapshots:
            cumul = cumul[:n_snapshots]
        elif len(cumul) < n_snapshots:
            cumul = np.pad(cumul, (0, n_snapshots - len(cumul)), mode="edge")
        result[name] = np.diff(cumul, prepend=0.0)

    return result


def sum_timers(raw: RawTimerData, names: list[str], n: int) -> np.ndarray:
    arrays = [raw[nm] for nm in names if nm in raw]
    return np.sum(arrays, axis=0) if arrays else np.zeros(n)


def extract_stages(
    raw:              RawTimerData,
    stage_timers:     dict[str, list[str]],
    group_children:   list[str],
    residual_stage:   str | None = "Overhead",
    conv_stage:       str        = "ConvProxSeeds",
) -> StageData:
    n = len(raw.get(ANCHOR_TIMER, np.array([])))

    stages: StageData = {}
    stages["total"] = sum_timers(raw, stage_timers["total"], n)

    for key, timer_names in stage_timers.items():
        if key in ("total", "createSeedsGroup"):
            continue
        stages[key] = sum_timers(raw, timer_names, n)

    group_incl = sum_timers(raw, stage_timers.get("createSeedsGroup", []), n)
    if residual_stage is not None:
        grid_t = stages.get("GridSetup", np.zeros(n))
        conv_t = stages.get(conv_stage,  np.zeros(n))
        stages[residual_stage] = np.maximum(
            stages["total"] - grid_t - conv_t - group_incl, 0.0
        )

    children = np.sum(
        [stages.get(c, np.zeros(n)) for c in group_children], axis=0
    )
    stages["createSeedsGroup"] = np.maximum(group_incl - children, 0.0)

    return stages


def compute_stage_delta(
    a1:      np.ndarray,
    a2:      np.ndarray,
    norm_ms: float,
    n_boot:  int = BOOTSTRAP_SAMPLES,
) -> StageDelta:
    n    = min(len(a1), len(a2))
    diff = (a2[:n] - a1[:n]) / norm_ms
    ok   = np.isfinite(diff)
    r    = bootstrap_mean(diff[ok], n_boot=n_boot)

    return StageDelta(
        mean       = r["mean"],
        ci_low     = r["ci_low"],
        ci_high    = r["ci_high"],
        half_width = r["half_width"],
        mean_ms    = r["mean"] * norm_ms,
    )


def compute_all_stage_deltas(
    s1:      StageData,
    s2:      StageData,
    stages:  list[str],
    norm_ms: float,
    n_boot:  int = BOOTSTRAP_SAMPLES,
) -> dict[str, StageDelta]:
    def _ms(arr: np.ndarray) -> np.ndarray:
        return arr / 1e6
    return {
        stage: compute_stage_delta(
            _ms(s1.get(stage, np.zeros_like(s1["total"]))),
            _ms(s2.get(stage, np.zeros_like(s2["total"]))),
            norm_ms,
            n_boot,
        )
        for stage in stages
    }


def compute_overall_speedup(
    s1_total: np.ndarray,
    s2_total: np.ndarray,
    n_boot:   int = BOOTSTRAP_SAMPLES,
) -> SpeedupResult:
    n     = min(len(s1_total), len(s2_total))
    b_arr = s1_total[:n]
    o_arr = s2_total[:n]
    valid = np.isfinite(b_arr) & np.isfinite(o_arr) & (b_arr > 0) & (o_arr > 0)
    r     = bootstrap_geometric_mean_ratio_from_event_means(
        b_arr[valid], o_arr[valid], n_boot=n_boot
    )
    return SpeedupResult(ratio=r["ratio"], ci_low=r["ci_low"], ci_high=r["ci_high"])


YLIM_LO = 0.85
YLIM_HI = 1.05
EXPAND_LO_FLOOR = 0.05
LABEL_HEADROOM = 0.025
BASE_BREATHING = 0.02
LABEL_OFFSET_PT = 5
ZERO_BAR_THRESHOLD = 0.002


def _auto_ylim(bar_top, bar_bot, final_norm):
    # Baseline + final bars start at y=0; that bottom is decorative.
    n = len(bar_top)
    lows  = bar_bot[1:n - 1] + [final_norm]
    highs = bar_top[:]
    raw_lo = (min(lows) - BASE_BREATHING) if lows else YLIM_LO
    y_lo = min(YLIM_LO, max(EXPAND_LO_FLOOR, raw_lo))
    y_hi = max(YLIM_HI, max(highs) + LABEL_HEADROOM) if highs else YLIM_HI
    return y_lo, y_hi


def plot_waterfall_on_axis(
    ax:            plt.Axes,
    s1:            StageData,
    s2:            StageData,
    stages:        list[str],
    stage_labels:  dict[str, str],
    method1:       str             = "Baseline",
    method2:       str             = "Optimized",
    title:         str             = "",
    n_boot:        int             = BOOTSTRAP_SAMPLES,
    colors:        WaterfallColors = DEFAULT_COLORS,
) -> dict:
    base_ms   = s1["total"] / 1e6
    opt_ms    = s2["total"] / 1e6
    base_mean = float(np.nanmean(base_ms))
    opt_mean  = float(np.nanmean(opt_ms))
    norm_ms   = base_mean

    deltas     = compute_all_stage_deltas(s1, s2, stages, norm_ms, n_boot)
    speedup    = compute_overall_speedup(s1["total"], s2["total"], n_boot)
    final_norm = opt_mean / norm_ms

    final_ci_lo = 1.0 / speedup["ci_high"]
    final_ci_hi = 1.0 / speedup["ci_low"]

    ax.bar(0, 1.0, width=0.6, color=colors["baseline"], alpha=0.9,
           edgecolor="black", linewidth=1.0)

    bar_x:   list[float] = [0]
    bar_top: list[float] = [1.0]
    bar_bot: list[float] = [0.0]

    running = 1.0
    for i, stage in enumerate(stages):
        x      = i + 1
        d      = deltas[stage]["mean"]
        ci_lo  = deltas[stage]["ci_low"]
        ci_hi  = deltas[stage]["ci_high"]

        color      = colors["faster"] if d <= 0 else colors["slower"]
        bar_bottom = running + d if d < 0 else running
        top        = bar_bottom + abs(d)

        ax.bar(x, abs(d), bottom=bar_bottom, width=0.6,
               color=color, alpha=0.9, edgecolor="black", linewidth=0.8)

        # Tick stub for ~0% bars so the column isn't a phantom under the label.
        if abs(d) < ZERO_BAR_THRESHOLD:
            ax.plot([x - 0.30, x + 0.30], [running, running],
                    color="black", lw=1.0, alpha=0.85, solid_capstyle="butt")

        err_lo = abs(d - ci_lo)
        err_hi = abs(ci_hi - d)
        ax.errorbar(
            x, top, yerr=[[err_lo], [err_hi]],
            fmt="none", ecolor="black", capsize=2.5, capthick=0.8, lw=0.8,
        )

        pct = d * 100
        sgn = "+" if pct >= 0 else ""
        ax.annotate(
            f"{sgn}{pct:.1f}%",
            xy=(x, top), xycoords="data",
            xytext=(0, LABEL_OFFSET_PT), textcoords="offset points",
            ha="center", va="bottom",
            fontsize=10, color="black",
        )

        bar_x.append(x)
        bar_top.append(top)
        bar_bot.append(bar_bottom)
        running += d

    x_final = len(stages) + 1
    final_err_lo = final_norm - final_ci_lo
    final_err_hi = final_ci_hi - final_norm

    ax.bar(x_final, final_norm, width=0.6, color=colors["final"], alpha=0.9,
           edgecolor="black", linewidth=1.0)
    ax.errorbar(
        x_final, final_norm, yerr=[[final_err_lo], [final_err_hi]],
        fmt="none", ecolor="black", capsize=2.5, capthick=0.8, lw=0.8,
    )
    ax.annotate(
        f"{final_norm:.3f}",
        xy=(x_final, final_norm), xycoords="data",
        xytext=(0, LABEL_OFFSET_PT), textcoords="offset points",
        ha="center", va="bottom",
        fontsize=10, color="black",
    )

    total_pct = (final_norm - 1.0) * 100
    ax.text(
        0.98, 0.95, f"Total: {total_pct:+.1f}%",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.3",
                  facecolor="white", edgecolor="0.6", linewidth=0.6,
                  alpha=0.9),
    )

    bar_x.append(x_final)
    bar_top.append(final_norm)
    bar_bot.append(0.0)

    # Connector lines along the running total.
    for i in range(1, len(bar_x) - 2):
        ax.plot(
            [bar_x[i] + 0.3, bar_x[i+1] - 0.3],
            [bar_top[i],     bar_bot[i+1]],
            color="0.45", lw=0.7, linestyle="--", alpha=0.6,
        )

    tick_labels = (
        [f"{method1} (total)"] +
        [stage_labels.get(s, s) for s in stages] +
        [f"{method2} (total)"]
    )
    xs = np.arange(len(stages) + 2)
    ax.set_xticks(xs)
    ax.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("Normalized execution time")
    if title:
        ax.set_title(title)
    ax.set_ylim(*_auto_ylim(bar_top, bar_bot, final_norm))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return {
        "baseline_mean_ms":  base_mean,
        "optimized_mean_ms": opt_mean,
        "final_norm":        final_norm,
        "speedup":           speedup,
        "deltas":            deltas,
    }


def add_waterfall_legend(
    fig_or_ax,
    method1:  str             = "Baseline",
    method2:  str             = "Optimized",
    colors:   WaterfallColors = DEFAULT_COLORS,
    loc:      str             = "upper left",
    fontsize: int             = 10,
    n_boot:   int             = BOOTSTRAP_SAMPLES,
) -> None:
    handles = [
        mpatches.Patch(facecolor=colors["baseline"], edgecolor="black",
                       alpha=0.9, label=f"{method1} total"),
        mpatches.Patch(facecolor=colors["faster"],   edgecolor="black",
                       alpha=0.9, label=f"Faster in {method2}"),
        mpatches.Patch(facecolor=colors["slower"],   edgecolor="black",
                       alpha=0.9, label=f"Slower in {method2}"),
        mpatches.Patch(facecolor=colors["final"],    edgecolor="black",
                       alpha=0.9, label=f"{method2} total"),
    ]

    is_figure = hasattr(fig_or_ax, "legend") and hasattr(fig_or_ax, "axes")
    if is_figure:
        fig_or_ax.legend(handles=handles, loc=loc, fontsize=fontsize,
                         framealpha=0.9, edgecolor="black")
    else:
        fig_or_ax.legend(handles=handles, loc=loc, fontsize=fontsize,
                         framealpha=0.9, edgecolor="black")


def print_stage_summary(
    s1:      StageData,
    s2:      StageData,
    stages:  list[str],
    method1: str = "Method1",
    method2: str = "Method2",
) -> None:
    def _ms(arr): return float(np.nanmean(arr)) / 1e6

    col_w = max(len(method1), len(method2), 14)
    hdr   = f"{'Stage':<22} {method1:>{col_w}} ms  {method2:>{col_w}} ms   Delta"
    print(hdr)
    print("-" * len(hdr))
    for stage in ["total"] + stages:
        v1  = _ms(s1.get(stage, np.array([0.0])))
        v2  = _ms(s2.get(stage, np.array([0.0])))
        pct = (v2 - v1) / v1 * 100 if v1 > 0 else float("nan")
        sgn = "+" if pct >= 0 else ""
        print(f"  {stage:<20} {v1:>{col_w}.2f}     {v2:>{col_w}.2f}     {sgn}{pct:.1f}%")
    print()
