from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

def _resolve_pprof() -> Path:
    env = os.environ.get("PPROF_BIN")
    if env:
        return Path(env).expanduser()
    candidates = [
        Path("../go/bin/pprof").resolve(),
        Path.home() / "go" / "bin" / "pprof",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def _resolve_flamegraph_dir() -> Path:
    env = os.environ.get("FLAMEGRAPH_DIR")
    if env:
        return Path(env).expanduser()
    candidates = [
        Path("../FlameGraph").resolve(),
        Path.home() / "FlameGraph",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


PPROF      = _resolve_pprof()
PYTHON_BIN = "python3"

_FLAMEGRAPH_DIR = _resolve_flamegraph_dir()
STACKCOLLAPSE   = _FLAMEGRAPH_DIR / "stackcollapse-go.pl"
FLAMEGRAPH      = _FLAMEGRAPH_DIR / "flamegraph.pl"
DOT             = Path("/usr/bin/dot") if Path("/usr/bin/dot").exists() else None

FONT_SCALE   = 3.5
MAX_FUNC_LEN = 55


def require_pprof() -> None:
    if not PPROF.exists():
        print(f"ERROR: Go pprof not found at {PPROF}")
        print("  Set $PPROF_BIN to override, or install pprof at "
              "$HOME/go/bin/pprof (Go default).")
        sys.exit(1)

def write_text_report(prof_files, out_path: Path, show_from: str) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PPROF), "--text", "-relative_percentages",
        f"-show_from={show_from}", PYTHON_BIN,
    ] + [str(p) for p in prof_files]
    print(f"  Generating {out_path.name} ...")
    with out_path.open("w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.DEVNULL, check=False)
    return out_path


# flat-time(unit)  flat%  sum%  cum-time(unit)  cum%  name
_TEXT_LINE = re.compile(
    r"^\s*[\d.]+\S*"
    r"\s+([0-9.]+)%"
    r"\s+[0-9.]+%"
    r"\s+[\d.]+\S*"
    r"\s+([0-9.]+)%"
    r"\s+(.+)$"
)


def parse_text_report(txt_path: Path, top_n: int, skip_tokens=()):
    if not txt_path.exists():
        return []
    out: list[tuple[str, float, float]] = []
    with txt_path.open() as fh:
        for line in fh:
            m = _TEXT_LINE.match(line)
            if not m:
                continue
            flat = float(m.group(1))
            cum  = float(m.group(2))
            func = m.group(3).strip()
            if any(tok in func for tok in skip_tokens):
                continue
            out.append((func, flat, cum))
    return out[:top_n]

def _strip_flamegraph_ui(svg_path: Path, strip_title: bool = False) -> None:
    # Strip the interactive search/zoom UI from flamegraph.pl SVGs and
    # flatten the yellow gradient to white. flamegraph.pl rejects
    # --bgcolors=white, so background flattening is done here instead.
    if not svg_path.exists() or svg_path.stat().st_size == 0:
        return

    # Drop <script> blocks via line scan rather than regex so nested CDATA
    # / escape sequences can't accidentally swallow downstream SVG content.
    in_script = False
    out_lines: list[str] = []
    for line in svg_path.read_text().splitlines(keepends=True):
        if not in_script and "<script" in line:
            in_script = True
            if "</script>" in line:
                in_script = False
            continue
        if in_script:
            if "</script>" in line:
                in_script = False
            continue
        out_lines.append(line)
    text = "".join(out_lines)

    for gid in ("search", "ignorecase", "unzoom", "matched"):
        text = re.sub(rf'<g id="{gid}".*?</g>', "", text, flags=re.DOTALL)

    # Top-level UI <text> labels — the .hide CSS class is honoured by
    # browsers but dropped by rsvg/inkscape, so they leak into the PDF.
    for tid in ("search", "ignorecase", "unzoom", "matched", "details"):
        text = re.sub(rf'<text id="{tid}"[^>]*>.*?</text>\s*', "",
                      text, flags=re.DOTALL)

    if strip_title:
        text = re.sub(r'<text id="title"[^>]*>.*?</text>\s*', "",
                      text, flags=re.DOTALL)

    text = re.sub(r"^\s*#(search|ignorecase)[^\n]*\n", "",
                  text, flags=re.MULTILINE)
    text = re.sub(r'\s+on(?:mouseover|mouseout|click)="[^"]*"', "", text)
    text = re.sub(r'fill="url\(#background\)"', 'fill="white"', text)
    text = re.sub(
        r'<linearGradient\s+id="background".*?</linearGradient>\s*',
        "", text, flags=re.DOTALL,
    )

    svg_path.write_text(text)


def write_flamegraph(prof_files, out_path: Path, show_from: str,
                     title: str = "", *,
                     width: int = 1600, height_per_frame: int = 36,
                     fontsize: int = 14) -> None:
    if not STACKCOLLAPSE.exists() or not FLAMEGRAPH.exists():
        raise FileNotFoundError(
            f"FlameGraph scripts not found at {_FLAMEGRAPH_DIR} — refusing "
            f"to silently skip {out_path.name}. Set $FLAMEGRAPH_DIR or "
            f"install FlameGraph at $HOME/FlameGraph."
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(PPROF), "-raw", f"-show_from={show_from}",
           PYTHON_BIN] + [str(p) for p in prof_files]

    # flamegraph.pl's Getopt::Long rejects --title= (empty), which then
    # SIGPIPEs the upstream stackcollapse-go. Pass a placeholder and strip
    # the rendered title element in post-processing when not wanted.
    fg_title  = title if title else "FlameGraph"
    drop_title = not title

    with out_path.open("w") as out:
        p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
        p2 = subprocess.Popen([str(STACKCOLLAPSE)], stdin=p1.stdout,
                              stdout=subprocess.PIPE, text=True)
        p1.stdout.close()
        p3 = subprocess.Popen(
            [str(FLAMEGRAPH),
             f"--width={width}", f"--height={height_per_frame}",
             f"--fontsize={fontsize}",
             "--minwidth=2",
             "--hash", f"--title={fg_title}"],
            stdin=p2.stdout, stdout=out, text=True,
        )
        p2.stdout.close()
        rc1 = p1.wait()
        rc2 = p2.wait()
        rc3 = p3.wait()

    for rc, who in ((rc1, "pprof"),
                    (rc2, "stackcollapse-go"),
                    (rc3, "flamegraph.pl")):
        if rc != 0:
            raise RuntimeError(
                f"{who} exited with code {rc} while producing "
                f"{out_path.name}. See the pipeline log for stderr."
            )

    raw_size = out_path.stat().st_size if out_path.exists() else 0
    if raw_size == 0:
        raise RuntimeError(
            f"{out_path.name} is 0 bytes despite zero exit codes — the "
            f"flame-graph pipeline silently produced no output. Check the "
            f"pipeline log for the failing stage."
        )

    _strip_flamegraph_ui(out_path, strip_title=drop_title)
    print(f"  Generated flamegraph: {out_path}  ({raw_size:,} bytes raw)")

def write_callgraph(prof_files, out_path: Path, show_from: str) -> None:
    if DOT is None:
        return
    # nodefraction/edgefraction prune the ~1% inline-leaf clutter pprof
    # piles at the bottom of the graph.
    cmd = [
        str(PPROF), "-dot", "-call_tree", f"-show_from={show_from}",
        "-relative_percentages",
        "-nodecount=35",
        "-nodefraction=0.02",
        "-edgefraction=0.01",
        PYTHON_BIN,
    ] + [str(p) for p in prof_files]
    try:
        dot_output = subprocess.check_output(cmd, text=True,
                                             stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return
    dot_output = "\n".join(
        l for l in dot_output.splitlines() if "subgraph cluster_L" not in l
    )
    dot_output = re.sub(r'[0-9]+(?:\.[0-9]+)?(?:ns|µs|ms|s)\\n', '', dot_output)
    dot_output = re.sub(
        r'label="[0-9]+(?:\.[0-9]+)?(?:ns|µs|ms|s)(?:\\n\\(inline\\)?)"',
        'label=""', dot_output,
    )
    dot_output = re.sub(
        r'fontsize=(\d+)',
        lambda m: f'fontsize="{int(int(m.group(1)) * FONT_SCALE)}"',
        dot_output,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dot_cmd = [
        str(DOT), "-Tpdf", "-Gsize=9.7,6.3", "-Grankdir=TB", "-Gmargin=0.3",
        "-Efontsize=50", "-Nwidth=2.0", "-Nheight=2.5", "-Gsep=+12",
        f"-o{out_path}",
    ]
    subprocess.run(dot_cmd, input=dot_output, text=True, check=False)
    print(f"  Generated callgraph: {out_path}")

def write_source_annotation(prof_files, out_path: Path, show_from: str) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PPROF), "--list", show_from, f"-show_from={show_from}",
        "-relative_percentages", PYTHON_BIN,
    ] + [str(p) for p in prof_files]
    with out_path.open("w") as fh:
        subprocess.run(cmd, stdout=fh, stderr=subprocess.DEVNULL, check=False)
    return out_path

_LATEX_SPECIAL = str.maketrans({
    "_":  r"\_",   "%":  r"\%",   "&":  r"\&",   "#":  r"\#",   "$":  r"\$",
    "{":  r"\{",   "}":  r"\}",
    "~":  r"\textasciitilde{}",   "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
    "<":  r"\textless{}",         ">":  r"\textgreater{}",
})


_ACTS_PREFIX_RE = re.compile(
    r"^Acts::(?:\(anonymous namespace\)::)?"
    r"(?:[A-Za-z_][A-Za-z_0-9]*::)*?"
)


def _strip_leading_namespaces(name: str) -> str:
    # Keep std:: as-is and only strip Acts:: chains. Track every kind of
    # bracket (<>, (), {}, []) so a "::" inside a lambda specifier or
    # template parameter list isn't mistaken for a namespace boundary.
    if name.startswith("std::"):
        return name
    if not name.startswith("Acts::"):
        return name

    depth = 0
    positions = []
    i = 0
    while i < len(name) - 1:
        ch = name[i]
        if ch in "<({[":
            depth += 1
        elif ch in ">)}]":
            depth = max(0, depth - 1)
        elif depth == 0 and ch == ":" and name[i+1] == ":":
            positions.append(i)
            i += 1
        i += 1

    # Keep the last two segments (class::method).
    if len(positions) >= 2:
        cut = positions[-2]
        return name[cut+2:]
    return name


def latex_func(name: str) -> str:
    short = _strip_leading_namespaces(name)
    if len(short) > MAX_FUNC_LEN:
        body = short[:MAX_FUNC_LEN].translate(_LATEX_SPECIAL)
        return rf"\texttt{{{body}}}\ldots"
    return rf"\texttt{{{short.translate(_LATEX_SPECIAL)}}}"


# "<lead> & \texttt{...} & <flat> & <cum> \\". <lead> is \quad or an int;
# <flat>/<cum> are numeric or the \textemdash{} placeholder.
_TEX_ROW = re.compile(
    r"&\s*\\texttt\{(?P<func>.*?)\}(?P<dots>\\ldots)?\s*"
    r"&\s*(?P<flat>[0-9.]+|\\textemdash\{\})\s*"
    r"&\s*(?P<cum>[0-9.]+|\\textemdash\{\})\s*\\\\"
)


def verify_tex_against_report(tex_path: Path, sections, *,
                              tol: float = 0.01) -> None:
    # Round-trip guard against silent regex/hand-edit drift in numbers.
    tex_path = Path(tex_path)
    if not tex_path.exists():
        raise FileNotFoundError(f"Cannot verify; LaTeX file missing: {tex_path}")

    expected: list[tuple[float | None, float | None]] = []
    for _label, funcs in sections:
        for _func, flat, cum in funcs:
            expected.append((flat, cum))

    seen: list[tuple[float | None, float | None]] = []
    for line in tex_path.read_text().splitlines():
        m = _TEX_ROW.search(line)
        if not m:
            continue
        flat = (None if m.group("flat") == r"\textemdash{}"
                else float(m.group("flat")))
        cum  = (None if m.group("cum")  == r"\textemdash{}"
                else float(m.group("cum")))
        seen.append((flat, cum))

    real_seen = [r for r in seen if r != (None, None)]
    if len(real_seen) != len(expected):
        raise RuntimeError(
            f"{tex_path.name}: row-count mismatch "
            f"({len(real_seen)} in .tex vs {len(expected)} in source)."
        )
    for i, ((tex_flat, tex_cum), (src_flat, src_cum)) in enumerate(
            zip(real_seen, expected)):
        if tex_flat is None or tex_cum is None:
            raise RuntimeError(
                f"{tex_path.name}: row {i} is a placeholder in .tex but "
                f"the source had real values {src_flat}/{src_cum}.")
        if abs(tex_flat - src_flat) > tol or abs(tex_cum - src_cum) > tol:
            raise RuntimeError(
                f"{tex_path.name}: row {i} drifted "
                f"(tex flat={tex_flat}/cum={tex_cum} vs "
                f"src flat={src_flat}/cum={src_cum}, tol={tol})."
            )


def latex_function_table(header_name: str, sections, top_n: int,
                         *, numbered: bool = False) -> str:
    # Padding rows pass None (not 0.0) for flat/cum so a real 0.0 entry
    # doesn't collide with a placeholder and break the round-trip check.
    def fmt(v) -> str:
        return r"\textemdash{}" if v is None else f"{v:.2f}"

    lines = [
        r"\begin{tabular}{rlrr}",
        r"\toprule",
        rf"\textbf{{\#}} & \textbf{{{header_name}}} & "
        rf"\textbf{{Flat\,\%}} & \textbf{{Cum\,\%}} \\",
        r"\midrule",
    ]
    first = True
    for title, funcs in sections:
        if title is not None:
            if not first:
                lines.append(r"\\[-0.5em]")
            lines.append(rf"\multicolumn{{4}}{{l}}{{\textbf{{{title}}}}} \\")
        first = False
        padded = list(funcs) + [("---", None, None)] * max(0, top_n - len(funcs))
        for i, (func, flat, cum) in enumerate(padded, start=1):
            lead = str(i) if numbered else r"\quad"
            lines.append(rf"{lead} & {latex_func(func)} & {fmt(flat)} & {fmt(cum)} \\")
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)

