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

RAW_DIR  = Path("raw-data/Results/Seeding3/RealCPUTime")
SAVE_DIR = Path("figures/Results/Seeding3/RealCPUTime")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

RUNS = default_runs()
METHODS = ["Seeding", "Seeding2", "Seeding3"]
TIMER_NAME = "Seeding"
OUTPUT_FILE = SAVE_DIR / "Seeding3PerformanceTable.tex"


def load_run(method: str, run: int) -> pd.DataFrame:
    path = RAW_DIR / f"RealCPUTime{method}_run{run}.csv"
    # data-gen may force Runs=1 (bare name) even when global runs > 1.
    if not path.exists():
        path = RAW_DIR / f"RealCPUTime{method}.csv"
    df = pd.read_csv(path)
    rows = df[df["NAME"] == TIMER_NAME].copy()
    if rows.empty:
        raise ValueError(f"No {TIMER_NAME!r} rows in {path}")
    rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
    rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
    rows["TIME_MS_PER_EVENT"] = rows["TIME_NS_PER_EVENT"] / 1e6
    rows["RUN"] = run
    rows["METHOD"] = method
    rows["SAMPLE_INDEX"] = range(1, len(rows) + 1)
    return rows


def load_all() -> pd.DataFrame:
    frames = []
    for method in METHODS:
        for run in range(1, RUNS + 1):
            frames.append(load_run(method, run))
    return pd.concat(frames, ignore_index=True)


def subset(df_all: pd.DataFrame, method: str) -> pd.DataFrame:
    return df_all[df_all["METHOD"] == method].copy()


def build_row(df_all: pd.DataFrame) -> tuple:
    df_s1 = subset(df_all, "Seeding")
    df_s2 = subset(df_all, "Seeding2")
    df_s3 = subset(df_all, "Seeding3")

    s1_mean = summarize_event_mean_from_frame(
        df_s1, value_col="TIME_MS_PER_EVENT", scale=1.0, seed=1,
    )
    s2_mean = summarize_event_mean_from_frame(
        df_s2, value_col="TIME_MS_PER_EVENT", scale=1.0, seed=2,
    )
    s3_mean = summarize_event_mean_from_frame(
        df_s3, value_col="TIME_MS_PER_EVENT", scale=1.0, seed=3,
    )
    sp_s2s1 = bootstrap_geometric_mean_ratio_from_frames(
        df_s1, df_s2, value_col="TIME_MS_PER_EVENT", seed=4,
    )
    sp_s3s1 = bootstrap_geometric_mean_ratio_from_frames(
        df_s1, df_s3, value_col="TIME_MS_PER_EVENT", seed=5,
    )
    sp_s3s2 = bootstrap_geometric_mean_ratio_from_frames(
        df_s2, df_s3, value_col="TIME_MS_PER_EVENT", seed=6,
    )

    return (
        format_mean_pm(s1_mean, 1),
        format_mean_pm(s2_mean, 1),
        format_mean_pm(s3_mean, 1),
        format_ratio_ci(sp_s2s1, 3),
        format_ratio_ci(sp_s3s1, 3),
        format_ratio_ci(sp_s3s2, 3),
    )


def build_latex_table(df_all: pd.DataFrame) -> str:
    s1, s2, s3, sp_s2s1, sp_s3s1, sp_s3s2 = build_row(df_all)

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\begin{tabular}{lrrr}",
        r"\toprule",
        (
            r"\textbf{Configuration} & "
            r"\textbf{Time per event [ms]} & "
            r"\textbf{Speedup vs.\ S1} & "
            r"\textbf{Speedup vs.\ S2} \\"
        ),
        r"\midrule",
        rf"\texttt{{Seeding}}  (S1) & ${s1}$ & --- & --- \\",
        r"\rowcolor{gray!15}",
        rf"\texttt{{Seeding2}} (S2) & ${s2}$ & ${sp_s2s1}$ & --- \\",
        rf"\texttt{{Seeding3}} (S3) & ${s3}$ & ${sp_s3s1}$ & ${sp_s3s2}$ \\",
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
