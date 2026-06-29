from __future__ import annotations

import json
from pathlib import Path

from scripts.run_agent_evals import (
    EvalCommandResult,
    EvalRunConfig,
    build_eval_commands,
    build_preflight,
    build_run_summary,
    run_eval_mode,
    write_run_summary,
)


def test_eval_commands_use_official_generate_and_grade_path() -> None:
    commands = build_eval_commands(EvalRunConfig())

    assert commands["generate"][:3] == ["agents-cli", "eval", "generate"]
    assert "--dataset" in commands["generate"]
    assert "tests/eval/datasets/basic-dataset.json" in commands["generate"]
    assert "--output" in commands["generate"]
    assert "artifacts/evals/traces" in commands["generate"]

    assert commands["grade"][:3] == ["agents-cli", "eval", "grade"]
    assert "--config" in commands["grade"]
    assert "tests/eval/eval_config.yaml" in commands["grade"]
    assert "--traces" in commands["grade"]
    assert "artifacts/evals/traces" in commands["grade"]
    assert "--output" in commands["grade"]
    assert "artifacts/evals/grade-results" in commands["grade"]


def test_eval_preflight_skips_without_credentials() -> None:
    report = build_preflight(
        EvalRunConfig(provider="gemini"),
        env={},
        agents_cli_path="/usr/local/bin/agents-cli",
    )

    assert report.status == "skipped"
    assert "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS" in report.missing_environment
    assert report.commands["generate"][:3] == ["agents-cli", "eval", "generate"]
    assert report.commands["grade"][:3] == ["agents-cli", "eval", "grade"]


def test_eval_preflight_is_ready_with_provider_and_judge_credentials() -> None:
    report = build_preflight(
        EvalRunConfig(provider="gemini"),
        env={"GOOGLE_API_KEY": "super-secret-value"},
        agents_cli_path="/usr/local/bin/agents-cli",
    )

    serialized = json.dumps(report.to_dict())

    assert report.status == "ready"
    assert report.missing_environment == []
    assert "super-secret-value" not in serialized
    assert "GOOGLE_API_KEY" in report.present_environment_keys


def test_eval_preflight_requires_provider_specific_generation_credentials() -> None:
    report = build_preflight(
        EvalRunConfig(provider="claude"),
        env={"GOOGLE_API_KEY": "judge-only"},
        agents_cli_path="/usr/local/bin/agents-cli",
    )

    assert report.status == "skipped"
    assert "ANTHROPIC_API_KEY" in report.missing_environment
    assert "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS" not in report.missing_environment


def test_eval_run_mode_records_command_results_and_stops_on_failure(tmp_path: Path) -> None:
    config = EvalRunConfig(app_dir=tmp_path)
    calls: list[list[str]] = []

    def failing_runner(command: list[str], cwd: Path) -> int:
        calls.append(command)
        assert cwd == tmp_path
        return 7

    results = run_eval_mode("run", config, runner=failing_runner)

    assert [result.name for result in results] == ["generate"]
    assert results[0].return_code == 7
    assert calls == [build_eval_commands(config)["generate"]]
    assert (tmp_path / "artifacts/evals/traces").is_dir()
    assert (tmp_path / "artifacts/evals/grade-results").is_dir()


def test_eval_run_summary_records_artifacts_without_secret_values(tmp_path: Path) -> None:
    config = EvalRunConfig(
        provider="gemini",
        app_dir=tmp_path,
        summary_output=Path("artifacts/evals/baseline-summary.json"),
    )
    traces_dir = tmp_path / config.traces_dir
    results_dir = tmp_path / config.results_dir
    traces_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)
    (traces_dir / "trace_001.json").write_text("{}", encoding="utf-8")
    (results_dir / "results_001.json").write_text("{}", encoding="utf-8")

    report = build_preflight(
        config,
        env={"GOOGLE_API_KEY": "super-secret-value"},
        agents_cli_path="/usr/local/bin/agents-cli",
    )
    summary = build_run_summary(
        mode="run",
        config=config,
        preflight=report,
        status="completed",
        command_results=[
            EvalCommandResult("generate", report.commands["generate"], 0),
            EvalCommandResult("grade", report.commands["grade"], 0),
        ],
        generated_at="2026-06-29T00:00:00Z",
    )
    payload = summary.to_dict()
    serialized = json.dumps(payload)

    assert payload["schema_version"] == "portfolio-agent-eval-baseline/v1"
    assert payload["status"] == "completed"
    assert payload["artifacts"]["trace_files"] == ["trace_001.json"]
    assert payload["artifacts"]["grade_result_files"] == ["results_001.json"]
    assert payload["commands"]["compare_template"] == [
        "agents-cli",
        "eval",
        "compare",
        "<baseline_results_json>",
        "<candidate_results_json>",
    ]
    assert "super-secret-value" not in serialized
    assert payload["preflight"]["present_environment_keys"] == ["GOOGLE_API_KEY"]


def test_write_run_summary_creates_parent_directory(tmp_path: Path) -> None:
    config = EvalRunConfig(app_dir=tmp_path)
    report = build_preflight(config, env={}, agents_cli_path="/usr/local/bin/agents-cli")
    summary = build_run_summary(
        mode="preflight",
        config=config,
        preflight=report,
        status="skipped",
        command_results=[],
        generated_at="2026-06-29T00:00:00Z",
    )

    output = tmp_path / "nested" / "summary.json"
    written = write_run_summary(summary, output)

    assert written == output
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "portfolio-agent-eval-baseline/v1"
    assert data["status"] == "skipped"
