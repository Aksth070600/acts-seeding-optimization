#!/usr/bin/env python3

import sys
sys.path.insert(0, "figure-gen")
sys.path.insert(0, "data-gen")
from _common import style as cfg
from workflow import default_runs

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

TIMING_DIR  = Path("raw-data/Methods")
WORKLOAD_DIR = Path("raw-data/Methods")
SAVE_DIR    = Path("figures/Methods")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

RUNS = default_runs()
WINDOW = 10
TIMER_NAME = "Seeding"

PIXEL_PREFIX = "PixelTiming"
STRIP_PREFIX = "StripTiming"

PIXEL_WORKLOAD_FILE = WORKLOAD_DIR / "PixelWorkload.csv"
STRIP_WORKLOAD_FILE = WORKLOAD_DIR / "StripWorkload.csv"

OUTPUT_FILE = SAVE_DIR / "WarmUp_RunningMean.pdf"

def load_times(prefix):
    frames = []
    for r in range(1, RUNS + 1):
        path = TIMING_DIR / f"{prefix}_run{r}.csv"
        if not path.exists() and RUNS == 1:
            path = TIMING_DIR / f"{prefix}.csv"
        df = pd.read_csv(path)
        rows = df[df["NAME"] == TIMER_NAME].copy()
        if rows.empty:
            raise ValueError(f"No {TIMER_NAME!r} rows in {path}")
        rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
        rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
        rows["REALTIME_S"] = rows["TIME_NS_PER_EVENT"] / 1e9
        rows["SAMPLE_INDEX"] = range(1, len(rows) + 1)
        rows["RUN"] = r
        frames.append(rows)
    return pd.concat(frames, ignore_index=True)


def load_workload(path):
    return pd.read_csv(path)

def merge_time_workload(df_time, df_work):
    return df_time.merge(
        df_work[["EVENT_INDEX", "SPACEPOINTS"]],
        left_on="SAMPLE_INDEX",
        right_on="EVENT_INDEX",
        how="inner",
    ).copy()

def fit_linear(df):
    avg = df.groupby("SAMPLE_INDEX", as_index=False).agg(
        T=("REALTIME_S", "mean"),
        N_SP=("SPACEPOINTS", "first"),
    )
    a, b = np.polyfit(avg["N_SP"], avg["T"], 1)
    pred = a * avg["N_SP"] + b
    ss_res = ((avg["T"] - pred) ** 2).sum()
    ss_tot = ((avg["T"] - avg["T"].mean()) ** 2).sum()
    r2 = 1.0 - ss_res / ss_tot
    return a, b, r2

def build_series(df, a, b):
    df = df.copy()
    df["VAL"] = (df["REALTIME_S"] - (a * df["SPACEPOINTS"] + b)) * 1000.0
    df = df.sort_values(["RUN", "SAMPLE_INDEX"])
    df["RUN_MEAN"] = (
        df.groupby("RUN")["VAL"]
        .transform(lambda s: s.rolling(WINDOW, center=True, min_periods=1).mean())
    )
    return df

def summarize(df):
    return (
        df.groupby("SAMPLE_INDEX", as_index=False)
        .agg(
            MEAN=("VAL", "mean"),
            RUN_MEAN=("RUN_MEAN", "mean"),
        )
        .sort_values("SAMPLE_INDEX")
    )

def draw(ax, df, color, linestyle, show_ylabel):
    x = df["SAMPLE_INDEX"].to_numpy()

    ax.plot(x, df["MEAN"],     color=color, alpha=0.45, linewidth=1.0,
            linestyle=linestyle, marker="o", markersize=4)
    ax.plot(x, df["RUN_MEAN"], color=color, linewidth=1.8,
            linestyle=linestyle, marker="o", markersize=4)

    ax.axhline(0.0, color="black", linestyle=":", linewidth=1.0, alpha=0.6)

    ax.set_xlabel("Event index")
    if show_ylabel:
        ax.set_ylabel("Runtime residual [ms]")

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="in")


def main():
    pix_time = load_times(PIXEL_PREFIX)
    str_time = load_times(STRIP_PREFIX)

    pix_work = load_workload(PIXEL_WORKLOAD_FILE)
    str_work = load_workload(STRIP_WORKLOAD_FILE)

    pix_merged = merge_time_workload(pix_time, pix_work)
    str_merged = merge_time_workload(str_time, str_work)

    pix_a, pix_b, pix_r2 = fit_linear(pix_merged)
    str_a, str_b, str_r2 = fit_linear(str_merged)

    print(f"Pixel fit: a = {pix_a:.3e}, b = {pix_b:.3e}, R^2 = {pix_r2:.4f}")
    print(f"Strip fit: a = {str_a:.3e}, b = {str_b:.3e}, R^2 = {str_r2:.4f}")

    pix = summarize(build_series(pix_merged, pix_a, pix_b))
    stp = summarize(build_series(str_merged, str_a, str_b))

    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        figsize=(cfg.FIGSIZE_FULL[0] * 1.9, cfg.FIGSIZE_FULL[1]),
        sharey=True,
    )

    draw(ax1, pix, cfg.COLORS["Pixel"], linestyle="-",  show_ylabel=True)
    draw(ax2, stp, cfg.COLORS["Strip"], linestyle="--", show_ylabel=False)

    # Detector identity is encoded by colour+linestyle; legend only
    # distinguishes per-event vs running mean.
    legend_handles = [
        Line2D([0], [0], color="0.4", lw=1.0, alpha=0.7,
               marker="o", markersize=4, label="Per-event mean"),
        Line2D([0], [0], color="0.4", lw=1.8,
               marker="o", markersize=4, label=f"Running mean ({WINDOW})"),
    ]
    fig.legend(handles=legend_handles, loc="upper center",
               bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)

    fig.tight_layout(pad=cfg.TIGHT_PAD, rect=[0, 0, 1, 0.93])

    fig.savefig(OUTPUT_FILE)
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
