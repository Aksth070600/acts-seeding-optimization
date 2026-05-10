from __future__ import annotations

from heaptrack_summary import HeaptrackPair


def fmt_bytes(n: int) -> str:
    if n == 0:
        return r"$0\,\mathrm{B}$"
    if n >= 1_000_000:
        return rf"${n/1_000_000:.1f}\,\mathrm{{MB}}$"
    if n >= 1_000:
        return rf"${n/1_000:.1f}\,\mathrm{{kB}}$"
    return rf"${n}\,\mathrm{{B}}$"


def fmt_int(n: int) -> str:
    return rf"${n:,}$".replace(",", r"\,")


def ratio_bytes(base: int, new: int) -> str:
    if base == 0 and new == 0:
        return r"${\approx}1.0\times$"
    if base == 0:
        return r"$\infty$"
    r = new / base
    if abs(r - 1.0) < 0.02:
        return r"${\approx}1.0\times$"
    return rf"${r:.2f}\times$"


def ratio_int(base: int, new: int) -> str:
    if base == 0:
        return r"\text{--}"
    r = new / base
    if abs(r - 1.0) < 0.02:
        return r"${\approx}1.0\times$"
    return rf"${r:.2f}\times$"


def _entry_rows(entry: HeaptrackPair) -> list[str]:
    return [
        r"    \rowcolor{gray!25}",
        rf"    \multicolumn{{5}}{{l}}{{\textbf{{\texttt{{{entry.label}}}}}}} \\",
        (
            r"    "
            rf"& Peak memory & {fmt_bytes(entry.base_peak_bytes)}"
            rf" & {fmt_bytes(entry.var_peak_bytes)}"
            rf" & {ratio_bytes(entry.base_peak_bytes, entry.var_peak_bytes)} \\"
        ),
        (
            r"    \rowcolor{gray!15}" + "\n    "
            rf"& Allocations & {fmt_int(entry.base_allocs)}"
            rf" & {fmt_int(entry.var_allocs)}"
            rf" & {ratio_int(entry.base_allocs, entry.var_allocs)} \\"
        ),
    ]


def build_table(
    blocks: list[tuple[str, list[HeaptrackPair]]],
    label_base: str,
    label_variant: str,
    ratio_label: str,
) -> str:
    # blocks: list of (group_label, entries). Non-empty group_label emits
    # a subheader band (used by CodeOpts); empty emits rows directly.
    rows: list[str] = []
    for group_label, entries in blocks:
        if group_label:
            rows.append(r"    \rowcolor{gray!40}")
            rows.append(
                rf"    \multicolumn{{5}}{{l}}{{\textbf{{{group_label} detector}}}} \\"
            )
        for entry in entries:
            rows.extend(_entry_rows(entry))

    lines = [
        r"\renewcommand{\arraystretch}{1.4}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"    \toprule",
        (
            rf"    \textbf{{Function}} & \textbf{{Metric}}"
            rf" & \textbf{{{label_base}}} & \textbf{{{label_variant}}}"
            rf" & \textbf{{Ratio {ratio_label}}} \\"
        ),
        r"    \midrule",
    ] + rows + [
        r"    \bottomrule",
        r"\end{tabular}%",
        r"}",
        "",
    ]
    return "\n".join(lines)
