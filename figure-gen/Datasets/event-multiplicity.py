import sys
sys.path.insert(0, "figure-gen")
from _common import style as cfg

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, MultipleLocator
from pathlib import Path

RAW_DIR  = Path("raw-data/Datasets")
SAVE_DIR = Path("figures/Datasets")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

n_truth  = np.load(RAW_DIR / "nPartEVT.npy")
n_tracks = np.load(RAW_DIR / "nTRK.npy")
cl_hw    = np.load(RAW_DIR / "CLhardware.npy",  allow_pickle=True)
sp_idx   = np.load(RAW_DIR / "SPCL2_index.npy", allow_pickle=True)

n_events   = len(n_truth)
n_pix_cl   = np.array([np.sum(np.array(cl_hw[i])  == "PIXEL") for i in range(n_events)])
n_strip_cl = np.array([np.sum(np.array(cl_hw[i])  == "STRIP") for i in range(n_events)])
n_pix_sp   = np.array([np.sum(np.array(sp_idx[i]) == -1)      for i in range(n_events)])
n_strip_sp = np.array([np.sum(np.array(sp_idx[i]) != -1)      for i in range(n_events)])

BINS = 10

def fmt_k(x, _):
    if abs(x) >= 1000:
        return f"{x/1000:g}k"
    return f"{x:g}"

def fmt_k_1dec(x, _):
    if abs(x) >= 1000:
        return f"{x/1000:.1f}k"
    return f"{x:.0f}"

def style_axes(ax, *, xlabel):
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
    ax.xaxis.set_minor_locator(MaxNLocator(nbins=20))
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt_k))
    ax.tick_params(axis="both", which="both", direction="in")
    ax.set_xlabel(xlabel)

def step_hist(ax, data, color, linestyle="-"):
    ax.hist(data, bins=BINS, histtype="step", color=color, linestyle=linestyle)

fig, axes = plt.subplots(3, 2, figsize=cfg.FIGSIZE_DATASET_MULTI,
                         sharey=True, constrained_layout=True)
ax_truth,  ax_tracks = axes[0]
ax_cl_pix, ax_cl_str = axes[1]
ax_sp_pix, ax_sp_str = axes[2]

step_hist(ax_truth,  n_truth,    cfg.COLORS["neutral"])
step_hist(ax_tracks, n_tracks,   cfg.COLORS["neutral"])
step_hist(ax_cl_pix, n_pix_cl,   cfg.COLORS["Pixel"])
step_hist(ax_cl_str, n_strip_cl, cfg.COLORS["Strip"], linestyle="--")
step_hist(ax_sp_pix, n_pix_sp,   cfg.COLORS["Pixel"])
step_hist(ax_sp_str, n_strip_sp, cfg.COLORS["Strip"], linestyle="--")

style_axes(ax_truth,  xlabel="Truth particles per event")
style_axes(ax_tracks, xlabel="Tracks per event")
style_axes(ax_cl_pix, xlabel="Pixel clusters per event")
style_axes(ax_cl_str, xlabel="Strip clusters per event")
style_axes(ax_sp_pix, xlabel="Pixel space points per event")
style_axes(ax_sp_str, xlabel="Strip space points per event")

ax_tracks.xaxis.set_major_formatter(plt.FuncFormatter(fmt_k_1dec))

for ax in (ax_truth, ax_cl_pix, ax_sp_pix):
    ax.set_ylabel("Number of events")

ymax = max(ax.get_ylim()[1] for ax in axes.flat)
ax_truth.set_ylim(0, ymax * 1.10)

fig.savefig(SAVE_DIR / "event_multiplicity.pdf")
