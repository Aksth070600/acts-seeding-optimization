#!/usr/bin/env python3

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


_NFS_FALLBACK_WARNED = False


def _rmtree_nfs_tolerant(path: Path) -> None:
    # NFS keeps a busy-file alive as .nfs<hex>, which trips rmtree on
    # the parent dir. Try once, then fall to ignore_errors=True; the
    # NFS server reaps the residual files when the holder releases.
    global _NFS_FALLBACK_WARNED
    try:
        shutil.rmtree(path, ignore_errors=False)
        return
    except OSError as e:
        if not _NFS_FALLBACK_WARNED:
            sys.stderr.write(
                f"Note: rmtree({path}) hit {e!r}; using ignore_errors=True "
                "for this and any subsequent cleanup in this run. "
                "Residual NFS .nfs* files will be reaped by the NFS server "
                "when the holding process releases.\n"
            )
            _NFS_FALLBACK_WARNED = True
        shutil.rmtree(path, ignore_errors=True)


_REPO_ROOT = Path(__file__).resolve().parent.parent


def load_config(name: str) -> dict:
    import yaml

    path = _REPO_ROOT / "configs" / f"{name}.yaml"
    with path.open() as f:
        return yaml.safe_load(f) or {}


def parameter_args(source: str | Mapping[str, Any]) -> list[str]:
    config = load_config(source) if isinstance(source, str) else dict(source)
    if not config:
        return []
    return ["--parameters", ", ".join(f"{k}={v}" for k, v in config.items())]


def default_events() -> int:
    cfg = load_config("config")
    return int(cfg.get("events", 50))


def default_runs() -> int:
    cfg = load_config("config")
    return int(cfg.get("runs", 1))


