from __future__ import annotations

from pathlib import Path
import _style as style

FIGURES = Path("figures")
RAW = Path("raw-data")


def figures_dir(*parts: str) -> Path:
    p = FIGURES.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def raw_dir(*parts: str) -> Path:
    return RAW.joinpath(*parts)


def save_figure(fig, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)


def write_latex(path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content)


def load_runs(dir_path, filename_fmt: str, runs: int, **fmt_kwargs):
    import pandas as pd

    frames = []
    for run in range(1, runs + 1):
        path = Path(dir_path) / filename_fmt.format(run=run, **fmt_kwargs)
        if not path.exists() and runs == 1:
            unsuffixed = filename_fmt.replace("_run{run}", "").format(run=run, **fmt_kwargs)
            fallback = Path(dir_path) / unsuffixed
            if fallback.exists():
                path = fallback
        df = pd.read_csv(path)
        df["RUN"] = run
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
