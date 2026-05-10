#!/usr/bin/env python3


from __future__ import annotations

import numpy as np
import pandas as pd

BOOTSTRAP_SAMPLES = 10_000
RNG_SEED = 42


def _rng(seed: int | None = None) -> np.random.Generator:
    return np.random.default_rng(RNG_SEED if seed is None else seed)


def event_level_means(
    df: pd.DataFrame,
    value_col: str,
    event_col: str = "SAMPLE_INDEX",
) -> np.ndarray:
    return (
        df.groupby(event_col)[value_col]
        .mean()
        .sort_index()
        .to_numpy(dtype=float)
    )


def event_level_paired_means(
    df_baseline: pd.DataFrame,
    df_optimized: pd.DataFrame,
    value_col: str,
    event_col: str = "SAMPLE_INDEX",
) -> tuple[np.ndarray, np.ndarray]:
    # Inner-join keeps only events present in both inputs.
    base = (
        df_baseline.groupby(event_col)[value_col]
        .mean()
        .rename("BASE")
    )
    opt = (
        df_optimized.groupby(event_col)[value_col]
        .mean()
        .rename("OPT")
    )

    merged = pd.concat([base, opt], axis=1, join="inner").sort_index()

    return (
        merged["BASE"].to_numpy(dtype=float),
        merged["OPT"].to_numpy(dtype=float),
    )


def bootstrap_mean(
    values: np.ndarray | list[float],
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int | None = None,
) -> dict:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("values must be a non-empty 1D array")

    rng = _rng(seed)
    n = len(values)
    boots = np.empty(n_boot, dtype=float)

    for b in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        boots[b] = values[idx].mean()

    mean = float(values.mean())
    ci_low, ci_high = np.percentile(boots, [2.5, 97.5])
    half_width = 0.5 * (ci_high - ci_low)

    return {
        "mean": mean,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "half_width": float(half_width),
        "bootstrap_samples": boots,
    }


def bootstrap_geometric_mean_ratio_from_event_means(
    baseline_event_means: np.ndarray | list[float],
    optimized_event_means: np.ndarray | list[float],
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int | None = None,
) -> dict:
    # Per-event speedup S_i = base_i / opt_i, summarised as exp(mean(log S_i)).
    # Bootstrap resamples events with replacement.
    base = np.asarray(baseline_event_means, dtype=float)
    opt = np.asarray(optimized_event_means, dtype=float)

    if base.ndim != 1 or opt.ndim != 1 or len(base) == 0 or len(opt) == 0:
        raise ValueError("baseline and optimized must be non-empty 1D arrays")
    if len(base) != len(opt):
        raise ValueError("baseline and optimized must have the same length")
    if np.any(base <= 0) or np.any(opt <= 0):
        raise ValueError("all values must be positive to compute log-ratios")

    log_ratios = np.log(base) - np.log(opt)
    point = float(np.exp(log_ratios.mean()))

    rng = _rng(seed)
    n = len(log_ratios)
    boots = np.empty(n_boot, dtype=float)

    for b in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        boots[b] = np.exp(log_ratios[idx].mean())

    ci_low, ci_high = np.percentile(boots, [2.5, 97.5])

    return {
        "ratio": point,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "bootstrap_samples": boots,
    }


def bootstrap_geometric_mean_ratio_from_frames(
    df_baseline: pd.DataFrame,
    df_optimized: pd.DataFrame,
    value_col: str,
    event_col: str = "SAMPLE_INDEX",
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int | None = None,
) -> dict:
    base, opt = event_level_paired_means(
        df_baseline=df_baseline,
        df_optimized=df_optimized,
        value_col=value_col,
        event_col=event_col,
    )

    return bootstrap_geometric_mean_ratio_from_event_means(
        baseline_event_means=base,
        optimized_event_means=opt,
        n_boot=n_boot,
        seed=seed,
    )


def summarize_event_mean_from_frame(
    df: pd.DataFrame,
    value_col: str,
    event_col: str = "SAMPLE_INDEX",
    scale: float = 1.0,
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int | None = None,
) -> dict:
    values = event_level_means(df=df, value_col=value_col, event_col=event_col) * scale
    return bootstrap_mean(values, n_boot=n_boot, seed=seed)


def summarize_total_from_frame(
    df: pd.DataFrame,
    value_col: str,
    event_col: str = "SAMPLE_INDEX",
    scale: float = 1.0,
    n_boot: int = BOOTSTRAP_SAMPLES,
    seed: int | None = None,
) -> dict:
    # total = N * mean(event_value); bootstrap over events, then scale by N.
    event_values = event_level_means(df=df, value_col=value_col, event_col=event_col)
    n_events = len(event_values)
    return bootstrap_mean(
        event_values * scale * n_events,
        n_boot=n_boot,
        seed=seed,
    )


def format_mean_pm(result: dict, decimals: int = 1) -> str:
    # Math-mode fragment; caller wraps in $...$.
    return f'{result["mean"]:.{decimals}f} \\pm {result["half_width"]:.{decimals}f}'


def format_ratio_ci(result: dict, decimals: int = 2) -> str:
    # Math-mode fragment; caller wraps in $...$.
    return (
        f'{result["ratio"]:.{decimals}f}\\,'
        f'[{result["ci_low"]:.{decimals}f},\\,{result["ci_high"]:.{decimals}f}]'
    )
