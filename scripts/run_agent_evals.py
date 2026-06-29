from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping


GOOGLE_EVAL_CREDENTIAL_KEYS = (
    "GOOGLE_API_KEY",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_APPLICATION_CREDENTIALS",
)
PROVIDER_GENERATION_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "gemini": GOOGLE_EVAL_CREDENTIAL_KEYS,
    "claude": ("ANTHROPIC_API_KEY",),
    "openai_compatible": ("OPENAI_API_KEY",),
    "ollama": ("OLLAMA_BASE_URL",),
}


@dataclass(frozen=True)
class EvalRunConfig:
    provider: str = "gemini"
    app_dir: Path = Path("apps/agent-service")
    dataset: Path = Path("tests/eval/datasets/basic-dataset.json")
    eval_config: Path = Path("tests/eval/eval_config.yaml")
    traces_dir: Path = Path("artifacts/evals/traces")
    results_dir: Path = Path("artifacts/evals/grade-results")
    summary_output: Path = Path("artifacts/evals/baseline-summary.json")


@dataclass(frozen=True)
class EvalCommandResult:
    name: str
    command: list[str]
    return_code: int

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "command": self.command,
            "return_code": self.return_code,
        }


@dataclass(frozen=True)
class EvalPreflightReport:
    status: str
    provider: str
    working_directory: str
    dataset: str
    eval_config: str
    traces_dir: str
    results_dir: str
    summary_output: str
    commands: dict[str, list[str]]
    missing_environment: list[str]
    missing_binaries: list[str]
    missing_files: list[str]
    present_environment_keys: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "provider": self.provider,
            "working_directory": self.working_directory,
            "dataset": self.dataset,
            "eval_config": self.eval_config,
            "traces_dir": self.traces_dir,
            "results_dir": self.results_dir,
            "summary_output": self.summary_output,
            "commands": self.commands,
            "missing_environment": self.missing_environment,
            "missing_binaries": self.missing_binaries,
            "missing_files": self.missing_files,
            "present_environment_keys": self.present_environment_keys,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EvalRunSummary:
    status: str
    mode: str
    provider: str
    generated_at: str
    preflight: EvalPreflightReport
    command_results: list[EvalCommandResult]
    artifacts: dict[str, object]
    commands: dict[str, list[str]]
    notes: list[str]
    next_actions: list[str]
    schema_version: str = "portfolio-agent-eval-baseline/v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "mode": self.mode,
            "provider": self.provider,
            "generated_at": self.generated_at,
            "preflight": self.preflight.to_dict(),
            "command_results": [
                result.to_dict() for result in self.command_results
            ],
            "artifacts": self.artifacts,
            "commands": self.commands,
            "notes": self.notes,
            "next_actions": self.next_actions,
        }


def _env_has_any(env: Mapping[str, str], keys: tuple[str, ...]) -> bool:
    return any(bool(env.get(key)) for key in keys)


def _requirement_label(keys: tuple[str, ...]) -> str:
    return " or ".join(keys)


def _path_string(path: Path) -> str:
    return path.as_posix()


def _under_app(app_dir: Path, path: Path) -> Path:
    return path if path.is_absolute() else app_dir / path


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _artifact_files(app_dir: Path, path: Path) -> list[str]:
    resolved = _under_app(app_dir, path)
    if not resolved.exists():
        return []
    return sorted(
        _path_string(file.relative_to(resolved))
        for file in resolved.rglob("*")
        if file.is_file()
    )


def build_eval_commands(config: EvalRunConfig) -> dict[str, list[str]]:
    return {
        "generate": [
            "agents-cli",
            "eval",
            "generate",
            "--dataset",
            _path_string(config.dataset),
            "--output",
            _path_string(config.traces_dir),
        ],
        "grade": [
            "agents-cli",
            "eval",
            "grade",
            "--config",
            _path_string(config.eval_config),
            "--traces",
            _path_string(config.traces_dir),
            "--output",
            _path_string(config.results_dir),
        ],
    }


def build_compare_command(
    baseline_result: str | Path = "<baseline_results_json>",
    candidate_result: str | Path = "<candidate_results_json>",
) -> list[str]:
    return [
        "agents-cli",
        "eval",
        "compare",
        _path_string(Path(baseline_result)),
        _path_string(Path(candidate_result)),
    ]


