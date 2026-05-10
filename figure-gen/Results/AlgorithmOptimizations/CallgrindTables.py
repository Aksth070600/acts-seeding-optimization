#!/usr/bin/env python3

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# (display label, callgrind symbol substring). The substrings differ from
# the labels because createDoubletsImpl is inlined into createDoublets,
# and the Pixel/Strip create*TripletTopCandidates names are templated
# specialisations of createTripletTopCandidates.
FUNCTION_PATTERNS = [
    ("createDoubletsImpl",              "createDoublets"),
    ("createPixelTripletTopCandidates", "createTripletTopCandidates"),
    ("filterTripletTopCandidates",      "filterTripletTopCandidates"),
]

def run_callgrind_annotate(path: str) -> str:
    try:
        result = subprocess.run(
            ["callgrind_annotate", "--inclusive=no", "--auto=no", path],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except FileNotFoundError:
        print("Error: callgrind_annotate not found in PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running callgrind_annotate on {path}", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

_FUNCTION_TABLE_ROW = re.compile(r"^[^\s:]+:[^:]")


def _is_function_table_row(symbol: str) -> bool:
    sym = symbol.lstrip()
    if sym.startswith("=>"):
        return False
    return bool(_FUNCTION_TABLE_ROW.match(sym))

def _split_row(line: str):
    clean = re.sub(r'\s*\([^)]*%\s*\)', '', line).strip()
    tokens = clean.split()
    counts = []
    for i, tok in enumerate(tokens):
        if tok == '.':
            counts.append(0)
        elif re.match(r'^[\d,]*\d[\d,]*$', tok):
            counts.append(int(tok.replace(',', '')))
        else:
            symbol = ' '.join(tokens[i:])
            return counts, symbol
    return counts, None


def parse_callgrind_output(text: str, debug: bool = False) -> dict:
    data: dict = {"columns": [], "totals": [], "functions": {}}
    column_names: List[str] = []
    in_table = False

    for line in text.splitlines():
        line = line.rstrip()

        if 'file:function' in line:
            in_table = True
            continue
        if re.match(r'^\s*Ir\s+(?:Dr|I1mr)', line):
            column_names = line.split()
            continue

        if 'PROGRAM TOTALS' in line:
            metrics_part = line[:line.index('PROGRAM TOTALS')]
            clean = re.sub(r'\s*\([^)]*%\s*\)', '', metrics_part).strip()
            totals = []
            for tok in clean.split():
                if tok == '.':
                    totals.append(0)
                elif re.match(r'^[\d,]+$', tok):
                    totals.append(int(tok.replace(',', '')))
            data['totals'] = totals
            continue

        if 'file:function' in line:
            in_table = True
            continue

        if not in_table:
            continue

        if re.match(r'^[-\s]*$', line):
            continue

        counts, symbol = _split_row(line)
        if not counts or symbol is None:
            continue
        if not _is_function_table_row(symbol):
            continue

        # Accumulate across inlined call-sites sharing one symbol.
        if symbol in data['functions']:
            existing = data['functions'][symbol]
            for i, v in enumerate(counts):
                if i < len(existing):
                    existing[i] += v
                else:
                    existing.append(v)
        else:
            data['functions'][symbol] = counts

    data['columns'] = column_names if column_names else [
        "Ir", "Dr", "Dw", "I1mr", "D1mr", "D1mw",
        "ILmr", "DLmr", "DLmw", "Bc", "Bcm", "Bi", "Bim",
    ]

    if debug:
        print(f"  Detected columns : {data['columns']}")
        print(f"  Totals           : {data['totals']}")
        print(f"  # function rows  : {len(data['functions'])}")

    return data

def col_index(data: dict, name: str) -> Optional[int]:
    try:
        return data["columns"].index(name)
    except ValueError:
        return None


def get_total(data: dict, col: str) -> Optional[int]:
    idx = col_index(data, col)
    if idx is None or idx >= len(data["totals"]):
        return None
    return data["totals"][idx]


def aggregate_by_substring(data: dict, col: str, substring: str) -> int:
    idx = col_index(data, col)
    if idx is None:
        return 0
    total = 0
    for sym, counts in data["functions"].items():
        if substring in sym and idx < len(counts):
            total += counts[idx]
    return total

def sci(n: Optional[int], sig: int = 3) -> str:
    if n is None:
        return r"\text{--}"
    if n == 0:
        return r"$0$"
    exp = int(math.floor(math.log10(abs(n))))
    mantissa = round(n / 10 ** exp, sig - 1)
    mantissa_str = f"{mantissa:.{sig - 1}f}".rstrip("0").rstrip(".")
    return rf"${mantissa_str}\times10^{{{exp}}}$"


def ratio_str(base: Optional[int], new: Optional[int]) -> str:
    if base is None or new is None or base == 0:
        return r"\text{--}"
    r = new / base
    if abs(r - 1.0) < 0.02:
        return r"${\approx}1.0\times$"
    return rf"${r:.2f}\times$"

def zebra_prefix(i: int) -> str:
    return r"    \rowcolor{gray!15}" + "\n    " if (i % 2 == 1) else "    "

def build_summary_table(
    base: dict,
    sph: dict,
) -> str:

    def datarow(label: str, bv: Optional[int], sv: Optional[int], zebra_idx: int) -> str:
        prefix = zebra_prefix(zebra_idx)
        return rf"{prefix}{label} & {sci(bv)} & {sci(sv)} & {ratio_str(bv, sv)} \\"

    def catrow(title: str) -> str:
        return (
            r"    \rowcolor{gray!25}" + "\n"
            rf"    \multicolumn{{4}}{{l}}{{\textbf{{{title}}}}} \\"
        )

    Ir_b   = get_total(base, "Ir");    Ir_s   = get_total(sph, "Ir")
    Dr_b   = get_total(base, "Dr");    Dr_s   = get_total(sph, "Dr")
    Dw_b   = get_total(base, "Dw");    Dw_s   = get_total(sph, "Dw")
    I1mr_b = get_total(base, "I1mr");  I1mr_s = get_total(sph, "I1mr")
    DLmr_b = get_total(base, "DLmr");  DLmr_s = get_total(sph, "DLmr")
    DLmw_b = get_total(base, "DLmw");  DLmw_s = get_total(sph, "DLmw")
    Bcm_b  = get_total(base, "Bcm");   Bcm_s  = get_total(sph, "Bcm")

    Dr_tot_b = (Dr_b  + Dw_b)   if (Dr_b   and Dw_b)   else None
    Dr_tot_s = (Dr_s  + Dw_s)   if (Dr_s   and Dw_s)   else None
    DLm_b    = (DLmr_b + DLmw_b) if (DLmr_b and DLmw_b) else None
    DLm_s    = (DLmr_s + DLmw_s) if (DLmr_s and DLmw_s) else None

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrr}",
        r"    \toprule",
        (
            r"    \textbf{Metric}"
            r" & \textbf{Cylindrical}"
            r" & \textbf{Spherical}"
            r" & \textbf{Spherical / Cylindrical} \\"
        ),
        r"    \midrule",
        catrow("Computational work"),
        datarow(r"Instructions (Ir)", Ir_b, Ir_s, 0),
        catrow("Memory access behaviour"),
        datarow(r"Data accesses $(\mathrm{Dr}+\mathrm{Dw})$",       Dr_tot_b, Dr_tot_s, 0),
        datarow(r"LLC data misses $(\mathrm{DLmr}+\mathrm{DLmw})$", DLm_b,    DLm_s,    1),
        catrow("Instruction locality"),
        datarow(r"Instruction-cache misses $(\mathrm{I1mr})$", I1mr_b, I1mr_s, 0),
        catrow("Control-flow efficiency"),
        datarow(r"Branch mispredictions $(\mathrm{Bcm})$", Bcm_b, Bcm_s, 0),
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]
    return "\n".join(lines)

