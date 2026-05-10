"""Stage 4b of the parameter-optimisation pipeline: select the
per-rule winner from the events=50 confirmation results.

Reads
  raw-data/.../Confirmation/results.csv      — events=50 measurements
  raw-data/.../Confirmation/candidates.yaml  — params per cell
  raw-data/.../Baseline/                     — Cyl baseline
  configs/parameter_optimization/anchor.yaml
  configs/parameter_optimization/selection_rules.yaml

Writes one file per rule under configs/parameter_optimization/winners/:

  max_efficiency.yaml
  best.yaml
  fastest.yaml

Each file is a complete runner config (every parameter, neighbor
arrays expanded to per-bin literals) plus a header comment block
recording the rule, the measured (eff, fake, dup, time) at the
confirmation event count, the Cylindrical baseline, and the deltas.

Usage::

    python3 configs/parameter_optimization/pick_winners.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.append(str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    NEIGHBOR_KEYS, PARAM_OPT_DIR, REPO,
    load_anchor, load_selection_rules, n_bins_from,
)

sys.path.append(str(REPO / "figure-gen"))
from parameter_scan_plotter import load_baseline  # noqa: E402


RAW_DIR     = REPO / "raw-data" / "Results" / "AlgorithmOptimizations" / "ParameterOptimization"
CONFIRM_DIR = RAW_DIR / "Confirmation"
WINNERS_DIR = PARAM_OPT_DIR / "winners"


def _apply_rules(rows: list[dict], base: dict, rules: dict) -> dict:
    eps_best = float(rules.get("best_tolerance_pp", rules["tolerance_pp"])) / 100.0
    floor    = float(rules["fastest_efficiency_floor"])

    def _d(r):
        return {
            "d_eff":  r["abs"]["eff"]  - base["eff"],
            "d_fake": r["abs"]["fake"] - base["fake"],
            "d_dup":  r["abs"]["dup"]  - base["dup"],
            "d_time": r["abs"]["time"] - base["time"],
        }

    feasible_max = sorted(rows,
                          key=lambda r: (-r["abs"]["eff"], r["abs"]["time"]))
    # best uses its own tolerance (default 0.0 → strictly-better-than-Cyl
    # on every metric); fastest uses the global tolerance for fake/dup.
    feasible_best = sorted(
        [r for r in rows
         if (_d(r)["d_eff"]  >= -eps_best
             and _d(r)["d_fake"] <=  eps_best
             and _d(r)["d_dup"]  <=  eps_best)],
        key=lambda r: (r["abs"]["time"], -r["abs"]["eff"]),
    )
    # fastest: argmin time over eff ≥ floor only.  No fake/dup gates.
    feasible_fast = sorted(
        [r for r in rows if r["abs"]["eff"] >= floor],
        key=lambda r: (r["abs"]["time"], -r["abs"]["eff"]),
    )

    return {
        "max_efficiency": feasible_max[0]  if feasible_max  else None,
        "best":           feasible_best[0] if feasible_best else None,
        "fastest":        feasible_fast[0] if feasible_fast else None,
    }


def _read_confirmation() -> list[dict]:
    """Merge results.csv + candidates.yaml into rows the rule
    application can consume."""
    csv_path  = CONFIRM_DIR / "results.csv"
    cand_path = CONFIRM_DIR / "candidates.yaml"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found — run run_confirmation.py first."
        )
    if not cand_path.exists():
        raise FileNotFoundError(
            f"{cand_path} not found — run run_confirmation.py first."
        )

    df    = pd.read_csv(csv_path)
    cands = yaml.safe_load(cand_path.read_text())
    flat: list[tuple[str, dict]] = []
    for rule in ("max_efficiency", "best", "fastest"):
        for c in cands.get(rule, []):
            flat.append((rule, c))

    if len(flat) != len(df):
        raise RuntimeError(
            f"candidates.yaml has {len(flat)} entries but results.csv "
            f"has {len(df)} rows — out of sync."
        )

    rows: list[dict] = []
    for i, (proposing_rule, c) in enumerate(flat):
        r = df.iloc[i]
        params = {k: v for k, v in c.items() if not k.startswith("_")}
        rows.append({
            "cell_id":        int(r["cell_id"]),
            "proposing_rule": proposing_rule,
            "params":         params,
            "abs": {
                "eff":  float(r["eff"]),
                "fake": float(r["fake"]),
                "dup":  float(r["dup"]),
                "time": float(r["time_ms"]),
            },
            "n_events": int(r.get("n_events", 50)),
        })
    return rows


def _full_config_for_winner(row: dict, anchor: dict) -> dict:
    """Runner-ready config dict: every parameter present, neighbor
    arrays expanded to length-N pair lists where N matches the cell's
    eta-bin count."""
    cell = dict(anchor)
    cell.update(row["params"])
    n_bins = n_bins_from(cell)

    out: dict = {}
    for k, v in cell.items():
        if k not in NEIGHBOR_KEYS:
            out[k] = v
            continue
        # Detect already-expanded list-of-lists vs scalar/pair.
        if (isinstance(v, list) and v
                and isinstance(v[0], (list, tuple))
                and len(v) == n_bins):
            out[k] = [list(p) for p in v]
        elif (isinstance(v, (list, tuple)) and len(v) == 2
              and not isinstance(v[0], (list, tuple))):
            pair = [int(v[0]), int(v[1])]
            out[k] = [list(pair) for _ in range(n_bins)]
        else:
            n = int(v)
            pair = [-n, n]
            out[k] = [list(pair) for _ in range(n_bins)]
    return out


def _winner_yaml_text(rule: str, row: dict, full_cfg: dict, base: dict) -> str:
    a = row["abs"]
    d_eff  = (a["eff"]  - base["eff"])  * 100
    d_fake = (a["fake"] - base["fake"]) * 100
    d_dup  = (a["dup"]  - base["dup"])  * 100
    speedup = base["time"] / a["time"] if a["time"] > 0 else float("inf")

    header = (
        f"# {rule} winner — generated by "
        "configs/parameter_optimization/pick_winners.py\n"
        f"#\n"
        f"# Selected from confirmation runs at events={row['n_events']}.\n"
        f"# Proposing rule (events=5 grid): {row['proposing_rule']}.\n"
        f"#\n"
        f"# Measured:\n"
        f"#   eff  = {a['eff']:.4f}  (Δ{d_eff:+.3f} pp vs Cyl)\n"
        f"#   fake = {a['fake']:.4f}  (Δ{d_fake:+.3f} pp vs Cyl)\n"
        f"#   dup  = {a['dup']:.4f}  (Δ{d_dup:+.3f} pp vs Cyl)\n"
        f"#   time = {a['time']:.1f} ms  ({speedup:.2f}× speedup vs Cyl "
        f"{base['time']:.1f} ms)\n"
        f"#\n"
        f"# Cylindrical baseline:\n"
        f"#   eff = {base['eff']:.4f}   fake = {base['fake']:.4f}\n"
        f"#   dup = {base['dup']:.4f}   time = {base['time']:.1f} ms\n"
        f"#\n"
        f"# Until the 14 callsites of configs/seeding3_*.yaml are migrated\n"
        f"# in a follow-up, those YAMLs remain authoritative for the\n"
        f"# downstream chapters; this file is a parallel record.\n"
        f"\n"
    )
    body = yaml.safe_dump(full_cfg, sort_keys=False, default_flow_style=False)
    return header + body


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.parse_args()

    base   = load_baseline(RAW_DIR / "Baseline")
    rows   = _read_confirmation()
    rules  = load_selection_rules()
    anchor = load_anchor()

    winners = _apply_rules(rows, base, rules)

    WINNERS_DIR.mkdir(parents=True, exist_ok=True)
    for rule, row in winners.items():
        path = WINNERS_DIR / f"{rule}.yaml"
        if row is None:
            print(f"  {rule:>14}: no feasible cell — skipping {path.name}")
            continue
        full_cfg = _full_config_for_winner(row, anchor)
        text     = _winner_yaml_text(rule, row, full_cfg, base)
        path.write_text(text)
        a = row["abs"]
        print(f"  {rule:>14}: eff={a['eff']:.4f}  time={a['time']:.1f}ms  "
              f"→ {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
