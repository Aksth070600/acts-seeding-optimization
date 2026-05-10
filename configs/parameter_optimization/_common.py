"""Shared helpers for the parameter-optimisation pipeline.

Imported by every runner under ``configs/parameter_optimization/``
(run_1d_sweep, run_grid, run_confirmation, pick_winners).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import yaml

REPO          = Path(__file__).resolve().parents[2]
PARAM_OPT_DIR = REPO / "configs" / "parameter_optimization"

sys.path.append(str(REPO / "data-gen"))
from workflow import DataGenWorkflow  # noqa: E402


# ── Constants ────────────────────────────────────────────────────────────────

NEIGHBOR_KEYS = ("etaBinNeighborsBottom", "etaBinNeighborsTop")

AXIS_NAMES = {
    "DeltaEtaMax":              "deltaEtaMax",
    "PhiBinDeflectionCoverage": "phiBinDeflectionCoverage",
    "EtaBinNeighborsBottom":    "etaBinNeighborsBottom",
    "EtaBinNeighborsTop":       "etaBinNeighborsTop",
    "MaxSeedsPerSpM":           "maxSeedsPerSpM",
    "ImpactMax":                "impactMax",
    "CompatSeedLimit":          "compatSeedLimit",
    "DeltaRMax":                "deltaRMax",
}


def n_eta_bins(*, etaMin: float, etaMax: float, deltaEtaMax: float) -> int:
    """C++ side computes ``floor((etaMax - etaMin) / deltaEtaMax)`` and
    clamps to at least 1; mirror that here so the override arrays we
    build line up with the real bin count."""
    return max(1, int(math.floor(
        (float(etaMax) - float(etaMin)) / float(deltaEtaMax)
    )))


def n_bins_from(cell: dict) -> int:
    """Pull ``etaMin``/``etaMax``/``deltaEtaMax`` from a merged cell
    dict and return the resulting bin count."""
    return n_eta_bins(
        etaMin      = cell["etaMin"],
        etaMax      = cell["etaMax"],
        deltaEtaMax = cell["deltaEtaMax"],
    )


def neighbors_literal(window, n_bins: int) -> str:
    """Render a per-bin neighbor window as the runner literal
    ``[[lo, hi], ...] × n_bins``. Accepts:
      * int n                 → symmetric window [-n, n] × n_bins
      * [lo, hi]              → asymmetric pair × n_bins
      * [[lo, hi], ...]       → already-expanded list of pairs; the
                                first pair is taken and re-expanded to
                                n_bins (length-fixing for sweeps that
                                change deltaEtaMax)
      * already-rendered str  → returned unchanged (idempotent)
    """
    if isinstance(window, str):
        return window
    if isinstance(window, (list, tuple)):
        if window and isinstance(window[0], (list, tuple)):
            # list-of-pairs (anchor's expanded array). Take the first
            # pair as the canonical window — anchors used in this
            # pipeline always carry uniform per-bin windows.
            lo, hi = int(window[0][0]), int(window[0][1])
        else:
            lo, hi = int(window[0]), int(window[1])
    else:
        n = int(window)
        lo, hi = -n, n
    return "[" + ",".join([f"[{lo},{hi}]"] * n_bins) + "]"

def render_overrides(cell: dict) -> str:
    """Render a cell dict as the runner ``--parameters`` string.
    Neighbor axes are auto-expanded to per-bin literals using the
    cell's ``etaMin``/``etaMax``/``deltaEtaMax``."""
    n_bins = n_bins_from(cell)
    parts = []
    for k, v in cell.items():
        if k in NEIGHBOR_KEYS:
            parts.append(f"{k}={neighbors_literal(v, n_bins)}")
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)

def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def load_anchor() -> dict:
    """configs/parameter_optimization/anchor.yaml — shared default
    configuration. Used as the baseline for every cell."""
    return _load_yaml(PARAM_OPT_DIR / "anchor.yaml")


def load_axis(path: Path) -> dict:
    """One axis spec (configs/parameter_optimization/axes/<P>.yaml).
    Caller passes the path explicitly so run_1d_sweep can be invoked
    with an arbitrary path."""
    return _load_yaml(path)


def load_grid() -> dict:
    """configs/parameter_optimization/grid.yaml — joint-search intervals."""
    return _load_yaml(PARAM_OPT_DIR / "grid.yaml")


def load_selection_rules() -> dict:
    """configs/parameter_optimization/selection_rules.yaml — rule
    tolerances + descriptions."""
    return _load_yaml(PARAM_OPT_DIR / "selection_rules.yaml")


def load_confirmation() -> dict:
    """configs/parameter_optimization/confirmation.yaml — confirmation
    event count."""
    return _load_yaml(PARAM_OPT_DIR / "confirmation.yaml")
    
def make_workflow() -> DataGenWorkflow:
    workflow = DataGenWorkflow()
    workflow.copy_required_dirs()
    workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
    workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/globalTiming")
    workflow.build_environment()
    return workflow
