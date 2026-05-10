# matplotlib + _common imports are lazy inside plot_parameter_scan so
# analysis-only callers can import the load_* helpers without pulling matplotlib.
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

TIMER_NAME = "Seeding"

def load_timing(path: Path) -> float:
    df = pd.read_csv(path)
    rows = df[df["NAME"] == TIMER_NAME].copy()
    if rows.empty:
        raise ValueError(f"No {TIMER_NAME!r} rows in {path}")
    rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
    rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
    return float(rows["TIME_NS_PER_EVENT"].mean() / 1e6)


def load_metric(path: Path, key: str) -> float:
    return float(pd.read_csv(path).iloc[0][key])


def _scan_path(scan_dir: Path, stem: str, run_index: int, total_runs: int) -> Path:
    if total_runs == 1:
        return scan_dir / f"{stem}.csv"
    return scan_dir / f"{stem}_run{run_index}.csv"


def load_sweep_grids(scan_dir: Path, n_cells: int) -> dict[str, np.ndarray]:
    time = np.zeros(n_cells)
    eff  = np.zeros(n_cells)
    fake = np.zeros(n_cells)
    dup  = np.zeros(n_cells)
    for k in range(n_cells):
        run = k + 1
        t_path = _scan_path(scan_dir, "ParamOptimizationTiming",  run, n_cells)
        m_path = _scan_path(scan_dir, "ParamOptimizationMetrics", run, n_cells)
        time[k] = load_timing(t_path)
        eff[k]  = load_metric(m_path, "seeding_particle_efficiency")
        fake[k] = load_metric(m_path, "seeding_particle_fake_ratio")
        dup[k]  = load_metric(m_path, "seeding_particle_duplicate_ratio")
    return {"time": time, "eff": eff, "fake": fake, "dup": dup}


def load_baseline(baseline_dir: Path) -> dict[str, float]:
    return {
        "time": load_timing(baseline_dir / "ParamOptimizationTiming.csv"),
        "eff":  load_metric(baseline_dir / "ParamOptimizationMetrics.csv", "seeding_particle_efficiency"),
        "fake": load_metric(baseline_dir / "ParamOptimizationMetrics.csv", "seeding_particle_fake_ratio"),
        "dup":  load_metric(baseline_dir / "ParamOptimizationMetrics.csv", "seeding_particle_duplicate_ratio"),
    }


