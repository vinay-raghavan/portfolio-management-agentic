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
                        "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS"
                    ],
                    "present_environment_keys": [],
                },
                "artifacts": {
                    "trace_files": [],
                    "grade_result_files": [],
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
    assert payload["eval_baseline"]["status"] == "skipped"
    assert payload["eval_baseline"]["triage_status"] == "no_results"
    assert payload["eval_baseline"]["missing_environment"] == [
        "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT or GOOGLE_APPLICATION_CREDENTIALS"
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