HOTSPOTS = [
    {
        "label":       "H1_createDoubletsImpl",
        "show_from":   "createDoubletsImpl",
        "description": (
            "H1 --- inner-loop predicate cost. Cost is distributed across the "
            "candidate-pair predicate sequence (collision-region origin check, "
            "deltaZ check, interaction-point cut, helix-diameter cut, "
            "Delegate-dispatched experiment-cuts call); the collision-region "
            "check is the single largest per-line contributor."
        ),
    },
    {
        "label":       "H2_createPixelTripletTopCandidates",
        "show_from":   "createPixelTripletTopCandidates",
        "description": (
            "H2 --- early-exit ordering inefficiency. ``error2`` (multi-line "
            "error-propagation) is computed before the cheap "
            "``deltaCotTheta2`` (subtraction + square), so candidates that "
            "would be rejected on cot-theta grounds alone still pay the full "
            "error cost first."
        ),
    },
    {
        "label":       "H3_IndirectCall",
        "show_from":   "sortByCotTheta",
        "description": (
            "H3 --- indirect-call overhead. Filter symbol is "
            "``sortByCotTheta`` (universal representative across both "
            "detector geometries): the projection lambda inside "
            "``std::ranges::sort`` executes in its own frame, defeating "
            "compiler inlining at the projection-interface boundary. The "
            "same pattern appears in ``Acts::Delegate`` dispatches "
            "(``itkFastTrackingSPselect`` on pixel, ``itkFastTrackingCuts`` "
            "on strip), discussed in the thesis text."
        ),
    },
    {
        "label":       "H4_AllocationPressure",
        "show_from":   "DoubletsForMiddleSp::emplace_back",
        "description": (
            "H4 --- allocation pressure. Filter symbol is "
            "``DoubletsForMiddleSp::emplace_back`` (dominant of the two H4 "
            "contributors): the struct-of-arrays doublet container performs "
            "five independent ``vector::push_back`` calls per accepted "
            "doublet, each on a separately-growing buffer. Grid bin "
            "``push_back`` in ``CylindricalSpacePointGrid2::insert`` shares "
            "the same on-demand-growth pattern and is discussed in the "
            "thesis text."
        ),
    },
]


