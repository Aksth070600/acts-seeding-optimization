import sys
sys.path.insert(0, "figure-gen")
from _common import style as cfg

import numpy as np
import matplotlib.pyplot as plt
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

pt = np.sqrt(px**2 + py**2)

fig, ax = plt.subplots(figsize=cfg.FIGSIZE_DATASET_HALFROW)

ax.hist(pt, bins=np.logspace(np.log10(pt.min()), np.log10(pt.max()), 100),
        histtype="step", color=cfg.COLORS["neutral"])

ax.set_xscale("log")
ax.set_yscale("log")
ax.tick_params(axis="both", which="both", direction="in")
ax.set_xlabel(r"Track $p_T$ [MeV]")
ax.set_ylabel("Number of tracks")

fig.tight_layout(pad=cfg.TIGHT_PAD)
fig.savefig(SAVE_DIR / "track_pt.pdf")
