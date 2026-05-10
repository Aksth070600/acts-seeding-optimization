import sys
sys.path.insert(0, "configs")
import numpy as np
from pathlib import Path

RAW_DIR  = Path("raw-data/Datasets")
SAVE_DIR = Path("figures/Datasets")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

n_truth  = np.load(RAW_DIR / "nPartEVT.npy")
n_tracks = np.load(RAW_DIR / "nTRK.npy")
cl_hw    = np.load(RAW_DIR / "CLhardware.npy",  allow_pickle=True)
sp_idx   = np.load(RAW_DIR / "SPCL2_index.npy", allow_pickle=True)

n_events = len(n_truth)

n_pix_cl   = np.array([np.sum(np.array(cl_hw[i])  == "PIXEL") for i in range(n_events)])
n_strip_cl = np.array([np.sum(np.array(cl_hw[i])  == "STRIP") for i in range(n_events)])
n_pix_sp   = np.array([np.sum(np.array(sp_idx[i]) == -1)      for i in range(n_events)])
n_strip_sp = np.array([np.sum(np.array(sp_idx[i]) != -1)      for i in range(n_events)])


def stats(arr):
    return arr.mean(), arr.std(), arr.std() / arr.mean() * 100, arr.min(), arr.max()


def row(label, arr, shaded=False):
    mean, sd, cv, mn, mx = stats(arr)
    prefix = r"\rowcolor{gray!15}" + "\n" if shaded else ""
    return (
        f"{prefix}"
        f"    \\quad {label} & ${mean:,.0f} \\pm {sd:,.0f}$ & {cv:.1f} "
        f"& {mn:,.0f} & {mx:,.0f} \\\\"
    )


def section_header(title):
    return (
        r"\rowcolor{gray!25}" + "\n"
        + r"\multicolumn{5}{l}{\textbf{" + title + r"}} \\"
    )


lines = [
    section_header("Reconstruction"),
    row("Truth particles", n_truth,  shaded=False),
    row("Tracks",          n_tracks, shaded=True),
    section_header("Pixel detector"),
    row("Clusters",                               n_pix_cl, shaded=False),
    row(r"Space points\textsuperscript{\dag}",    n_pix_sp, shaded=True),
    section_header("Strip detector"),
    row("Clusters",        n_strip_cl, shaded=False),
    row("Space points",    n_strip_sp, shaded=True),
]

table = (
    r"\normalsize" + "\n"
    + r"\renewcommand{\arraystretch}{1.4}" + "\n"
    + r"\resizebox{\textwidth}{!}{%" + "\n"
    + r"\begin{tabular}{lrrrr}" + "\n"
    + r"\toprule" + "\n"
    + r"\textbf{Quantity} & \textbf{Mean $\pm$ SD} & \textbf{CV (\%)} "
      r"& \textbf{Min} & \textbf{Max} \\" + "\n"
    + r"\midrule" + "\n"
    + "\n".join(lines) + "\n"
    + r"\bottomrule" + "\n"
    + r"\end{tabular}%" + "\n"
    + r"}"
)

out = SAVE_DIR / "table_dataset_characteristics.tex"
out.write_text(table)
