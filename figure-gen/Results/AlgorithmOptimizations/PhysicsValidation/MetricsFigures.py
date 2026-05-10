import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import mplhep as hep
    hep.style.use("ATLAS")
    warnings.filterwarnings("ignore", message=".*divide by zero.*",   module="mplhep")
    warnings.filterwarnings("ignore", message=".*All sumw are zero.*", module="mplhep")
    warnings.filterwarnings("ignore", message=".*invalid value.*",     module="mplhep")
except ImportError:
    sys.exit("[error] mplhep required: pip install mplhep")

# Override mplhep ATLAS-style font sizes (must come after hep.style.use).
plt.rcParams.update({
    "font.size":       14,
    "axes.labelsize":  16,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 16,
})

try:
    import boost_histogram as bh
except ImportError:
    sys.exit("[error] boost_histogram required: pip install boost-histogram")

try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.ProcessLine("gErrorIgnoreLevel = kError;")
except ImportError:
    sys.exit("[error] PyROOT required (available in LCG)")

DEFAULT_ROOT = (
    "raw-data/Results/AlgorithmOptimizations/PhysicsValidation/"
    "performance_seeding.root"
)
DEFAULT_BASE = (
    "raw-data/Results/AlgorithmOptimizations/ParameterOptimization/"
    "Baseline/performance_seeding.root"
)
DEFAULT_OUT = "figures/Results/AlgorithmOptimizations/PhysicsValidationFigures"

DPI     = 150
FIGSIZE = (8, 4.5)
HR      = (3, 1)

COLOR_BASELINE = "#1f77b4"
COLOR_A1       = "#d62728"
COLOR_DELTA    = "#7f7f7f"

LABEL_BASELINE = "Cylindrical"
LABEL_A1       = "Spherical"

XLABEL_MAP = {
    "pT":     r"$p_\mathrm{T}$ [GeV]",
    "eta":    r"$\eta$",
    "phi":    r"$\phi$ [rad]",
    "z0":     r"$z_0$ [mm]",
    "DeltaR": r"$\Delta R$",
    "prodR":  r"Production radius $r_\mathrm{prod}$ [mm]",
}

YLABEL_MAP = {
    "trackeff":            "Efficiency",
    "fakeRatio":           "Fake ratio",
    "duplicationRatio":    "Duplicate ratio",
    "nDuplicated":         r"$\langle n_\mathrm{duplicated} \rangle$",
    "nStates":             r"$\langle n_\mathrm{states} \rangle$",
    "nMeasurements":       r"$\langle n_\mathrm{measurements} \rangle$",
    "nOutliers":           r"$\langle n_\mathrm{outliers} \rangle$",
    "nHoles":              r"$\langle n_\mathrm{holes} \rangle$",
    "nSharedHits":         r"$\langle n_\mathrm{shared\,hits} \rangle$",
    "completeness":        "Completeness",
    "purity":              "Purity",
    "nRecoTracks":         r"$\langle n_\mathrm{reco} \rangle$",
    "nTruthMatchedTracks": r"$\langle n_\mathrm{truth\,matched} \rangle$",
    "nFakeTracks":         r"$\langle n_\mathrm{fake} \rangle$",
}


def fmt_xlabel(key):
    suffix = key.split("_vs_")[-1] if "_vs_" in key else key
    return XLABEL_MAP.get(suffix, None)


def fmt_ylabel(key):
    prefix = key.split("_vs_")[0] if "_vs_" in key else key
    return YLABEL_MAP.get(prefix, None)

def _open(path):
    f = ROOT.TFile.Open(str(path))
    if not f or f.IsZombie():
        raise IOError(f"Cannot open {path}")
    return f


def classnames(path):
    f = _open(path)
    result = {k.GetName(): k.GetClassName() for k in f.GetListOfKeys()}
    f.Close()
    return result