def _missing_files(config: EvalRunConfig) -> list[str]:
    missing = []
    for path in (config.dataset, config.eval_config):
        resolved = _under_app(config.app_dir, path)
        if not resolved.exists():
            missing.append(_path_string(resolved))
    return missing


def build_preflight(
    config: EvalRunConfig,
    env: Mapping[str, str] | None = None,
    agents_cli_path: str | None = None,
) -> EvalPreflightReport:
    env = os.environ if env is None else env
    provider = config.provider.strip().lower()
    commands = build_eval_commands(config)
    missing_environment: list[str] = []
    missing_binaries: list[str] = []
    present_environment_keys: list[str] = []
    notes = [
        "Model-backed evals are credential-gated and skipped by default when required credentials are absent.",
        "The runner prints environment key names only; secret values are never included in preflight output.",
        "The official ADK eval path remains agents-cli eval generate followed by agents-cli eval grade.",
    ]

    provider_requirements = PROVIDER_GENERATION_REQUIREMENTS.get(provider)
    if provider_requirements is None:
        supported = ", ".join(sorted(PROVIDER_GENERATION_REQUIREMENTS))
        missing_environment.append(f"SUPPORTED_LLM_PROVIDER({supported})")
    elif not _env_has_any(env, provider_requirements):
        missing_environment.append(_requirement_label(provider_requirements))
    else:
        present_environment_keys.extend(
            key for key in provider_requirements if env.get(key)
        )

    if not _env_has_any(env, GOOGLE_EVAL_CREDENTIAL_KEYS):
        google_label = _requirement_label(GOOGLE_EVAL_CREDENTIAL_KEYS)
        if google_label not in missing_environment:
            missing_environment.append(google_label)
    else:
        present_environment_keys.extend(
            key for key in GOOGLE_EVAL_CREDENTIAL_KEYS if env.get(key)
        )

    if agents_cli_path is None:
        agents_cli_path = shutil.which("agents-cli")
    if not agents_cli_path:
        missing_binaries.append("agents-cli")

    missing_files = _missing_files(config)
    status = (
        "ready"
        if not missing_environment and not missing_binaries and not missing_files
        else "skipped"
    )

    return EvalPreflightReport(
        status=status,
        provider=provider,
        working_directory=_path_string(config.app_dir),
        dataset=_path_string(config.dataset),
        eval_config=_path_string(config.eval_config),
        traces_dir=_path_string(config.traces_dir),
        results_dir=_path_string(config.results_dir),
        summary_output=_path_string(config.summary_output),
        commands=commands,
        missing_environment=missing_environment,
        missing_binaries=missing_binaries,
        missing_files=missing_files,
        present_environment_keys=sorted(set(present_environment_keys)),
        notes=notes,
    )


def build_run_summary(
    *,
    mode: str,
    config: EvalRunConfig,
    preflight: EvalPreflightReport,
    status: str,
    command_results: list[EvalCommandResult],
    generated_at: str | None = None,
) -> EvalRunSummary:
    failed_results = [
        result for result in command_results if result.return_code != 0
    ]
    notes = [
        "Summary stores environment key names only; credential values are never recorded.",
        "Trace and grade result file names are listed relative to their artifact directories.",
        "The official ADK eval path remains agents-cli eval generate followed by agents-cli eval grade.",
    ]
    if failed_results:
        notes.append(
            f"First failed command: {failed_results[0].name} exited with {failed_results[0].return_code}."
        )

    if status == "skipped":
        next_actions = [
            "Configure the missing model or judge credentials shown by preflight.",
            "Rerun uv run python scripts/run_agent_evals.py run --fail-on-skip.",
        ]
    elif status == "failed":
        next_actions = [
            "Inspect the listed trace and grade result artifacts.",
            "Tune agent instructions, tool descriptions, or eval cases from the failing trajectory.",
            "Rerun the eval and compare against this baseline summary.",
        ]
    elif status == "completed":
        next_actions = [
            "Review the generated grade result JSON or HTML file.",
            "Use agents-cli eval compare with this baseline and a future candidate result.",
            "Promote concrete failures into deterministic tests or eval regressions.",
        ]
    elif status == "dry_run":
        next_actions = [
            "Remove --dry-run in a credentialed environment to generate traces and grade results.",
        ]
    else:
        next_actions = [
            "Use the preflight output to decide whether credentials, files, or agents-cli are missing.",
        ]

    return EvalRunSummary(
        status=status,
        mode=mode,
        provider=preflight.provider,
        generated_at=_utc_timestamp() if generated_at is None else generated_at,
        preflight=preflight,
        command_results=command_results,
        artifacts={
            "traces_dir": _path_string(config.traces_dir),
            "results_dir": _path_string(config.results_dir),
            "summary_output": _path_string(config.summary_output),
            "trace_files": _artifact_files(config.app_dir, config.traces_dir),
            "grade_result_files": _artifact_files(config.app_dir, config.results_dir),
        },
        commands={
            **preflight.commands,
            "compare_template": build_compare_command(),
        },
        notes=notes,
        next_actions=next_actions,
    )


