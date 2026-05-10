from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd

sys.path.insert(0, "data-gen")
from workflow import default_runs  # noqa: E402

RAW_DIR           = Path("raw-data/Results/CodeOptimizations")
CALLGRIND_RAW_DIR = Path("raw-data/Results/CodeOptimizations")
SAVE_DIR          = Path("figures/Results/CodeOptimizations")

RUNS  = default_runs()
GEOMS = ["Pixel", "Strip"]

VARIANT_SUBDIRS: dict[str, str] = {
    "Baseline": "clean",
    "O1":       "O1/clean",
    "O1-2":     "O1-2/clean",
    "O1+O2":    "O1-2/clean",
    "O2":       "O2/clean",
    "O3":       "O3/clean",
    "O4":       "O4/clean",
}


def variant_dir(variant: str) -> Path:
    try:
        return RAW_DIR / VARIANT_SUBDIRS[variant]
    except KeyError as exc:
        raise ValueError(f"Unknown variant: {variant}") from exc


def callgrind_variant_dir(variant: str) -> Path:
    try:
        return CALLGRIND_RAW_DIR / VARIANT_SUBDIRS[variant]
    except KeyError as exc:
        raise ValueError(f"Unknown variant: {variant}") from exc

TIMER_NAME = "Seeding"

def load_global_run(geom: str, variant: str, run: int) -> pd.DataFrame:
    path = variant_dir(variant) / f"{geom}SeedingGlobalTime_run{run}.csv"
    if not path.exists():
        path = variant_dir(variant) / f"{geom}SeedingGlobalTime.csv"
    df = pd.read_csv(path)

    rows = df[df["NAME"] == TIMER_NAME].copy()
    if rows.empty:
        raise ValueError(f"No {TIMER_NAME!r} rows in {path}")

    rows = rows.sort_values("COUNT", kind="stable").reset_index(drop=True)
    rows["TIME_NS_PER_EVENT"] = rows["TIME_NS"].diff().fillna(rows["TIME_NS"])
    rows["TIME_MS_PER_EVENT"] = rows["TIME_NS_PER_EVENT"] / 1e6
    rows["RUN"] = run
    rows["SAMPLE_INDEX"] = range(1, len(rows) + 1)
    rows["GEOM"] = geom
    rows["VARIANT"] = variant
    return rows


