#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
sys.path.insert(0, "data-gen")

import pandas as pd

from bootstrap_ci_helper import (
    summarize_event_mean_from_frame,
    bootstrap_geometric_mean_ratio_from_frames,
    format_mean_pm,
    format_ratio_ci,
)
from workflow import default_runs

RAW_DIR = Path("raw-data/Results/Baseline/RealCPUTime")
SAVE_DIR = Path("figures/Results/Baseline/RealCPUTime")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

RUNS = default_runs()
METHODS = ["Seeding", "Seeding2"]
GEOMS = ["Pixel", "Strip"]
TIMER_NAME = "Seeding"

OUTPUT_FILE = SAVE_DIR / "BaselinePerformanceTable.tex"


def load_run(geom: str, method: str, run: int) -> pd.DataFrame:
    path = RAW_DIR / f"{geom}RealCPUTime{method}_run{run}.csv"
    # data-gen may force Runs=1 (bare name) even when global runs > 1.
    if not path.exists():
        path = RAW_DIR / f"{geom}RealCPUTime{method}.csv"
    df = pd.read_csv(path)
    rows = df[df["NAME"] == TIMER_NAME].copy()
    if rows.empty:
        raise ValueError(f"No {TIMER_NAME!r} rows in {path}")
    rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
    rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
    rows["TIME_MS_PER_EVENT"] = rows["TIME_NS_PER_EVENT"] / 1e6
    rows["RUN"] = run
    rows["GEOM"] = geom
    rows["METHOD"] = method
    rows["SAMPLE_INDEX"] = range(1, len(rows) + 1)
    return rows


def load_all() -> pd.DataFrame:
    frames = []
    for geom in GEOMS:
        for method in METHODS:
            for run in range(1, RUNS + 1):
                frames.append(load_run(geom, method, run))
    return pd.concat(frames, ignore_index=True)


def subset(df_all: pd.DataFrame, geom: str, method: str) -> pd.DataFrame:
    return df_all[
        (df_all["GEOM"] == geom) &
        (df_all["METHOD"] == method)
    ].copy()


def throughput_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["EVENTS_PER_SECOND"] = 1000.0 / out["TIME_MS_PER_EVENT"]
    return out


def build_geometry_row(df_all: pd.DataFrame, geom: str, seed_offset: int) -> dict:
    df_base = subset(df_all, geom, "Seeding")
    df_opt  = subset(df_all, geom, "Seeding2")

    base_time = summarize_event_mean_from_frame(
        df_base, value_col="TIME_MS_PER_EVENT", scale=1.0, seed=seed_offset + 1,
    )
    opt_time = summarize_event_mean_from_frame(
        df_opt,  value_col="TIME_MS_PER_EVENT", scale=1.0, seed=seed_offset + 2,
    )

    base_tp = summarize_event_mean_from_frame(
        throughput_frame(df_base), value_col="EVENTS_PER_SECOND", scale=1.0,
        seed=seed_offset + 3,
    )
    opt_tp = summarize_event_mean_from_frame(
        throughput_frame(df_opt), value_col="EVENTS_PER_SECOND", scale=1.0,
        seed=seed_offset + 4,
    )

    speedup = bootstrap_geometric_mean_ratio_from_frames(
        df_base, df_opt, value_col="TIME_MS_PER_EVENT", seed=seed_offset + 5,
    )

    return {
        "base_time": format_mean_pm(base_time, 1),
        "opt_time":  format_mean_pm(opt_time, 1),
        "base_tp":   format_mean_pm(base_tp, 2),
        "opt_tp":    format_mean_pm(opt_tp, 2),
        "speedup":   format_ratio_ci(speedup, 3),
    }


def build_latex_table(df_all: pd.DataFrame) -> str:
    pix = build_geometry_row(df_all, "Pixel", 0)
    stp = build_geometry_row(df_all, "Strip", 1000)

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\setlength{\tabcolsep}{5pt}",
        r"\footnotesize",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"\textbf{Detector} & "
        r"\multicolumn{2}{c}{\textbf{Time [ms/event]}} & "
        r"\multicolumn{2}{c}{\textbf{Throughput [events/s]}} & "
        r"\textbf{Speedup [95\% CI]} \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r" & \texttt{Seeding} & \texttt{Seeding2} & "
        r"\texttt{Seeding} & \texttt{Seeding2} & \\",
        r"\midrule",
        r"\rowcolor{gray!15}",
        rf"Pixel & ${pix['base_time']}$ & ${pix['opt_time']}$ & "
        rf"${pix['base_tp']}$ & ${pix['opt_tp']}$ & ${pix['speedup']}$ \\",
        rf"Strip & ${stp['base_time']}$ & ${stp['opt_time']}$ & "
        rf"${stp['base_tp']}$ & ${stp['opt_tp']}$ & ${stp['speedup']}$ \\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
    ]

    return "\n".join(lines)


def main():
    df_all = load_all()
    OUTPUT_FILE.write_text(build_latex_table(df_all))


if __name__ == "__main__":
    main()