def run_hotspot_suite(prof_files, output_dir: Path, txt_dir: Path,
                      *, file_prefix: str = "") -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)
    for hs in HOTSPOTS:
        label     = hs["label"]
        show_from = hs["show_from"]
        print(f"\n  -- {label} --")

        ann_path = txt_dir / f"{file_prefix}{label}_annotation.txt"
        write_source_annotation(prof_files, ann_path, show_from)
        content = ann_path.read_text(errors="replace")
        if "ROUTINE" not in content:
            print(f"  WARNING: no ROUTINE block in {ann_path.name} — "
                  f"check that ACTS was built with -g and symbol '{show_from}' matches.")
        else:
            print(f"    -> {hs['description']}")


def write_hotspots_index(output_dir: Path, txt_dir: Path, *,
                         title: str, variants) -> None:
    # variants: iterable of (file_prefix, display_label). Pass
    # display_label=None for single-pipeline layouts.
    idx = output_dir / "INDEX.txt"
    with idx.open("w") as fh:
        fh.write(f"{title}\n")
        fh.write("=" * 60 + "\n\n")
        for hs in HOTSPOTS:
            fh.write(f"[{hs['label']}]\n")
            fh.write(f"  show_from : {hs['show_from']}\n")
            fh.write(f"  note      : {hs['description']}\n")
            for prefix, display in variants:
                ann = txt_dir / f"{prefix}{hs['label']}_annotation.txt"
                if display is not None:
                    fh.write(f"  {display}:\n")
                    indent = "    "
                else:
                    indent = "  "
                fh.write(f"{indent}annotation : {ann.name}"
                         f"{'  [OK]' if ann.exists() else '  [MISSING]'}\n")
            fh.write("\n")
    print(f"\nIndex written: {idx}")
