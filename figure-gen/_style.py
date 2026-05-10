import matplotlib as mpl

TEXTWIDTH = 5.787

FIGSIZE_FULL   = (5.787, 3.576)
FIGSIZE_HALF   = (2.894, 1.788)
FIGSIZE_SQUARE = (2.894, 2.894)

FIGSIZE_DATASET_SINGLE = (6.0, 4.0)
FIGSIZE_DATASET_JOINT  = (7.0, 5.0)
FIGSIZE_DATASET_MULTI  = (8.0, 6.0)
# Sized so every Figure 4.2 panel scales by ~0.55x in LaTeX
# (a/b at 0.48\textwidth: 5"  -> 2.78" page; c/d at 0.95\textwidth:
# 10" -> 5.50" page). Keeps font sizes consistent across panels.
FIGSIZE_DATASET_HALFROW = (5.0, 3.0)
FIGSIZE_DATASET_FULLROW = (10.0, 3.0)
FIGSIZE_DATASET_FULLBIG = (10.0, 6.0)

FONT_SIZE    = 11
LABEL_SIZE   = 12
TITLE_SIZE   = 12
TICK_SIZE    = 10
LEGEND_SIZE  = 10
MARKER_SIZE  = 4
LINE_WIDTH   = 1.2

TIGHT_PAD   = 0.8
TIGHT_H_PAD = 1.0
TIGHT_W_PAD = 0.6

COLORS = {
    "Pixel":   "#2C6E97",
    "Strip":   "#F18F01",
    "good":    "#2E8B57",
    "bad":     "#D1495B",
    "neutral": "#000000",
}

mpl.rcParams.update({
    "font.size":           FONT_SIZE,
    "axes.labelsize":      LABEL_SIZE,
    "axes.titlesize":      TITLE_SIZE,
    "xtick.labelsize":     TICK_SIZE,
    "ytick.labelsize":     TICK_SIZE,
    "legend.fontsize":     LEGEND_SIZE,
    "lines.linewidth":     LINE_WIDTH,
    "lines.markersize":    MARKER_SIZE,
    "axes.prop_cycle":     mpl.cycler(color=list(COLORS.values())),
    "savefig.format":      "pdf",
    "savefig.dpi":         300,
    "savefig.bbox":        "tight",
    "pdf.fonttype":        42,
})
