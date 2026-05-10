#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")

from bootstrap_ci_helper import (
    summarize_event_mean_from_frame,
    format_mean_pm,
    bootstrap_geometric_mean_ratio_from_frames,
    format_ratio_ci,
)
from codeopts_helpers import (
    callgrind_variant_dir,
    find_latest_file,
    fmt_bignum,
    fmt_relative_change,
    load_all_global,
    load_all_local,
    parse_annotate_substring,
    run_callgrind_annotate,
    save_tex,
    subset,
    SAVE_DIR,
)


VARIANT      = "O1+O2"
OUTPUT_LABEL = "O1-2"

VARIANTS = ["Baseline", VARIANT]

DOUBLET_NAME  = "createDoubletsImpl"
DOUBLET_LABEL = r"\texttt{createDoubletsImpl}"
DOUBLET_TAG   = "LocalTime1"
DOUBLET_CG    = ["createDoublets"]

TRIPLET_NAME  = "createPixelTripletTopCandidates"
TRIPLET_LABEL = r"\texttt{createPixelTripletTopCandidates}"
TRIPLET_TAG   = "LocalTime2"
TRIPLET_CG    = ["createTripletTopCandidates"]

OUTPUT_FILE = SAVE_DIR / f"{OUTPUT_LABEL}PerformanceTable.tex"


def _timing(df_base, df_opt, col, seed_base, decimals=2):
    base = summarize_event_mean_from_frame(df_base, value_col=col, scale=1.0, seed=seed_base + 1)
    opt  = summarize_event_mean_from_frame(df_opt,  value_col=col, scale=1.0, seed=seed_base + 2)
    ratio = bootstrap_geometric_mean_ratio_from_frames(df_base, df_opt, value_col=col, seed=seed_base + 3)
    return (
        format_mean_pm(base, decimals),
        format_mean_pm(opt,  decimals),
        format_ratio_ci(ratio, 3),
    )


def _callgrind_annotated(geom: str, variant: str):
    # One annotate call per (geom, variant); reused for doublets and triplets.
    path = find_latest_file(
        callgrind_variant_dir(variant),
        f"{geom}Seeding2Callgrind.callgrind.*",
    )
    return run_callgrind_annotate(path)


def _cg_row(result: dict, event: str, scope: str, baseline: dict, opt: dict):
    b = baseline[event][scope]
    o = opt[event][scope]
    return fmt_bignum(b), fmt_bignum(o), fmt_relative_change(b, o)


def detector_rows(df_global, df_doublets, df_triplets, geom: str, seed_offset: int, title: str) -> list[str]:
    g_base, g_opt, g_rat = _timing(
        subset(df_global, geom, "Baseline"),
        subset(df_global, geom, VARIANT),
        "TIME_MS_PER_EVENT", seed_offset + 100,
    )
    d_base, d_opt, d_rat = _timing(
        subset(df_doublets, geom, "Baseline"),
        subset(df_doublets, geom, VARIANT),
        "AVERAGE_TIME_NS", seed_offset + 200,
    )
    t_base, t_opt, t_rat = _timing(
        subset(df_triplets, geom, "Baseline"),
        subset(df_triplets, geom, VARIANT),
        "AVERAGE_TIME_NS", seed_offset + 300,
    )

    text_baseline = _callgrind_annotated(geom, "Baseline")
    text_variant  = _callgrind_annotated(geom, VARIANT)

    doublet_baseline = parse_annotate_substring(text_baseline, DOUBLET_CG, events=("Ir", "Bcm"))
    doublet_variant  = parse_annotate_substring(text_variant,  DOUBLET_CG, events=("Ir", "Bcm"))
    triplet_baseline = parse_annotate_substring(text_baseline, TRIPLET_CG, events=("Ir", "Bcm"))
    triplet_variant  = parse_annotate_substring(text_variant,  TRIPLET_CG, events=("Ir", "Bcm"))

    has_bcm = ("Bcm" in doublet_baseline and "Bcm" in doublet_variant
               and "Bcm" in triplet_baseline and "Bcm" in triplet_variant)

    rows: list[str] = [
        r"    \rowcolor{gray!25}",
        rf"    \multicolumn{{5}}{{l}}{{\textbf{{{title}}}}} \\",
    ]
    zebra = [False]

    def emit(metric: str, base: str, opt: str, change: str):
        prefix = r"    \rowcolor{gray!15}" + "\n" if zebra[0] else "    "
        zebra[0] = not zebra[0]
        rows.append(f"{prefix}& {metric} & {base} & {opt} & {change} \\\\")

    emit(r"Global time/event [ms]",                 f"${g_base}$", f"${g_opt}$", f"${g_rat}$")
    emit(rf"{DOUBLET_LABEL} [ns]",                  f"${d_base}$", f"${d_opt}$", f"${d_rat}$")
    emit(rf"{TRIPLET_LABEL} [ns]",                  f"${t_base}$", f"${t_opt}$", f"${t_rat}$")

    emit(r"Global instructions (Ir)",               *_cg_row(None, "Ir", "global", doublet_baseline, doublet_variant))
    emit(rf"{DOUBLET_LABEL} (Ir)",                  *_cg_row(None, "Ir", "local",  doublet_baseline, doublet_variant))
    emit(rf"{TRIPLET_LABEL} (Ir)",                  *_cg_row(None, "Ir", "local",  triplet_baseline, triplet_variant))

    if has_bcm:
        emit(r"Global branch mispred.\ (Bcm)",      *_cg_row(None, "Bcm", "global", doublet_baseline, doublet_variant))
        emit(rf"{DOUBLET_LABEL} mispred.\ (Bcm)",   *_cg_row(None, "Bcm", "local",  doublet_baseline, doublet_variant))
        emit(rf"{TRIPLET_LABEL} mispred.\ (Bcm)",   *_cg_row(None, "Bcm", "local",  triplet_baseline, triplet_variant))

    return rows


def build_latex_table(df_global, df_doublets, df_triplets) -> str:
    lines: list[str] = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\begin{tabular}{llrrr}",
        r"    \toprule",
        rf"    \textbf{{Detector}} & \textbf{{Metric}} & \textbf{{Baseline}} & \textbf{{{VARIANT}}} & \textbf{{Speedup / Rel.\ change}} \\",
        r"    \midrule",
    ]
    lines += detector_rows(df_global, df_doublets, df_triplets, "Pixel", 0,    "Pixel detector")
    lines += detector_rows(df_global, df_doublets, df_triplets, "Strip", 1000, "Strip detector")
    lines += [r"    \bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()  # noqa: F841

    df_global   = load_all_global(VARIANTS)
    df_doublets = load_all_local(VARIANTS, csv_tag_for=DOUBLET_TAG, name_in_csv=DOUBLET_NAME)
    df_triplets = load_all_local(VARIANTS, csv_tag_for=TRIPLET_TAG, name_in_csv=TRIPLET_NAME)

    save_tex(OUTPUT_FILE, build_latex_table(df_global, df_doublets, df_triplets))
    print(f"Saved table to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
