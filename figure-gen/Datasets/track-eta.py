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
pz = np.concatenate([np.array(m)[:, 2] for m in mom])

pt  = np.sqrt(px**2 + py**2)
p   = np.sqrt(px**2 + py**2 + pz**2)
eta = np.log((p + pz) / pt)

fig, ax = plt.subplots(figsize=cfg.FIGSIZE_DATASET_HALFROW)

ax.hist(eta, bins=100, histtype="step", color=cfg.COLORS["neutral"])

ax.set_xlim(-4, 4)
ax.set_xticks([-4, -2, 0, 2, 4])
ax.xaxis.set_minor_locator(MultipleLocator(0.5))
ax.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
ax.tick_params(axis="both", which="both", direction="in")
ax.set_ylim(bottom=0)
ax.set_xlabel(r"Track $\eta$")
ax.set_ylabel("Number of tracks")

fig.tight_layout(pad=cfg.TIGHT_PAD)
fig.savefig(SAVE_DIR / "track_eta.pdf")
