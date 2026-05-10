import uproot
import numpy as np
from pathlib import Path

DATAPATH = "/storage/shared/ACTS/user.avallier.38040858.EXT0._000074.Dump_GNN4Itk.root"
SAVE_DIR = Path("raw-data/Datasets")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

with uproot.open(DATAPATH) as f:
    tree = f["GNN4ITk"]

    np.save(SAVE_DIR / "TRKperigee_momentum.npy", tree["TRKperigee_momentum"].array(library="np"))
    np.save(SAVE_DIR / "CLhardware.npy",          tree["CLhardware"].array(library="np"))
    np.save(SAVE_DIR / "SPCL2_index.npy",         tree["SPCL2_index"].array(library="np"))
    np.save(SAVE_DIR / "nPartEVT.npy",      tree["nPartEVT"].array(library="np"))
    np.save(SAVE_DIR / "nTRK.npy",                tree["nTRK"].array(library="np"))