def read_teff(path, key):
    f   = _open(path)
    obj = f.Get(key)
    tot = obj.GetTotalHistogram()
    n   = tot.GetNbinsX()
    edges   = np.array([tot.GetXaxis().GetBinLowEdge(i) for i in range(1, n + 2)])
    eff     = np.array([obj.GetEfficiency(i)            for i in range(1, n + 1)])
    err_lo  = np.array([obj.GetEfficiencyErrorLow(i)    for i in range(1, n + 1)])
    err_hi  = np.array([obj.GetEfficiencyErrorUp(i)     for i in range(1, n + 1)])
    xlabel  = tot.GetXaxis().GetTitle()
    f.Close()
    return edges, eff, err_lo, err_hi, xlabel


def read_tprofile(path, key):
    f   = _open(path)
    obj = f.Get(key)
    n       = obj.GetNbinsX()
    edges   = np.array([obj.GetXaxis().GetBinLowEdge(i) for i in range(1, n + 2)])
    entries = np.array([obj.GetBinEntries(i) for i in range(1, n + 1)])
    means   = np.array([obj.GetBinContent(i) for i in range(1, n + 1)])
    errors  = np.array([obj.GetBinError(i)   for i in range(1, n + 1)])
    means   = np.where(entries > 0, means,  np.nan)
    errors  = np.where(entries > 0, errors, np.nan)
    xlabel  = obj.GetXaxis().GetTitle()
    ylabel  = obj.GetYaxis().GetTitle() or obj.GetTitle()
    f.Close()
    return edges, means, errors, xlabel, ylabel


def read_th2_profile(path, key):
    f   = _open(path)
    obj = f.Get(key)
    nx  = obj.GetNbinsX()
    ny  = obj.GetNbinsY()
    xedges = np.array([obj.GetXaxis().GetBinLowEdge(i) for i in range(1, nx + 2)])
    yc     = np.array([obj.GetYaxis().GetBinCenter(j)  for j in range(1, ny + 1)])
    vals   = np.array([[obj.GetBinContent(i, j) for j in range(1, ny + 1)]
                       for i in range(1, nx + 1)])
    totals = vals.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_y = np.where(totals > 0, (vals * yc).sum(axis=1) / totals, np.nan)
    xlabel = obj.GetXaxis().GetTitle()
    ytitle = obj.GetYaxis().GetTitle()
    ylabel = f"<{ytitle}>" if ytitle else r"$\langle N_\mathrm{tracks} \rangle$"
    f.Close()
    return xedges, mean_y, xlabel, ylabel

def to_weight(values, edges, errors=None):
    h = bh.Histogram(bh.axis.Variable(edges), storage=bh.storage.Weight())
    h.view()["value"]    = np.where(np.isfinite(values), values, 0.0)
    var = errors ** 2 if errors is not None else np.zeros_like(values)
    h.view()["variance"] = np.where(np.isfinite(var) & (var > 0), var, 0.0)
    return h


def to_double(values, edges):
    h = bh.Histogram(bh.axis.Variable(edges), storage=bh.storage.Double())
    h.view()[:] = np.nan_to_num(values, nan=0.0)
    return h


def eff_to_bh(edges, eff, elo, ehi):
    sym = 0.5 * (np.nan_to_num(elo) + np.nan_to_num(ehi))
    return to_weight(eff, edges, sym)


def rel_diff(new, base):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(np.abs(base) > 0, (new - base) / base * 100.0, np.nan)

def make_fig():
    fig = plt.figure(figsize=FIGSIZE)
    gs  = fig.add_gridspec(2, 1, height_ratios=HR, hspace=0.08)
    ax_m = fig.add_subplot(gs[0])
    ax_r = fig.add_subplot(gs[1], sharex=ax_m)
    return fig, ax_m, ax_r


RATIO_YMAX_PCT = 30.0


def _ratio_ylim(delta):
    return RATIO_YMAX_PCT


