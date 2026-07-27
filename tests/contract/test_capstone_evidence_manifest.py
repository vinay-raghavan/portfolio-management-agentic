from __future__ import annotations

import json
from pathlib import Path

from scripts.build_capstone_evidence import (
    CapstoneEvidenceConfig,
    build_capstone_evidence,
    write_capstone_evidence,
)


def test_capstone_evidence_manifest_is_repo_safe_and_actionable(tmp_path: Path) -> None:
    app_dir = tmp_path / "apps" / "agent-service"
    eval_dir = app_dir / "artifacts" / "evals"
    eval_dir.mkdir(parents=True)
    (eval_dir / "baseline-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-baseline/v1",
                "status": "skipped",
                "preflight": {
                    "status": "skipped",
                    "missing_environment": [
                        "GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS",
                        "GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS",
                        "GOOGLE_APPLICATION_CREDENTIALS or gcloud application-default credentials",
                    ],
                    "present_environment_keys": [],
                },
                "artifacts": {
                    "trace_files": [],
                    "grade_result_files": [],
                },
                "submission_readiness": {
                    "status": "blocked",
                    "blocking_reasons": [
                        "Missing credential environment: GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_APPLICATION_CREDENTIALS or gcloud application-default credentials"
                    ],
                    "required_next_actions": [
                        "Configure the missing preflight requirements and rerun uv run python scripts/run_agent_evals.py run --fail-on-skip."
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "triage-report.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-triage/v1",
                "status": "no_results",
                "summary": {"failure_count": 0},
            }
        ),
        encoding="utf-8",
    )

    manifest = build_capstone_evidence(
        CapstoneEvidenceConfig(repo_root=tmp_path),
        generated_at="2026-06-29T00:00:00Z",
    )
    payload = manifest.to_dict()
    serialized = json.dumps(payload)

    assert payload["schema_version"] == "portfolio-agentic-capstone-evidence/v1"
    assert payload["generated_at"] == "2026-06-29T00:00:00Z"
    assert payload["product_scope"] == {
        "mode": "governed_trading_workflow_platform",
        "capstone_execution_mode": "approval_gated_paper_simulation",
        "live_execution_status": "disabled_until_explicit_production_controls",
        "deployment_shape": "Docker or Podman Compose",
        "default_data_mode": "offline_safe_fixtures",
        "configured_data_mode": "read_only_provider_adapters",
    }
    assert payload["eval_baseline"]["status"] == "skipped"
    assert payload["eval_baseline"]["triage_status"] == "no_results"
    assert payload["eval_baseline"]["missing_environment"] == [
        "GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_APPLICATION_CREDENTIALS or gcloud application-default credentials",
    ]
    assert payload["eval_baseline"]["submission_readiness"]["status"] == "blocked"
    assert payload["eval_baseline"]["submission_readiness"]["blocking_reasons"] == [
        "Missing credential environment: GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_APPLICATION_CREDENTIALS or gcloud application-default credentials"
    ]
    assert payload["verification_commands"] == [
        "uv run pytest tests",
        "cd apps/agent-service && uv run pytest tests/unit tests/integration",
        "podman compose config --quiet",
        "cd apps/web && npm run typecheck && npm run build",
        "uv run python scripts/run_agent_evals.py preflight --json",
        "uv run python scripts/run_agent_evals.py triage --json",
    ]
    assert {
        "pre_market_briefing",
        "configured_provider_readiness",
        "multi_factor_screener",
        "recommendation_to_pending_paper_order",
        "approval_gated_simulated_fill",
        "paper_trading_report",
        "forbidden_live_trading_refusal",
    }.issubset({item["id"] for item in payload["workflow_evidence"]})
    assert all(item["status"] == "implemented" for item in payload["workflow_evidence"])
    assert "credentialed_model_eval_baseline" in {
        item["id"] for item in payload["remaining_gaps"]
    }
    assert "capstone_media_package" in {
        item["id"] for item in payload["remaining_gaps"]
    }
    assert "/" + "Users/" not in serialized
    assert str(tmp_path) not in serialized
    assert "super-secret" not in serialized
    assert "fyers" not in serialized.lower()


