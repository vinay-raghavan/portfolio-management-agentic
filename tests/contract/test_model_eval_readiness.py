from __future__ import annotations

import json

from scripts.run_agent_evals import EvalRunConfig, build_eval_commands, build_preflight


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