def _draw_ratio_panel(ax_r, edges, delta):
    ymax_abs = _ratio_ylim(delta)
    ax_r.set_xlim(float(edges[0]), float(edges[-1]))
    # Pin ylim before and after histplot — autoscale on a NaN-only delta
    # collapses the shared-x view and crashes the tick locator.
    ax_r.set_ylim(-ymax_abs, ymax_abs)
    ax_r.set_autoscaley_on(False)
    hep.histplot(to_double(delta, edges), ax=ax_r,
                 histtype="fill", color=COLOR_DELTA, alpha=0.6)
    ax_r.set_ylim(-ymax_abs, ymax_abs)
    ax_r.set_autoscaley_on(False)


def style_ratio(ax_r, xlabel):
    ax_r.axhline(0, color="black", lw=0.8, ls="--")
    ax_r.set_ylabel(r"(Sph $-$ Cyl) $/$ Cyl")
    ax_r.set_xlabel(xlabel)
    ax_r.grid(True, ls=":", alpha=0.4)
    ax_r.set_yticks([-RATIO_YMAX_PCT, -RATIO_YMAX_PCT / 2, 0,
                     RATIO_YMAX_PCT / 2, RATIO_YMAX_PCT])
    ax_r.set_ylim(-RATIO_YMAX_PCT, RATIO_YMAX_PCT)


def save(fig, out_dir, key):
    path = out_dir / f"{key}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  [saved] {path.name}")
    return path

def draw_eff(ax_m, ax_r, path_new, path_base, key):
    edges, e_n, elo_n, ehi_n, xlabel = read_teff(path_new,  key)
    _,     e_b, elo_b, ehi_b, _      = read_teff(path_base, key)
    _draw_ratio_panel(ax_r, edges, rel_diff(e_n, e_b))
    hep.histplot(eff_to_bh(edges, e_b, elo_b, ehi_b), ax=ax_m,
                 histtype="errorbar", label=LABEL_BASELINE,
                 color=COLOR_BASELINE, marker="s",
                 linestyle="--", markersize=3)
    hep.histplot(eff_to_bh(edges, e_n, elo_n, ehi_n), ax=ax_m,
                 histtype="errorbar", label=LABEL_A1,
                 color=COLOR_A1, markersize=5)
    ax_m.set_ylabel("Efficiency")
    style_ratio(ax_r, xlabel)


def draw_rate(ax_m, ax_r, path_new, path_base, key, ylabel):
    edges, e_n, elo_n, ehi_n, xlabel = read_teff(path_new,  key)
    _,     e_b, elo_b, ehi_b, _      = read_teff(path_base, key)
    _draw_ratio_panel(ax_r, edges, rel_diff(e_n, e_b))
    hep.histplot(eff_to_bh(edges, e_b, elo_b, ehi_b), ax=ax_m,
                 histtype="errorbar", label=LABEL_BASELINE,
                 color=COLOR_BASELINE, marker="s",
                 linestyle="--", markersize=3)
    hep.histplot(eff_to_bh(edges, e_n, elo_n, ehi_n), ax=ax_m,
                 histtype="errorbar", label=LABEL_A1,
                 color=COLOR_A1, markersize=5)
    ax_m.set_ylabel(ylabel)
    style_ratio(ax_r, xlabel)


def draw_prof(ax_m, ax_r, path_new, path_base, key):
    edges, m_n, e_n, xlabel, ylabel = read_tprofile(path_new,  key)
    _,     m_b, e_b, _,      _      = read_tprofile(path_base, key)
    _draw_ratio_panel(ax_r, edges, rel_diff(m_n, m_b))
    hep.histplot(to_weight(m_b, edges, e_b), ax=ax_m,
                 histtype="errorbar", label=LABEL_BASELINE,
                 color=COLOR_BASELINE, marker="s",
                 linestyle="--", markersize=3)
    hep.histplot(to_weight(m_n, edges, e_n), ax=ax_m,
                 histtype="errorbar", label=LABEL_A1,
                 color=COLOR_A1, markersize=5)
    ax_m.set_ylabel(ylabel)
    style_ratio(ax_r, xlabel)