def aggregate_sum(data: dict, cols: List[str], substring: str) -> int:
    return sum(aggregate_by_substring(data, col, substring) for col in cols)

def build_function_table(
    base: dict,
    sph: dict,
    patterns: List[Tuple[str, str]],
) -> str:
    METRICS = [
        (r"Instructions (Ir)",                           ["Ir"]),
        (r"Data accesses $(\mathrm{Dr+Dw})$",            ["Dr", "Dw"]),
        (r"LLC data misses $(\mathrm{DLmr+DLmw})$",      ["DLmr", "DLmw"]),
        (r"Instr.\ cache misses $(\mathrm{I1mr})$",      ["I1mr"]),
        (r"Branch mispredictions $(\mathrm{Bcm})$",      ["Bcm"]),
    ]

    rows = []
    for func_idx, (label, substring) in enumerate(patterns):
        rows.append(r"    \rowcolor{gray!25}")
        rows.append(
            rf"    \multicolumn{{5}}{{l}}{{\textbf{{\texttt{{{label}}}}}}} \\"
        )
        for metric_idx, (metric_label, cols) in enumerate(METRICS):
            bv = aggregate_sum(base, cols, substring)
            sv = aggregate_sum(sph,  cols, substring)
            prefix = zebra_prefix(metric_idx)
            rows.append(
                rf"{prefix}& {metric_label}"
                rf" & {sci(bv)} & {sci(sv)} & {ratio_str(bv, sv)} \\"
            )

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"    \toprule",
        (
            r"    \textbf{Function} & \textbf{Metric}"
            r" & \textbf{Cylindrical} & \textbf{Spherical}"
            r" & \textbf{Spherical / Cylindrical} \\"
        ),
        r"    \midrule",
    ] + rows + [
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]
    return "\n".join(lines)