def test_write_capstone_evidence_creates_parent_directory(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "capstone" / "evidence-manifest.json"
    manifest = build_capstone_evidence(
        CapstoneEvidenceConfig(repo_root=tmp_path),
        generated_at="2026-06-29T00:00:00Z",
    )

    written = write_capstone_evidence(manifest, output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert written == output
    assert payload["schema_version"] == "portfolio-agentic-capstone-evidence/v1"


def test_capstone_evidence_marks_passing_eval_ready_for_submission(
    tmp_path: Path,
) -> None:
    eval_dir = tmp_path / "apps" / "agent-service" / "artifacts" / "evals"
    eval_dir.mkdir(parents=True)
    (eval_dir / "baseline-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-baseline/v1",
                "status": "completed",
                "candidate_commit": "abc123def456",
                "preflight": {
                    "status": "ready",
                    "missing_environment": [],
                    "present_environment_keys": ["GOOGLE_API_KEY"],
                },
                "artifacts": {
                    "trace_files": ["trace_001.json"],
                    "grade_result_files": ["results_001.json"],
                },
                "submission_readiness": {
                    "status": "ready_for_triage",
                    "blocking_reasons": [],
                    "required_next_actions": [
                        "Run uv run python scripts/run_agent_evals.py triage --json."
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "triage-report.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-triage/v1",
                "status": "passed",
                "candidate_commit": "abc123def456",
                "summary": {"failure_count": 0, "critical_failure_count": 0},
                "submission_readiness": {
                    "status": "ready_for_capstone_submission",
                    "blocking_reasons": [],
                    "required_next_actions": [
                        "Keep the baseline summary, triage report, traces, and grade artifacts with the capstone evidence package.",
                        "Regenerate uv run python scripts/build_capstone_evidence.py.",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    media_dir = tmp_path / "docs" / "capstone" / "media" / "slides"
    media_dir.mkdir(parents=True)
    for filename in (
        "01-cover.png",
        "03-system-architecture.png",
        "05-agentic-workflow.png",
        "06-safety-model.png",
        "08-evaluation-deployability.png",
    ):
        (media_dir / filename).write_bytes(b"repo-safe-evidence")
    (tmp_path / "docs" / "capstone" / "TradePilot-Sentinel-Capstone.pptx").write_bytes(
        b"repo-safe-deck"
    )

    payload = build_capstone_evidence(
        CapstoneEvidenceConfig(repo_root=tmp_path),
        generated_at="2026-06-29T00:00:00Z",
    ).to_dict()

    assert payload["eval_baseline"]["submission_readiness"]["status"] == (
        "ready_for_capstone_submission"
    )
    assert payload["eval_baseline"]["triage_failure_count"] == 0
    assert "credentialed_model_eval_baseline" not in {
        item["id"] for item in payload["remaining_gaps"]
    }
    assert "eval_grade_artifacts" not in {
        item["id"] for item in payload["remaining_gaps"]
    }
    assert payload["submission_assets"]["status"] == "ready"
    assert "capstone_media_package" not in {
        item["id"] for item in payload["remaining_gaps"]
    }


def test_capstone_evidence_blocks_mismatched_eval_candidate_commits(
    tmp_path: Path,
) -> None:
    eval_dir = tmp_path / "apps" / "agent-service" / "artifacts" / "evals"
    eval_dir.mkdir(parents=True)
    (eval_dir / "baseline-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-baseline/v1",
                "status": "completed",
                "candidate_commit": "abc123def456",
                "preflight": {
                    "status": "ready",
                    "missing_environment": [],
                    "present_environment_keys": ["GOOGLE_API_KEY"],
                },
                "artifacts": {
                    "trace_files": ["trace_001.json"],
                    "grade_result_files": ["results_001.json"],
                },
                "submission_readiness": {
                    "status": "ready_for_triage",
                    "blocking_reasons": [],
                    "required_next_actions": [
                        "Run uv run python scripts/run_agent_evals.py triage --json."
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "triage-report.json").write_text(
        json.dumps(
            {
                "schema_version": "portfolio-agent-eval-triage/v1",
                "status": "passed",
                "candidate_commit": "def456abc789",
                "summary": {"failure_count": 0, "critical_failure_count": 0},
                "submission_readiness": {
                    "status": "ready_for_capstone_submission",
                    "blocking_reasons": [],
                    "required_next_actions": [
                        "Keep the baseline summary, triage report, traces, and grade artifacts with the capstone evidence package.",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    payload = build_capstone_evidence(
        CapstoneEvidenceConfig(repo_root=tmp_path),
        generated_at="2026-06-29T00:00:00Z",
    ).to_dict()

    assert payload["eval_baseline"]["candidate_commit"] == "abc123def456"
    assert payload["eval_baseline"]["triage_candidate_commit"] == "def456abc789"
    assert payload["eval_baseline"]["submission_readiness"] == {
        "status": "commit_mismatch",
        "source": "candidate_commit",
        "blocking_reasons": [
            "Eval baseline and triage report are not bound to the same candidate commit."
        ],
        "required_next_actions": [
            "Rerun uv run python scripts/run_agent_evals.py run --fail-on-skip and uv run python scripts/run_agent_evals.py triage --json for the exact candidate commit."
        ],
    }
    assert {
        "id": "eval_commit_binding",
        "status": "candidate_commit_mismatch",
        "next_action": "Rerun the credentialed eval baseline and triage for the exact candidate commit.",
    } in payload["remaining_gaps"]
