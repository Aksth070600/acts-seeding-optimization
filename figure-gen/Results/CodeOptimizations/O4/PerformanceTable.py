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


VARIANT     = "O4"
VARIANTS    = ["Baseline", VARIANT]
LOCAL_NAME  = "createDoubletsImpl"
LOCAL_LABEL = r"\texttt{createDoubletsImpl}"
LOCAL_TAG   = "LocalTime1"

CALLGRIND_TARGETS = {
    "Pixel": ["createDoublets"],
    "Strip": ["createDoublets"],
}

OUTPUT_FILE = SAVE_DIR / f"{VARIANT}PerformanceTable.tex"


def _timing(df_base, df_opt, col, seed_base, decimals=2):
    base = summarize_event_mean_from_frame(df_base, value_col=col, scale=1.0, seed=seed_base + 1)
    opt  = summarize_event_mean_from_frame(df_opt,  value_col=col, scale=1.0, seed=seed_base + 2)
    ratio = bootstrap_geometric_mean_ratio_from_frames(df_base, df_opt, value_col=col, seed=seed_base + 3)
    return (
        format_mean_pm(base, decimals),
        format_mean_pm(opt,  decimals),
        format_ratio_ci(ratio, 3),
    )


def _callgrind(geom: str):
    out = {}
    for variant in VARIANTS:
        path = find_latest_file(
            callgrind_variant_dir(variant),
            f"{geom}Seeding2Callgrind.callgrind.*",
        )
        out[variant] = parse_annotate_substring(
            run_callgrind_annotate(path),
            CALLGRIND_TARGETS[geom],
            events=("Ir", "Bcm"),
        )
    return out


def _cg_row(cg: dict, event: str, scope: str):
    b = cg["Baseline"][event][scope]
    o = cg[VARIANT][event][scope]
    return fmt_bignum(b), fmt_bignum(o), fmt_relative_change(b, o)


def detector_rows(df_global, df_local, geom: str, seed_offset: int, title: str) -> list[str]:
    g_base, g_opt, g_rat = _timing(
        subset(df_global, geom, "Baseline"),
        subset(df_global, geom, VARIANT),
        "TIME_MS_PER_EVENT", seed_offset + 100,
    )
    l_base, l_opt, l_rat = _timing(
        subset(df_local, geom, "Baseline"),
        subset(df_local, geom, VARIANT),
        "AVERAGE_TIME_NS", seed_offset + 200,
    )
    cg = _callgrind(geom)
    has_bcm = "Bcm" in cg["Baseline"] and "Bcm" in cg[VARIANT]

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
    emit(rf"{LOCAL_LABEL} [ns]",                    f"${l_base}$", f"${l_opt}$", f"${l_rat}$")
    emit(r"Global instructions (Ir)",               *_cg_row(cg, "Ir", "global"))
    emit(rf"{LOCAL_LABEL} (Ir)",                    *_cg_row(cg, "Ir", "local"))
    if has_bcm:
        emit(r"Global branch mispred.\ (Bcm)",      *_cg_row(cg, "Bcm", "global"))
        emit(rf"{LOCAL_LABEL} mispred.\ (Bcm)",     *_cg_row(cg, "Bcm", "local"))

    return rows


def build_latex_table(df_global, df_local) -> str:
    lines: list[str] = [
        r"\renewcommand{\arraystretch}{1.4}",
        # Plain tabular -- no \resizebox auto-fit -- so the text
        # renders at the document's \normalsize rather than getting
        # compressed to fit \textwidth.

        r"\begin{tabular}{llrrr}",
        r"    \toprule",
        rf"    \textbf{{Detector}} & \textbf{{Metric}} & \textbf{{Baseline}} & \textbf{{{VARIANT}}} & \textbf{{Speedup / Rel.\ change}} \\",
        r"    \midrule",
    ]
    lines += detector_rows(df_global, df_local, "Pixel", 0,    "Pixel detector")
    lines += detector_rows(df_global, df_local, "Strip", 1000, "Strip detector")
    lines += [r"    \bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()  # noqa: F841

    df_global = load_all_global(VARIANTS)
    df_local  = load_all_local(VARIANTS, csv_tag_for=LOCAL_TAG, name_in_csv=LOCAL_NAME)

    save_tex(OUTPUT_FILE, build_latex_table(df_global, df_local))
    print(f"Saved table to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
