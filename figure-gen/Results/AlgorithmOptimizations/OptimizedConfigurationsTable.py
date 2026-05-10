#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, "figure-gen")
sys.path.insert(0, "data-gen")

import pandas as pd
import yaml

from bootstrap_ci_helper import (
    summarize_event_mean_from_frame,
    format_mean_pm,
    bootstrap_geometric_mean_ratio_from_frames,
    format_ratio_ci,
)
from workflow import default_runs

REPO    = Path(__file__).resolve().parents[3]
RAW     = REPO / "raw-data" / "Results" / "AlgorithmOptimizations"
CONFIGS = REPO / "configs"
OUT     = REPO / "figures" / "Results" / "AlgorithmOptimizations" / "OptimizedConfigurationsTable.tex"

RUNS = default_runs()
TIMER_NAME = "Seeding"

# (header, raw-data subdir, yaml stem). Best is rightmost so it reads
# as the visual destination of the comparison; it also gets a light-
# grey column fill via columncolor in the tabular spec.
COLUMNS = [
    (r"\textbf{Max Efficiency}", "MaxEfficiency", "parameter_optimization/winners/max_efficiency"),
    (r"\textbf{Fastest}",        "Fastest",       "parameter_optimization/winners/fastest"),
    (r"\textbf{Best}",           "Best",          "parameter_optimization/winners/best"),
]


def _load_timing_run(path, run):
    df = pd.read_csv(path)
    rows = df[df["NAME"] == TIMER_NAME].copy()
    if rows.empty:
        raise ValueError(f"No {TIMER_NAME!r} rows in {path}")
    rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
    rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
    rows["TIME_MS_PER_EVENT"] = rows["TIME_NS_PER_EVENT"] / 1e6
    rows["RUN"] = run
    rows["SAMPLE_INDEX"] = range(1, len(rows) + 1)
    return rows


def load_timing(name_glob):
    frames = []
    for r in range(1, RUNS + 1):
        path = name_glob(r)
        # data-gen may force Runs=1 (bare name) even when global runs > 1.
        if not path.exists():
            unsuffixed = path.with_name(path.name.replace(f"_run{r}", ""))
            if unsuffixed.exists():
                path = unsuffixed
        frames.append(_load_timing_run(path, r))
    return pd.concat(frames, ignore_index=True)


def load_metrics(path):
    return pd.read_csv(path).iloc[0]


def load_yaml(name):
    return yaml.safe_load((CONFIGS / f"{name}.yaml").read_text()) or {}


def fmt_neighbors(value):
    if not isinstance(value, list) or not value:
        return "-"
    first = value[0]
    if all(pair == first for pair in value):
        a, b = first
        return f"$[{a}, {b}]\\!\\times\\!{len(value)}$"
    return f"{len(value)} entries"


def fmt_param(cfg, key, default="default"):
    if key not in cfg:
        return default
    val = cfg[key]
    if isinstance(val, bool):
        return r"\texttt{true}" if val else r"\texttt{false}"
    if isinstance(val, float):
        return f"{val:g}"
    if isinstance(val, list):
        return fmt_neighbors(val)
    return str(val)


# (label, yaml key, cylindrical default). Cyl shows "--" when None
# because the parameter is a Spherical-only override.
PARAM_ROWS = [
    (r"$\Delta\eta_{\max}$",      "deltaEtaMax",              None),
    (r"phiBinDeflectionCoverage", "phiBinDeflectionCoverage", None),
    (r"etaBinNeighborsBottom",    "etaBinNeighborsBottom",    None),
    (r"etaBinNeighborsTop",       "etaBinNeighborsTop",       None),
    (r"maxSeedsPerSpM",           "maxSeedsPerSpM",           None),
    (r"impactMax",                "impactMax",                None),
]