def write_run_summary(summary: EvalRunSummary, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _print_report(report: EvalPreflightReport, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    print(f"Eval preflight: {report.status}")
    print(f"Provider: {report.provider}")
    print(f"Working directory: {report.working_directory}")
    if report.missing_environment:
        print(f"Missing environment: {', '.join(report.missing_environment)}")
    if report.missing_binaries:
        print(f"Missing binaries: {', '.join(report.missing_binaries)}")
    if report.missing_files:
        print(f"Missing files: {', '.join(report.missing_files)}")
    print("Generate command:")
    print(" ".join(report.commands["generate"]))
    print("Grade command:")
    print(" ".join(report.commands["grade"]))


CommandRunner = Callable[[list[str], Path], int]


def _run(command: list[str], cwd: Path) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode


def run_eval_mode(
    mode: str,
    config: EvalRunConfig,
    runner: CommandRunner | None = None,
) -> list[EvalCommandResult]:
    runner = _run if runner is None else runner
    commands = build_eval_commands(config)
    _under_app(config.app_dir, config.traces_dir).mkdir(parents=True, exist_ok=True)
    _under_app(config.app_dir, config.results_dir).mkdir(parents=True, exist_ok=True)
    results: list[EvalCommandResult] = []
    if mode in {"generate", "run"}:
        result = EvalCommandResult(
            "generate",
            commands["generate"],
            runner(commands["generate"], config.app_dir),
        )
        results.append(result)
        if result.return_code != 0:
            return results
    if mode in {"grade", "run"}:
        result = EvalCommandResult(
            "grade",
            commands["grade"],
            runner(commands["grade"], config.app_dir),
        )
        results.append(result)
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Credential-aware runner for ADK model-backed evals."
    )
    parser.add_argument(
        "mode",
        choices=("preflight", "generate", "grade", "run"),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--provider", default=os.getenv("LLM_PROVIDER", "gemini"))
    parser.add_argument("--app-dir", type=Path, default=Path("apps/agent-service"))
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/eval/datasets/basic-dataset.json"),
    )
    parser.add_argument(
        "--config",
        dest="eval_config",
        type=Path,
        default=Path("tests/eval/eval_config.yaml"),
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        default=Path("artifacts/evals/traces"),
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("artifacts/evals/grade-results"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("artifacts/evals/baseline-summary.json"),
        help="Write a redacted eval run summary relative to the app directory by default.",
    )
    parser.add_argument("--json", action="store_true", help="Print preflight as JSON.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print readiness and commands without running agents-cli.",
    )
    parser.add_argument(
        "--fail-on-skip",
        action="store_true",
        help="Return a non-zero exit code when preflight is skipped.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = EvalRunConfig(
        provider=args.provider,
        app_dir=args.app_dir,
        dataset=args.dataset,
        eval_config=args.eval_config,
        traces_dir=args.traces_dir,
        results_dir=args.results_dir,
        summary_output=args.summary_output,
    )
    report = build_preflight(config)
    _print_report(report, as_json=args.json)

    command_results: list[EvalCommandResult] = []
    if report.status != "ready":
        status = "skipped"
        return_code = 2 if args.fail_on_skip else 0
    elif args.mode == "preflight":
        status = "ready"
        return_code = 0
    elif args.dry_run:
        status = "dry_run"
        return_code = 0
    else:
        command_results = run_eval_mode(args.mode, config)
        failed_result = next(
            (result for result in command_results if result.return_code != 0),
            None,
        )
        status = "failed" if failed_result else "completed"
        return_code = 0 if failed_result is None else failed_result.return_code

    summary = build_run_summary(
        mode=args.mode,
        config=config,
        preflight=report,
        status=status,
        command_results=command_results,
    )
    summary_path = write_run_summary(
        summary,
        _under_app(config.app_dir, config.summary_output),
    )
    print(f"Eval summary: {_path_string(summary_path)}", file=sys.stderr)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