def draw_th2(ax_m, ax_r, path_new, path_base, key):
    edges, y_n, xlabel, ylabel = read_th2_profile(path_new,  key)
    _,     y_b, _,      _      = read_th2_profile(path_base, key)
    _draw_ratio_panel(ax_r, edges, rel_diff(y_n, y_b))
    hep.histplot(to_weight(y_b, edges), ax=ax_m,
                 histtype="errorbar", label=LABEL_BASELINE,
                 color=COLOR_BASELINE, marker="s",
                 linestyle="--", markersize=3)
    hep.histplot(to_weight(y_n, edges), ax=ax_m,
                 histtype="errorbar", label=LABEL_A1,
                 color=COLOR_A1, markersize=5)
    ax_m.set_ylabel(ylabel)
    style_ratio(ax_r, xlabel)

def _plot(path_new, path_base, out_dir, key, draw_fn, draw_kwargs,
          ylim_main=None, title=None):
    fig, ax_m, ax_r = make_fig()
    draw_fn(ax_m, ax_r, path_new, path_base, key, **draw_kwargs)
    if ylim_main is not None:
        ax_m.set_ylim(*ylim_main)
    xl = fmt_xlabel(key)
    yl = fmt_ylabel(key)
    if xl:
        ax_r.set_xlabel(xl)
    if yl:
        ax_m.set_ylabel(yl)
    ax_m.legend(framealpha=0.85, loc="best")
    ax_m.tick_params(labelbottom=False)
    if title:
        ax_m.set_title(title)
    return save(fig, out_dir, key)


def plot_all(path_new, path_base, out_dir):
    saved = []

    for key in ["trackeff_vs_eta", "trackeff_vs_pT", "trackeff_vs_phi"]:
        saved.append(_plot(path_new, path_base, out_dir, key,
                           draw_eff, {}, ylim_main=(0, 1.05)))

    for key in ["nRecoTracks_vs_eta", "nRecoTracks_vs_pT"]:
        saved.append(_plot(path_new, path_base, out_dir, key,
                           draw_th2, {}))

    for key in ["nFakeTracks_vs_eta", "nFakeTracks_vs_pT"]:
        saved.append(_plot(path_new, path_base, out_dir, key,
                           draw_th2, {}))

    for key in ["nDuplicated_vs_eta", "nDuplicated_vs_pT", "nDuplicated_vs_phi"]:
        saved.append(_plot(path_new, path_base, out_dir, key,
                           draw_prof, {}))

    return saved

def explore(path):
    cn = classnames(path)
    for key, cls in cn.items():
        print(f"  {key:<55}  [{cls}]")
    return cn

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-file", default=DEFAULT_ROOT)
    parser.add_argument("--baseline",  default=DEFAULT_BASE)
    parser.add_argument("--out-dir",   default=DEFAULT_OUT)
    parser.add_argument("--explore-only", action="store_true")
    args = parser.parse_args()

    path_new  = Path(args.root_file)
    path_base = Path(args.baseline)
    out_dir   = Path(args.out_dir)

    for p in (path_new, path_base):
        if not p.exists():
            sys.exit(f"[error] File not found: {p}")

    print(f"\n{'='*65}")
    print(f"  A1 (new) : {path_new}")
    print(f"  Baseline : {path_base}")
    print(f"  Output   : {out_dir}")
    print(f"{'='*65}\n")

    cn = explore(path_new)
    print(f"\n  Total objects: {len(cn)}\n")

    if args.explore_only:
        print("[explore-only] Done.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    saved = plot_all(str(path_new), str(path_base), out_dir)
    print(f"\n  {len(saved)} figures saved.")

    print(f"\n[done] → {out_dir}/\n")


if __name__ == "__main__":
    main()