def build_table():
    cfgs = [load_yaml(yaml_name) for _, _, yaml_name in COLUMNS]

    m_cyl = load_metrics(
        RAW / "ParameterOptimization" / "Baseline" / "ParamOptimizationMetrics.csv"
    )
    metric_dfs = [
        load_metrics(RAW / "OptimizedConfigurations" / subdir / "Metrics.csv")
        for _, subdir, _ in COLUMNS
    ]

    df_cyl = load_timing(lambda r: RAW / "Timing" / f"CylindricalTiming_run{r}.csv")
    timing_dfs = [
        load_timing(
            lambda r, sd=subdir: RAW / "OptimizedConfigurations" / sd / f"Timing_run{r}.csv"
        )
        for _, subdir, _ in COLUMNS
    ]

    t_cyl = summarize_event_mean_from_frame(df_cyl, value_col="TIME_MS_PER_EVENT", seed=10)
    t_columns = [
        summarize_event_mean_from_frame(df, value_col="TIME_MS_PER_EVENT", seed=12 + i)
        for i, df in enumerate(timing_dfs)
    ]
    s_columns = [
        bootstrap_geometric_mean_ratio_from_frames(
            df_cyl, df, value_col="TIME_MS_PER_EVENT", seed=21 + i)
        for i, df in enumerate(timing_dfs)
    ]

    def _bold(s, win):
        return rf"\textbf{{{s}}}" if win else s

    def _winner_idx(values, higher_is_better):
        return (max if higher_is_better else min)(
            range(len(values)), key=lambda i: values[i]
        )

    def fmt_pct(x):
        return rf"{x * 100:.1f}\%"

    def fmt_delta_pp(sph, cyl, *, higher_is_better):
        delta_pp = (sph - cyl) * 100
        is_better = (delta_pp >= 0) if higher_is_better else (delta_pp <= 0)
        color = "deltagood" if is_better else "deltabad"
        sign = "+" if delta_pp >= 0 else "-"
        return (rf"{{\scriptsize\textcolor{{{color}}}"
                rf"{{({sign}{abs(delta_pp):.1f})}}}}")

    def fmt_time_ci(result, decimals=1):
        return (
            f'{result["mean"]:.{decimals}f}\\,'
            f'[{result["ci_low"]:.{decimals}f},\\,'
            f'{result["ci_high"]:.{decimals}f}]'
        )

    def fmt_speedup(result):
        return f"${format_ratio_ci(result, decimals=2)}$"

    h_cyl   = r"\textbf{Cylindrical}"
    headers = [hdr for hdr, _, _ in COLUMNS]

    n_data_cols  = 1 + len(COLUMNS)
    n_total_cols = 1 + n_data_cols
    multicol = rf"\multicolumn{{{n_total_cols}}}{{l}}"

    col_spec = (
        "l "
        + "c " * (1 + len(COLUMNS) - 1)
        + ">{\\columncolor{bestcol}}c"
    )

    sph_first_col = 3
    sph_last_col  = sph_first_col + len(COLUMNS) - 1
    grouping_row = (
        r"     & & "
        + rf"\multicolumn{{{len(COLUMNS)}}}{{c}}"
        + r"{\textit{Spherical configurations}} \\"
    )
    cmidrule = rf"    \cmidrule(lr){{{sph_first_col}-{sph_last_col}}}"

    lines = [
        r"\definecolor{bestcol}{gray}{0.92}",
        r"\definecolor{deltagood}{rgb}{0.10, 0.50, 0.20}",
        r"\definecolor{deltabad}{rgb}{0.65, 0.10, 0.10}",
        r"\renewcommand{\arraystretch}{1.25}",
        r"\resizebox{\textwidth}{!}{%",
        rf"\begin{{tabular}}{{{col_spec}}}",
        r"    \toprule",
        grouping_row,
        cmidrule,
        rf"    \textbf{{Quantity}} & {h_cyl} & " + " & ".join(headers) + r" \\",
        r"    \midrule",
        rf"    {multicol}{{\textit{{Parameter overrides (vs.\ runner defaults)}}}} \\",
    ]

    for label, key, cyl_default in PARAM_ROWS:
        cyl_cell = "--" if cyl_default is None else str(cyl_default)
        cells = [cyl_cell] + [fmt_param(cfg, key) for cfg in cfgs]
        lines.append(rf"    {label} & " + " & ".join(cells) + r" \\")

    def metric_row(label, key, *, higher_is_better):
        cyl_val   = float(m_cyl[key])
        sph_vals  = [float(m[key]) for m in metric_dfs]
        win_idx   = _winner_idx(sph_vals, higher_is_better)
        cyl_cell  = fmt_pct(cyl_val)
        sph_cells = [
            (_bold(fmt_pct(v), i == win_idx)
             + r"\,"
             + fmt_delta_pp(v, cyl_val, higher_is_better=higher_is_better))
            for i, v in enumerate(sph_vals)
        ]
        return rf"    {label} & {cyl_cell} & " + " & ".join(sph_cells) + r" \\"

    lines += [
        r"    \midrule",
        metric_row("Efficiency",      "seeding_particle_efficiency", higher_is_better=True),
        metric_row("Fake ratio",      "seeding_particle_fake_ratio", higher_is_better=False),
        metric_row("Duplicate ratio", "seeding_particle_duplicate_ratio", higher_is_better=False),
        r"    \midrule",
        rf"    {multicol}{{\textit{{Wall-clock per event}}}} \\",
    ]

    sph_t_means = [t["mean"] for t in t_columns]
    t_winner    = _winner_idx(sph_t_means, higher_is_better=False)
    t_cells     = [
        _bold(f"${fmt_time_ci(t)}$", i == t_winner)
        for i, t in enumerate(t_columns)
    ]
    lines.append(
        rf"    Time [ms] & ${fmt_time_ci(t_cyl)}$ & " + " & ".join(t_cells) + r" \\"
    )

    sph_s_ratios = [s["ratio"] for s in s_columns]
    s_winner     = _winner_idx(sph_s_ratios, higher_is_better=True)
    s_cells      = [
        _bold(fmt_speedup(s), i == s_winner) for i, s in enumerate(s_columns)
    ]
    lines += [
        rf"    Speedup vs.\ Cylindrical & -- & " + " & ".join(s_cells) + r" \\",
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]
    return "\n".join(lines)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_table())
    print(f"Saved table to {OUT}")


if __name__ == "__main__":
    main()
