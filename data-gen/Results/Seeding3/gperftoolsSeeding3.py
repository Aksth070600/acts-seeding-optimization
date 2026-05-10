import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(_REPO_ROOT / "data-gen"))
sys.path.insert(0, str(_REPO_ROOT / "figure-gen"))

from workflow import DataGenWorkflow, parameter_args
from gperftools_helper import (
    require_pprof, write_text_report,
    write_flamegraph, write_callgraph,
)

PROF_DIR = Path("raw-data/Results/Seeding3/Gperftools")
FIG_DIR  = Path("figures/Results/Seeding3/Gperftools")

SHOW_FROM_S3 = "SphericalGridTripletSeedingAlgorithm"


def _find_prof_files(stem: str) -> list[Path]:
    bare     = PROF_DIR / f"{stem}.prof"
    suffixed = sorted(PROF_DIR.glob(f"{stem}_run*.prof"))
    if suffixed:
        return suffixed
    if bare.exists():
        return [bare]
    return []


workflow = DataGenWorkflow()
workflow.copy_required_dirs()
workflow.copy_dir("AlgorithmOptimizations/Phi-Eta-R-Binning/_baseline")
workflow.build_environment()

workflow.run(
    RunnerDir=[],
    PythonRunners=["oddData.py"],
    DataDir="Results/Seeding3/Gperftools",
    PythonRunnerArgs=[
        "--version", "SphericalGridTriplet",
        *parameter_args("parameter_optimization/winners/best"),
    ],
    LogFileNames=["GperftoolsSeeding3"],
    Profiler="gperftools",
    PrepareEnvironment=False,
)

require_pprof()
PROF_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

prof_files = _find_prof_files("GperftoolsSeeding3")
if not prof_files:
    raise FileNotFoundError(
        f"No .prof files for GperftoolsSeeding3 in {PROF_DIR}. "
        f"The profiler step did not produce output."
    )
print(f"\n[gperftools post-render] Seeding3 ({len(prof_files)} prof file(s))")
write_text_report(prof_files, PROF_DIR / "Seeding3_report.txt", SHOW_FROM_S3)
write_flamegraph(prof_files, FIG_DIR / "Seeding3_flamegraph.svg",
                 SHOW_FROM_S3, title="Seeding3")
write_callgraph(prof_files, FIG_DIR / "Seeding3_callgraph.pdf", SHOW_FROM_S3)
