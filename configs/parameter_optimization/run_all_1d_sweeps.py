"""Stage 1 wrapper: run every axis spec in
``configs/parameter_optimization/axes/``.

Iterates over the YAMLs and dispatches each to ``run_1d_sweep.py`` as
a subprocess.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


REPO     = Path(__file__).resolve().parents[2]
AXES_DIR = REPO / "configs" / "parameter_optimization" / "axes"
RUN_1D   = Path(__file__).parent / "run_1d_sweep.py"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.parse_args()

    yamls = sorted(AXES_DIR.glob("*.yaml"))
    print(f"Found {len(yamls)} axis specs in {AXES_DIR.relative_to(REPO)}/")

    failures: list[str] = []
    skipped:  list[str] = []
    for yml in yamls:
        with yml.open() as f:
            spec = yaml.safe_load(f) or {}
        if not spec.get("values"):
            skipped.append(yml.name)
            print(f"  SKIP  {yml.name} — empty values (TODO placeholder)")
            continue
        print(f"\n--- {yml.name} {'-' * 50}")
        result = subprocess.run(
            [sys.executable, str(RUN_1D), "--axis", str(yml)],
        )
        if result.returncode != 0:
            failures.append(yml.name)

    print()
    print(f"Done. {len(yamls) - len(failures) - len(skipped)} ran, "
          f"{len(skipped)} skipped, {len(failures)} failed.")
    if failures:
        print(f"  failures: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
