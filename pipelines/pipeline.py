from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _read_runs_from_config() -> int:
    import yaml

    cfg_path = ROOT_DIR / "configs" / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    return int(cfg.get("runs", 1))


def run_files(base: str, stem: str, ext: str, n: int | None = None) -> list[str]:
    if n is None:
        n = _read_runs_from_config()
    if n == 1:
        return [f"{base}/{stem}{ext}"]
    return [f"{base}/{stem}_run{i}{ext}" for i in range(1, n + 1)]

# Shared GNN4ITk Athena dump consumed by methods/baseline/detailed/datasets.
GNN4ITK_DATASET_PATH = Path(
    "/storage/shared/ACTS/user.avallier.38040858.EXT0._000074.Dump_GNN4Itk.root"
)


class Pipeline:
    def __init__(self, name):
        self.name         = name
        self.steps        = []
        self.requirements = []

    def add(self, description, script, output=None, script_args=None,
            requires=None, always_run=False):
        if output is None:
            outputs = []
        elif isinstance(output, (str, Path)):
            outputs = [output]
        else:
            outputs = list(output)
        if requires is None:
            reqs = []
        elif isinstance(requires, (str, Path)):
            reqs = [Path(requires)]
        else:
            reqs = [Path(r) for r in requires]
        args = list(script_args) if script_args else []
        self.steps.append((description, script, outputs, args, reqs, always_run))

    def requires(self, path, description=None):
        self.requirements.append((Path(path), description or path))

    def _check_requirements(self):
        if not self.requirements:
            return True

        print("  Checking requirements...", flush=True)
        failed = []
        for path, description in self.requirements:
            full_path = ROOT_DIR / path if not path.is_absolute() else path
            if full_path.exists():
                print(f"    ✓ {description}")
            else:
                print(f"    ✗ {description} not found: {full_path}")
                failed.append(description)

        if failed:
            print(f"\n  Aborting — {len(failed)} required file(s) missing.\n")
            return False

        print()
        return True

    def run(self):
        n = len(self.steps)
        print(f"\n{'='*50}")
        print(f"  Pipeline: {self.name}  ({n} steps)")
        print(f"{'='*50}\n")

        t_total = time.time()
        failed  = []

        if not self._check_requirements():
            return False

        for i, (description, script, outputs, script_args, reqs, always_run) in enumerate(self.steps, start=1):
            if reqs:
                full_reqs = [ROOT_DIR / r if not r.is_absolute() else r for r in reqs]
                missing_reqs = [str(r) for r in full_reqs if not r.exists()]
                if missing_reqs:
                    print(f"  [{i}/{n}] {description} ... skipped (missing: {', '.join(missing_reqs)})")
                    continue

            # always_run bypasses the output-cache skip — gperftools
            # resolves PC addresses against the live ACTS binary, which
            # changes whenever any other variant is built.
            if outputs and not always_run:
                full_outputs = [ROOT_DIR / o if not Path(o).is_absolute() else Path(o) for o in outputs]
                missing = [o for o in full_outputs if not o.exists()]
                if not missing:
                    print(f"  [{i}/{n}] {description} ... skipped (all outputs exist)")
                    continue

            print(f"  [{i}/{n}] {description} ...", flush=True)
            t0 = time.time()

            log_dir = ROOT_DIR / "raw-data" / "pipeline"
            log_dir.mkdir(parents=True, exist_ok=True)
            # Encode script_args into the log name so dispatchers don't overwrite each other.
            arg_suffix = "_".join(
                "".join(c for c in a if c.isalnum()) for a in script_args
            )
            log_stem = Path(script).stem + (f"_{arg_suffix}" if arg_suffix else "")
            log_path = log_dir / f"{log_stem}.log"

            with log_path.open("w") as log_file:
                result = subprocess.run(
                    [sys.executable, script, *script_args],
                    stdin=subprocess.DEVNULL,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=ROOT_DIR,
                )

            elapsed = time.time() - t0

            if result.returncode != 0:
                print(f"         ✗ Failed ({elapsed:.1f}s) — see {log_path}")
                tail = log_path.read_text(errors="replace").splitlines()[-30:]
                if tail:
                    print("         --- last lines ---")
                    for line in tail:
                        print(f"         {line}")
                failed.append(script)
            else:
                print(f"         ✓ Done ({elapsed:.1f}s)")

        elapsed_total = time.time() - t_total
        print(f"\n{'='*50}")

        if failed:
            print(f"  {len(failed)}/{n} step(s) failed:")
            for f in failed:
                print(f"    - {f}")
        else:
            print(f"  All {n} steps completed ({elapsed_total:.1f}s)")

        print(f"{'='*50}\n")
        return len(failed) == 0
