import sys
sys.path.insert(0, "figure-gen")
from _common import style as cfg

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LogNorm
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MaxNLocator, MultipleLocator
from pathlib import Path

plt.rcParams["axes.labelsize"]  = 14
plt.rcParams["xtick.labelsize"] = 12
plt.rcParams["ytick.labelsize"] = 12
plt.rcParams["font.size"]       = 12

RAW_DIR  = Path("raw-data/Datasets")
SAVE_DIR = Path("figures/Datasets")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

mom = np.load(RAW_DIR / "TRKperigee_momentum.npy", allow_pickle=True)

px = np.concatenate([np.array(m)[:, 0] for m in mom])
py = np.concatenate([np.array(m)[:, 1] for m in mom])
pz = np.concatenate([np.array(m)[:, 2] for m in mom])

pt  = np.sqrt(px**2 + py**2)
p   = np.sqrt(px**2 + py**2 + pz**2)
eta = np.log((p + pz) / pt)

ETA_LIM = (-4.0, 4.0)
PT_LIM  = (max(pt.min(), 1.0), 1e5)

eta_edges = np.linspace(*ETA_LIM, 80)
pt_edges  = np.logspace(np.log10(PT_LIM[0]), np.log10(PT_LIM[1]), 80)

mask = (eta >= ETA_LIM[0]) & (eta <= ETA_LIM[1]) & (pt >= PT_LIM[0]) & (pt <= PT_LIM[1])

fig = plt.figure(figsize=cfg.FIGSIZE_DATASET_FULLBIG, constrained_layout=True)
gs  = GridSpec(2, 3, width_ratios=[4, 1, 0.18], height_ratios=[1, 4],
               hspace=0.05, wspace=0.05, figure=fig)

ax_main  = fig.add_subplot(gs[1, 0])
ax_top   = fig.add_subplot(gs[0, 0], sharex=ax_main)
ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)
ax_cbar  = fig.add_subplot(gs[1, 2])

# Empty bins are masked grey so "no data" is distinguishable from the
# dark-purple low-density end of viridis at print scale.
cmap = mpl.colormaps["viridis"].with_extremes(bad="#D9D9D9")
H, xe, ye = np.histogram2d(eta[mask], pt[mask], bins=[eta_edges, pt_edges])
H_masked  = np.ma.masked_where(H == 0, H)
im = ax_main.pcolormesh(
    xe, ye, H_masked.T,
    norm=LogNorm(vmin=1, vmax=H.max()),
    cmap=cmap,
)
ax_main.set_yscale("log")
ax_main.set_xlim(*ETA_LIM)
ax_main.set_ylim(*PT_LIM)
ax_main.set_xticks([-4, -2, 0, 2, 4])
ax_main.xaxis.set_minor_locator(MultipleLocator(0.5))
ax_main.tick_params(axis="both", which="both", direction="in")
ax_main.set_xlabel(r"Track $\eta$")
ax_main.set_ylabel(r"Track $p_T$ [MeV]")

ax_top.hist(eta[mask], bins=eta_edges, histtype="step", color=cfg.COLORS["neutral"])
ax_top.set_ylabel("Number of tracks")
ax_top.tick_params(axis="both", which="both", direction="in")
ax_top.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True, prune="lower"))
plt.setp(ax_top.get_xticklabels(), visible=False)

def fmt_k(x, _):
    if abs(x) >= 1000:
        return f"{x/1000:g}k"
    return f"{x:g}"

ax_right.hist(pt[mask], bins=pt_edges, histtype="step",
              orientation="horizontal", color=cfg.COLORS["neutral"])
ax_right.set_xlabel("Number of tracks")
ax_right.tick_params(axis="both", which="both", direction="in")
ax_right.xaxis.set_major_locator(MaxNLocator(nbins=3, integer=True, prune="lower"))
ax_right.xaxis.set_major_formatter(plt.FuncFormatter(fmt_k))
plt.setp(ax_right.get_yticklabels(), visible=False)
# ax_right.hist() autoscales the shared y-axis past PT_LIM[1]; re-pin it.
ax_right.set_ylim(*PT_LIM)

cbar = fig.colorbar(im, cax=ax_cbar)
cbar.set_label("Tracks per bin")
ax_cbar.tick_params(direction="in")

fig.align_ylabels([ax_top, ax_main])
fig.get_layout_engine().set(w_pad=0.08, h_pad=0.04)

fig.savefig(SAVE_DIR / "pT_vs_eta.pdf", pad_inches=0.15)