class DataGenWorkflow:
    def __init__(self, repo_root: str | Path | None = None) -> None:
        if repo_root is None:
            self.repo_root = Path(__file__).resolve().parent.parent
        else:
            self.repo_root = Path(repo_root).resolve()

        self.copy_script = self.repo_root / "utils" / "CopyDir.sh"
        self.build_script = self.repo_root / "environment" / "build.sh"
        self.python_scripts_dir = (
            self.repo_root / "ACTS" / "source" / "Examples" / "Scripts" / "Python"
        )
        self.parsers_dir = self.repo_root / "utils" / "parsers"
        self.raw_data_dir = self.repo_root / "raw-data"
        self.temp_data_dir = self.raw_data_dir / "temp"

        self.python_command = "python3"

    def run(
        self,
        RunnerDir: Iterable[str] | None = None,
        PythonRunners: Sequence[str] | None = None,
        DataDir: str | None = None,
        PythonRunnerArgs: Sequence[str] | None = None,
        Parsers: Sequence[tuple[str, str, int]] | None = None,
        LogFileNames: Sequence[str] | None = None,
        Sweep: dict[str, Sequence[Any]] | None = None,
        Runs: int | None = None,
        Profiler: str | None = None,
        ProfilerArgs: Sequence[str] | None = None,
        tempOutputDir: str | Path | None = None,
        PrepareEnvironment: bool = True,
    ) -> dict[str, Any]:
        RunnerDir = list(RunnerDir or [])
        PythonRunners = list(PythonRunners or [])
        PythonRunnerArgs = list(PythonRunnerArgs or [])
        Parsers = list(Parsers or [])
        Sweep = dict(Sweep or {})
        ProfilerArgs = list(ProfilerArgs or [])

        if "--events" not in PythonRunnerArgs and "--events" not in Sweep:
            PythonRunnerArgs = ["--events", str(default_events())] + PythonRunnerArgs

        if Runs is None and not Sweep:
            Runs = default_runs()

        if not PythonRunners:
            raise ValueError("PythonRunners must be provided")
        if DataDir is None:
            raise ValueError("DataDir must be provided")

        if LogFileNames is None:
            LogFileNames = [Path(runner).stem for runner in PythonRunners]
        else:
            LogFileNames = list(LogFileNames)

        if len(LogFileNames) != len(PythonRunners):
            raise ValueError(
                "LogFileNames must have the same length as PythonRunners"
            )

        for parser_spec in Parsers:
            if len(parser_spec) != 3:
                raise ValueError(
                    "Each parser spec must be a tuple of "
                    "(parser_name, parsed_file_name, runner_index)"
                )

            parser_name, parsed_file_name, runner_index = parser_spec

            if not isinstance(runner_index, int):
                raise ValueError(
                    f"Parser spec runner_index must be an int, got {runner_index!r}"
                )

            if runner_index < 0 or runner_index >= len(PythonRunners):
                raise ValueError(
                    f"Parser spec runner_index {runner_index} is out of range for "
                    f"{len(PythonRunners)} PythonRunners"
                )

            if not parser_name:
                raise ValueError("Parser filename must not be empty")

            if not parsed_file_name:
                raise ValueError("Parsed output filename must not be empty")

        self._validate_profiler(Profiler)
        
        run_count = self._resolve_run_count(Sweep=Sweep, Runs=Runs)
        
        self._validate_sweep(Sweep=Sweep, Runs=run_count)

        if PrepareEnvironment:
            self.copy_required_dirs()
            for dir_name in RunnerDir:
                self.copy_dir(dir_name)

            self.build_environment()

        run_results: list[dict[str, Any]] = []
        for run_index in range(run_count):
            run_args = self._build_run_arguments(
                base_args=PythonRunnerArgs,
                Sweep=Sweep,
                run_index=run_index,
            )

            runner_results: list[dict[str, Any]] = []
            log_paths_by_runner_index: dict[int, Path] = {}

            for runner_index, (python_runner, base_log_name) in enumerate(
                zip(PythonRunners, LogFileNames)
            ):
                run_log_name = self._build_run_log_name(
                    base_log_name=base_log_name,
                    python_runner=python_runner,
                    run_index=run_index,
                    total_runs=run_count,
                )

                log_path = self.run_python_script(
                    script_name=python_runner,
                    output_dir_name=DataDir,
                    script_args=run_args,
                    log_name=run_log_name,
                    profiler=Profiler,
                    profiler_args=ProfilerArgs,
                    temp_output_dir=tempOutputDir,
                )

                log_paths_by_runner_index[runner_index] = log_path

                profiler_output_path: Path | None = None
                if Profiler is not None:
                    profiler_output_path = self._get_profiler_output_path(
                        profiler=Profiler,
                        log_path=log_path,
                    )

                runner_results.append(
                    {
                        "runner_index": runner_index,
                        "python_runner": python_runner,
                        "runner_args": run_args,
                        "log_path": log_path,
                        "profiler": Profiler,
                        "profiler_output_path": profiler_output_path,
                    }
                )

            parser_results: list[dict[str, Any]] = []
            for parser_name, parsed_file_name, runner_index in Parsers:
                run_parsed_file_name = self._build_run_parsed_file_name(
                    parsed_file_name=parsed_file_name,
                    run_index=run_index,
                    total_runs=run_count,
                )

                input_log_path = log_paths_by_runner_index[runner_index]

                parsed_output_path = self.run_parser(
                    parser_name=parser_name,
                    log_path=input_log_path,
                    output_dir_name=DataDir,
                    parsed_file_name=run_parsed_file_name,
                )

                parser_results.append(
                    {
                        "parser_name": parser_name,
                        "input_runner_index": runner_index,
                        "input_log_path": input_log_path,
                        "parsed_output_path": parsed_output_path,
                    }
                )

            run_results.append(
                {
                    "run_index": run_index + 1,
                    "runners": runner_results,
                    "parsers": parser_results,
                }
            )

        return {
            "runs": run_results,
        }

    def copy_required_dirs(self) -> None:
        self.copy_dir("clean")
        self.copy_dir("runners")

    def copy_dir(self, dir_name: str) -> None:
        self._ensure_file_exists(self.copy_script, "CopyDir.sh")

        copy_command = (
            f"bash {shlex.quote(str(self.copy_script))} "
            f"{shlex.quote(dir_name)}"
        )
        self._run_bash_command(copy_command, cwd=self.repo_root)

    def build_environment(self) -> None:
        self._ensure_file_exists(self.build_script, "environment/build.sh")
        build_command = f"bash {shlex.quote(str(self.build_script))}"
        self._run_bash_command(build_command, cwd=self.repo_root)

    def run_python_script(
        self,
        script_name: str,
        output_dir_name: str,
        script_args: Sequence[str] | None = None,
        log_name: str | None = None,
        profiler: str | None = None,
        profiler_args: Sequence[str] | None = None,
        temp_output_dir: str | Path | None = None,
    ) -> Path:
        
        script_args = list(script_args or [])
        profiler_args = list(profiler_args or [])

        script_path = self.python_scripts_dir / script_name
        self._ensure_file_exists(script_path, "Python runner")

        temp_output_log_dir = self.temp_data_dir / output_dir_name
        temp_output_log_dir.mkdir(parents=True, exist_ok=True)

        if log_name is None:
            log_name = Path(script_name).stem

        log_name = self._normalize_log_name(log_name)
        log_path = temp_output_log_dir / f"{log_name}.log"

        cleanup_dir: Path | None = None
        if temp_output_dir is not None:
            cleanup_dir = Path(temp_output_dir)
            script_args.extend(["--output-dir", str(cleanup_dir)])

        if profiler is not None:
            self._get_profiler_output_path(profiler, log_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        base_cmd = [self.python_command, str(script_path), *script_args]
        cmd = self._build_profiled_command(
            base_cmd=base_cmd,
            profiler=profiler,
            log_path=log_path,
            profiler_args=profiler_args,
        )

        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                result = subprocess.run(
                    cmd,
                    cwd=self.repo_root,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )

            if result.returncode != 0:
                if self._is_nonfatal_python_runner_failure(
                    log_path=log_path,
                    returncode=result.returncode,
                ):
                    self._append_warning_to_log(
                        log_path,
                        (
                            "Runner exited with a non-zero status due to a known "
                            "ACTS FPE-abort condition after event processing completed. "
                            "Treating this run as successful."
                        ),
                    )
                else:
                    raise RuntimeError(
                        f"Python runner failed with exit code {result.returncode}. "
                        f"See log: {log_path}"
                    )

            return log_path
        finally:
            if cleanup_dir is not None and cleanup_dir.exists():
                _rmtree_nfs_tolerant(cleanup_dir)

    def run_parser(
        self,
        parser_name: str,
        log_path: str | Path,
        output_dir_name: str,
        parsed_file_name: str,
    ) -> Path:

        parser_path = self.parsers_dir / parser_name
        log_path = Path(log_path).resolve()

        self._ensure_file_exists(parser_path, "Parser")
        self._ensure_file_exists(log_path, "Log file")

        parsed_output_dir = self.raw_data_dir / output_dir_name
        parsed_output_dir.mkdir(parents=True, exist_ok=True)

        parsed_output_path = parsed_output_dir / parsed_file_name

        cmd = [
            self.python_command,
            str(parser_path),
            str(log_path),
            str(parsed_output_path),
        ]
        self._run_command(cmd, cwd=self.repo_root)

        return parsed_output_path

    def _resolve_run_count(
        self,
        Sweep: dict[str, Sequence[Any]],
        Runs: int | None,
    ) -> int:

        if Runs is not None:
            if Runs <= 0:
                raise ValueError("Runs must be greater than 0")
            return Runs

        if not Sweep:
            return 1

        first_length = len(next(iter(Sweep.values())))
        if first_length <= 0:
            raise ValueError("Sweep values must not be empty")

        return first_length

    def _validate_sweep(
        self,
        Sweep: dict[str, Sequence[Any]],
        Runs: int,
    ) -> None:

        for argument_name, values in Sweep.items():
            if len(values) != Runs:
                raise ValueError(
                    f"Sweep argument {argument_name!r} has {len(values)} values, "
                    f"but Runs is {Runs}"
                )

    def _validate_profiler(self, profiler: str | None) -> None:

        valid_profilers = {None, "gperftools", "callgrind", "heaptrack"}
        if profiler not in valid_profilers:
            raise ValueError(
                "Unknown profiler. Supported values are: "
                "None, 'gperftools', 'callgrind', 'heaptrack'"
            )

    def _build_run_arguments(
        self,
        base_args: Sequence[str],
        Sweep: dict[str, Sequence[Any]],
        run_index: int,
    ) -> list[str]:

        run_args = list(base_args)

        for argument_name, values in Sweep.items():
            value = values[run_index]

            if isinstance(value, bool):
                if value:
                    run_args.append(str(argument_name))
                continue

            run_args.append(str(argument_name))
            run_args.append(str(value))

        return run_args

    def _build_run_log_name(
        self,
        base_log_name: str | None,
        python_runner: str,
        run_index: int,
        total_runs: int,
    ) -> str:
        
        if base_log_name is None:
            base_name = Path(python_runner).stem
        else:
            base_name = self._normalize_log_name(base_log_name)

        if total_runs == 1:
            return base_name

        return f"{base_name}_run{run_index + 1}"

    def _build_run_parsed_file_name(
        self,
        parsed_file_name: str,
        run_index: int,
        total_runs: int,
    ) -> str:

        if total_runs == 1:
            return parsed_file_name

        parsed_path = Path(parsed_file_name)
        return f"{parsed_path.stem}_run{run_index + 1}{parsed_path.suffix}"

    def _build_profiled_command(
        self,
        base_cmd: list[str],
        profiler: str | None,
        log_path: Path,
        profiler_args: Sequence[str] | None = None,
    ) -> list[str]:

        profiler_args = list(profiler_args or [])

        if profiler is None:
            return base_cmd

        if profiler == "gperftools":
            return [
                "env",
                f"CPUPROFILE={self._get_profiler_output_path(profiler, log_path)}",
                *profiler_args,
                *base_cmd,
            ]

        if profiler == "callgrind":
            cmd = [
                "valgrind",
                "--tool=callgrind",
                (
                    "--callgrind-out-file="
                    f"{self._get_profiler_output_path(profiler, log_path)}.%p.%n"
                ),
                "--cache-sim=yes",
                "--branch-sim=yes",
                "--collect-jumps=yes",
                "--dump-instr=yes",
            ]

            has_start_control = any(
                arg.startswith("--instr-atstart=") or arg.startswith("--collect-atstart=")
                for arg in profiler_args
            )
            if not has_start_control:
                cmd.append("--instr-atstart=no")

            cmd.extend(profiler_args)
            cmd.extend(base_cmd)
            return cmd

        if profiler == "heaptrack":
            return [
                "heaptrack",
                "-o",
                str(self._get_profiler_output_path(profiler, log_path)),
                *profiler_args,
                *base_cmd,
            ]

        raise ValueError(
            "Unknown profiler. Supported values are: "
            "'gperftools', 'callgrind', 'heaptrack'"
        )

    def _get_profiler_output_path(self, profiler: str, log_path: Path) -> Path:

        suffix_map = {
            "gperftools": ".prof",
            "callgrind":  ".callgrind",
            "heaptrack":  ".heaptrack",
        }
        if profiler not in suffix_map:
            raise ValueError(
                "Unknown profiler. Supported values are: "
                "'gperftools', 'callgrind', 'heaptrack'"
            )

        # log_path is raw-data/temp/<DataDir>/<base>.log; profiler path
        # is the parallel raw-data/<DataDir>/<base><suffix>.
        try:
            rel = log_path.relative_to(self.temp_data_dir)
        except ValueError:
            return log_path.with_suffix(suffix_map[profiler])
        return (self.raw_data_dir / rel).with_suffix(suffix_map[profiler])

    def _is_nonfatal_python_runner_failure(
        self,
        log_path: Path,
        returncode: int,
    ) -> bool:

        if returncode == 0:
            return False

        if not log_path.exists():
            return False

        log_text = log_path.read_text(encoding="utf-8", errors="replace")

        has_fpe_abort = (
            "Encountered 1 unmasked FPEs" in log_text
            or "Encountered 2 unmasked FPEs" in log_text
            or ("Encountered" in log_text and "unmasked FPEs" in log_text)
        )

        has_abnormal_termination = (
            "Sequencer terminated abnormally" in log_text
            or "RuntimeError: Sequencer terminated abnormally" in log_text
        )

        has_fatras_fpe_summary = (
            "FPE summary for Algorithm: FatrasSimulation" in log_text
        )

        processed_events = (
            "Processed 50 events" in log_text
            or ("Processed" in log_text and "events" in log_text)
            or "Processing events" in log_text
        )

        return (
            has_fpe_abort
            and has_abnormal_termination
            and has_fatras_fpe_summary
            and processed_events
        )

    def _append_warning_to_log(self, log_path: Path, message: str) -> None:

        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write("\n")
            log_file.write(f"[workflow warning] {message}\n")

    def _run_command(self, cmd: Sequence[str], cwd: str | Path | None = None) -> None:
        result = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            pretty_cmd = " ".join(shlex.quote(part) for part in cmd)
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}: {pretty_cmd}"
            )

    def _run_bash_command(self, command: str, cwd: str | Path | None = None) -> None:
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=str(cwd) if cwd is not None else None,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed with exit code {result.returncode}: {command}"
            )

    @staticmethod
    def _ensure_file_exists(path: Path, label: str) -> None:
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")

    @staticmethod
    def _normalize_log_name(log_name: str) -> str:
        if log_name.endswith(".log"):
            return log_name[:-4]
        return log_name
