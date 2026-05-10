import sys
sys.path.insert(0, "figure-gen")
from _common import style as cfg

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, MultipleLocator
from pathlib import Path

plt.rcParams["axes.labelsize"]  = 14
plt.rcParams["xtick.labelsize"] = 12
plt.rcParams["ytick.labelsize"] = 12

RAW_DIR  = Path("raw-data/Datasets")
SAVE_DIR = Path("figures/Datasets")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

mom = np.load(RAW_DIR / "TRKperigee_momentum.npy", allow_pickle=True)

px = np.concatenate([np.array(m)[:, 0] for m in mom])
py = np.concatenate([np.array(m)[:, 1] for m in mom])

phi = np.arctan2(py, px)

fig, ax = plt.subplots(figsize=cfg.FIGSIZE_DATASET_FULLROW)

ax.hist(phi, bins=100, histtype="step", color=cfg.COLORS["neutral"])

ax.set_xlim(-np.pi, np.pi)
ax.set_xticks([-np.pi, -np.pi / 2, 0, np.pi / 2, np.pi])
ax.set_xticklabels([r"$-\pi$", r"$-\pi/2$", "0", r"$\pi/2$", r"$\pi$"])
ax.xaxis.set_minor_locator(MultipleLocator(np.pi / 8))
ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
ax.tick_params(axis="both", which="both", direction="in")
# 15% headroom so the "approximately uniform" claim reads visually.
ax.set_ylim(0, ax.get_ylim()[1] * 1.15)
ax.set_xlabel(r"Track $\phi$ [rad]")
ax.set_ylabel("Number of tracks")

fig.tight_layout(pad=cfg.TIGHT_PAD)
fig.savefig(SAVE_DIR / "track_phi.pdf")