def plot_parameter_scan(
    *,
    parameter_values: Sequence[float],
    eff:        np.ndarray,
    fake:       np.ndarray,
    dup:        np.ndarray,
    time_ms:    np.ndarray,
    parameter_label: str,
    title:      str | None = None,
    output_path: Path,
    baseline:   dict | None = None,
    xscale:     str = "linear",
    wc_ylim:    tuple[float, float] = (0.0, 0.45),
    eff_ylim:   tuple[float, float] = (0.5, 1.0),
    rate_ylim:  tuple[float, float] | None = None,
    anchor_x:   float | None = None,
) -> Path:
    sys.path.insert(0, "figure-gen")
    import _common  # noqa: F401
    import math
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    x = np.asarray(parameter_values, dtype=float)

    if baseline is not None and not np.isclose(baseline["time"], 0.0):
        wc = time_ms / baseline["time"]
        wc_label = "Time / Cyl baseline"
        wc_baseline = 1.0
    else:
        wc = time_ms.copy()
        wc_label = "Time per event [ms]"
        wc_baseline = None

    fig, (ax_eff, ax_rate, ax_wc) = plt.subplots(
        3, 1, figsize=(9.5, 7.0), sharex=True,
        layout="constrained",
        gridspec_kw={"height_ratios": [1.4, 1.4, 1.0]},
    )

    ax_eff.plot(x, eff, marker="o", linewidth=2, color="#1f77b4",
                label="Efficiency")
    ax_eff.set_ylim(*eff_ylim)
    ax_eff.set_ylabel("Efficiency")
    ax_eff.grid(True, ls=":", alpha=0.4)
    if title:
        ax_eff.set_title(title)

    # Okabe-Ito vermillion + bluish-green (colour-vision-safe pair).
    fake_pct = 100.0 * np.asarray(fake)
    dup_pct  = 100.0 * np.asarray(dup)
    ax_rate.plot(x, fake_pct, marker="s", linewidth=2, color="#D55E00",
                 label="Fake rate")
    ax_rate.plot(x, dup_pct,  marker="^", linewidth=2, color="#009E73",
                 label="Duplicate rate")
    if rate_ylim is None:
        ymax_raw = 1.15 * float(np.max(np.concatenate([fake_pct, dup_pct])))
        ymax = max(20.0, math.ceil(ymax_raw / 5.0) * 5.0)
        ax_rate.set_ylim(0.0, min(100.0, ymax))
    else:
        ax_rate.set_ylim(*rate_ylim)
    ax_rate.set_ylabel("Fake / duplicate rate [%]")
    ax_rate.grid(True, ls=":", alpha=0.4)
    ax_rate.legend(loc="lower right", frameon=False, fontsize="small")

    ax_wc.plot(x, wc, marker="o", linewidth=2, color="#444444")
    ax_wc.set_ylim(*wc_ylim)
    ax_wc.set_xlabel(parameter_label)
    ax_wc.set_ylabel(wc_label)
    ax_wc.grid(True, ls=":", alpha=0.4)

    # Cyl baseline at ratio=1.0 is above-range when wall-clock is
    # normalised; an in-panel annotation flags it.
    if wc_baseline is not None and wc_baseline > wc_ylim[1]:
        ax_wc.text(
            0.985, 0.92,
            f"Cyl baseline = {wc_baseline:.2f} (above plot range)",
            transform=ax_wc.transAxes, ha="right", va="top",
            fontsize="small", color="0.30",
            bbox=dict(facecolor="white", edgecolor="none",
                      alpha=0.75, pad=2.0),
        )

    if anchor_x is not None:
        for ax in (ax_eff, ax_rate, ax_wc):
            ax.axvline(anchor_x, ls="--", color="#222222", lw=1.4,
                       zorder=4, alpha=0.75)

        # Mirror "Default" label to the right when the anchor sits at
        # the right edge so it doesn't fall off the panel.
        try:
            anchor_idx = list(parameter_values).index(anchor_x)
            rel_pos = anchor_idx / max(1, len(parameter_values) - 1)
        except ValueError:
            rel_pos = 0.5
        if rel_pos > 0.7:
            label_text, label_ha = "Default ", "right"
        else:
            label_text, label_ha = " Default", "left"

        ax_eff.text(
            anchor_x, 0.95, label_text,
            transform=ax_eff.get_xaxis_transform(),
            ha=label_ha, va="top",
            fontsize="small", color="#111111", weight="bold", zorder=6,
            bbox=dict(facecolor="white", edgecolor="#222222",
                      boxstyle="round,pad=0.25", alpha=0.92),
        )

    if xscale == "log":
        ax_wc.set_xscale("log")
        ax_wc.set_xticks(list(x), minor=True)
    else:
        all_ticks = list(x)
        ax_wc.set_xticks(all_ticks)
        all_int = bool(x.size) and np.all(np.equal(np.mod(x, 1), 0))
        # Thin labels at high tick density but keep grid at every tick.
        stride = 2 if len(all_ticks) > 10 else 1
        if all_int:
            labels = [f"{int(round(v))}" if i % stride == 0 else ""
                      for i, v in enumerate(all_ticks)]
        else:
            labels = [f"{v:g}" if i % stride == 0 else ""
                      for i, v in enumerate(all_ticks)]
        ax_wc.set_xticklabels(labels)
        ax_wc.tick_params(axis="x", pad=4)

    for ax in (ax_eff, ax_rate, ax_wc):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path))
    plt.close(fig)
    return output_path