def load_all_global(variants: Iterable[str]) -> pd.DataFrame:
    frames = [
        load_global_run(g, v, r)
        for g in GEOMS for v in variants for r in range(1, RUNS + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def load_local_run(
    geom: str,
    variant: str,
    run: int,
    *,
    csv_tag: str,
    name_in_csv: str,
) -> pd.DataFrame:
    path = variant_dir(variant) / f"{geom}Seeding{csv_tag}_run{run}.csv"
    if not path.exists():
        path = variant_dir(variant) / f"{geom}Seeding{csv_tag}.csv"
    df = pd.read_csv(path)

    rows = df[df["NAME"] == name_in_csv].copy()
    if rows.empty:
        raise ValueError(f"No {name_in_csv!r} rows in {path}")

    return pd.DataFrame({
        "NAME":            [name_in_csv],
        "AVERAGE_TIME_NS": [rows["AVERAGE_TIME_NS"].mean()],
        "RUN":             [run],
        "SAMPLE_INDEX":    [run],
        "GEOM":            [geom],
        "VARIANT":         [variant],
    })


def load_all_local(
    variants: Iterable[str],
    *,
    csv_tag_for: "dict[str, str] | str",
    name_in_csv: str,
) -> pd.DataFrame:
    def tag(v: str) -> str:
        return csv_tag_for if isinstance(csv_tag_for, str) else csv_tag_for[v]

    frames = [
        load_local_run(g, v, r, csv_tag=tag(v), name_in_csv=name_in_csv)
        for g in GEOMS for v in variants for r in range(1, RUNS + 1)
    ]
    return pd.concat(frames, ignore_index=True)


def load_physics_metrics(variant: str) -> pd.Series:
    path = variant_dir(variant) / "Seeding2PhysicsMetrics.csv"
    return pd.read_csv(path).iloc[0]


def subset(df_all: pd.DataFrame, geom: str, variant: str) -> pd.DataFrame:
    return df_all[
        (df_all["GEOM"] == geom) &
        (df_all["VARIANT"] == variant)
    ].copy()


def run_callgrind_annotate(path: str | Path) -> str:
    try:
        result = subprocess.run(
            ["callgrind_annotate", "--inclusive=no", "--auto=no", str(path)],
            check=True, capture_output=True, text=True,
        )
        return result.stdout
    except FileNotFoundError:
        print("Error: callgrind_annotate not found in PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"Error running callgrind_annotate on {path}", file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        sys.exit(1)


def detect_event_columns(text: str) -> list[str]:
    for line in text.splitlines():
        if re.match(r'^\s*Ir\s+(?:Dr|I1mr)', line):
            return line.split()
    return ["Ir"]


def _split_row(line: str) -> tuple[list[int], str | None]:
    clean = re.sub(r'\s*\([^)]*%\s*\)', '', line).strip()
    tokens = clean.split()
    counts: list[int] = []
    for i, tok in enumerate(tokens):
        if tok == '.':
            counts.append(0)
        elif re.match(r'^[\d,]*\d[\d,]*$', tok):
            counts.append(int(tok.replace(',', '')))
        else:
            return counts, ' '.join(tokens[i:])
    return counts, None


def _read_program_totals(line: str) -> list[int]:
    part = line[:line.index('PROGRAM TOTALS')]
    clean = re.sub(r'\s*\([^)]*%\s*\)', '', part).strip()
    totals: list[int] = []
    for tok in clean.split():
        if tok == '.':
            totals.append(0)
        elif re.match(r'^[\d,]+$', tok):
            totals.append(int(tok.replace(',', '')))
    return totals


_FUNCTION_TABLE_ROW = re.compile(r"^[^\s:]+:[^:]")


def _is_function_table_row(symbol: str) -> bool:
    # Defence in depth on top of --auto=no: skip call-edge ("=>") rows
    # (inclusive cost, double-counts) and auto-annotated source-line rows
    # (no leading "file:" prefix).
    sym = symbol.lstrip()
    if sym.startswith("=>"):
        return False
    return bool(_FUNCTION_TABLE_ROW.match(sym))


def _parse_annotate(
    text: str,
    match,
    events: Iterable[str],
) -> dict:
    event_columns = detect_event_columns(text)
    interesting: dict[str, int] = {e: event_columns.index(e) for e in events if e in event_columns}
    data: dict = {e: {"global": None, "local": 0, "matched_rows": []} for e in interesting}

    in_table = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if 'PROGRAM TOTALS' in line:
            totals = _read_program_totals(line)
            for e, idx in interesting.items():
                if idx < len(totals):
                    data[e]["global"] = totals[idx]
            continue

        if 'file:function' in line:
            in_table = True
            continue
        if not in_table or re.match(r'^[-\s]*$', line):
            continue

        counts, symbol = _split_row(line)
        if symbol is None or not _is_function_table_row(symbol) or not match(symbol):
            continue

        for e, idx in interesting.items():
            if idx < len(counts):
                data[e]["local"] += counts[idx]
                data[e]["matched_rows"].append((counts[idx], symbol))

    for e, d in data.items():
        if d["global"] is None:
            raise ValueError(
                f"Could not find PROGRAM TOTALS count for {e}. "
                f"Detected columns: {event_columns}. "
                f"Ensure Callgrind was run with --branch-sim=yes if you need Bcm."
            )
        if d["global"] is not None and d["local"] > d["global"]:
            raise ValueError(
                f"Local {e} count ({d['local']:,}) exceeds PROGRAM TOTALS "
                f"({d['global']:,}). The matcher is picking up rows it "
                f"shouldn't be. Matched rows:\n  "
                + "\n  ".join(f"{c:>15,}  {s}" for c, s in d["matched_rows"])
            )
    return data


def parse_annotate_substring(
    text: str,
    local_targets: Iterable[str],
    events: Iterable[str] = ("Ir", "Bcm"),
) -> dict:
    targets = list(local_targets)
    return _parse_annotate(text, lambda s: any(t in s for t in targets), events)


def parse_annotate_prefix(
    text: str,
    exact_prefixes: Iterable[str],
    events: Iterable[str] = ("Ir",),
) -> dict:
    prefixes = list(exact_prefixes)
    return _parse_annotate(text, lambda s: any(s.startswith(p) for p in prefixes), events)


def find_latest_file(directory: Path, pattern: str) -> Path:
    matches = list(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No files matching {pattern} in {directory}")
    return max(matches, key=lambda p: p.stat().st_mtime)

def fmt_bignum(n: int) -> str:
    if n >= 1e9:
        return f"${n/1e9:.3f} \\times 10^{{9}}$"
    if n >= 1e6:
        return f"${n/1e6:.2f} \\times 10^{{6}}$"
    return f"${n:,}$".replace(",", "{,}")


def fmt_relative_change(baseline: int, opt: int, decimals: int = 2) -> str:
    if baseline == 0:
        return "$-$"
    pct = (opt - baseline) / baseline * 100
    sign = "+" if pct > 0 else ""
    return f"${sign}{pct:.{decimals}f}\\%$"


def fmt_latex_int(n: int) -> str:
    return f"{n:,}".replace(",", r"\,")


def fmt_latex_percent(x: float, decimals: int = 2) -> str:
    sign = "+" if x >= 0 else ""
    return f"{sign}{x*100:.{decimals}f}\\%"


def save_tex(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content)