CALLGRIND_DIR = Path("raw-data/Results/AlgorithmOptimizations")

def find_latest_callgrind(prefix: str) -> str:
    pattern = f"{prefix}Callgrind.callgrind.*"
    candidates = [p for p in CALLGRIND_DIR.glob(pattern) if p.stat().st_size > 0]
    if not candidates:
        raise FileNotFoundError(
            f"No non-empty callgrind dump matching {pattern} in {CALLGRIND_DIR}. "
            f"Re-run pipelines/sections/algorithm_optimizations.py to regenerate the data."
        )
    return str(max(candidates, key=lambda p: p.stat().st_mtime))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate LaTeX callgrind tables: Cylindrical B0 vs Spherical A1."
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Path to the Cylindrical callgrind dump. Defaults to the most "
             "recent non-empty CylindricalCallgrind.callgrind.* under "
             f"{CALLGRIND_DIR}.",
    )
    parser.add_argument(
        "--spherical",
        default=None,
        help="Path to the Spherical callgrind dump. Defaults to the most "
             "recent non-empty SphericalCallgrind.callgrind.* under "
             f"{CALLGRIND_DIR}.",
    )
    parser.add_argument(
        "--output-summary",
        default="figures/Results/AlgorithmOptimizations/A1CallgrindSummary.tex",
    )
    parser.add_argument(
        "--output-functions",
        default="figures/Results/AlgorithmOptimizations/A1CallgrindFunctions.tex",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.baseline is None:
        args.baseline = find_latest_callgrind("Cylindrical")
    if args.spherical is None:
        args.spherical = find_latest_callgrind("Spherical")

    print(f"Annotating baseline : {args.baseline}")
    base_raw = run_callgrind_annotate(args.baseline)
    print(f"Annotating spherical: {args.spherical}")
    sph_raw  = run_callgrind_annotate(args.spherical)

    print("\n--- Baseline ---")
    base = parse_callgrind_output(base_raw, debug=True)
    print("\n--- Spherical ---")
    sph  = parse_callgrind_output(sph_raw,  debug=True)

    if args.debug:
        print("\n--- First 40 function symbols in BASELINE ---")
        for sym in list(base["functions"].keys())[:40]:
            print(f"  {sym}")
        print("\n--- First 40 function symbols in SPHERICAL ---")
        for sym in list(sph["functions"].keys())[:40]:
            print(f"  {sym}")
        print("\n--- Function pattern matches ---")
        for label, substring in FUNCTION_PATTERNS:
            ir_b = aggregate_by_substring(base, "Ir",   substring)
            ir_s = aggregate_by_substring(sph,  "Ir",   substring)
            l1_b = aggregate_by_substring(base, "D1mr", substring)
            l1_s = aggregate_by_substring(sph,  "D1mr", substring)
            print(f"  [{label}]  Ir_base={ir_b:,}  Ir_sph={ir_s:,}"
                  f"  L1_base={l1_b:,}  L1_sph={l1_s:,}")

    summary   = build_summary_table(base, sph)
    functions = build_function_table(base, sph, FUNCTION_PATTERNS)

    for path_str, content in [
        (args.output_summary,   summary),
        (args.output_functions, functions),
    ]:
        p = Path(path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        print(f"Saved: {p}")


if __name__ == "__main__":
    main()
