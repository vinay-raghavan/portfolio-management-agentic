from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "portfolio-agentic-capstone-evidence/v1"


@dataclass(frozen=True)
class CapstoneEvidenceConfig:
    repo_root: Path = Path(".")
    eval_summary: Path = Path("apps/agent-service/artifacts/evals/baseline-summary.json")
    triage_report: Path = Path("apps/agent-service/artifacts/evals/triage-report.json")
    submission_deck: Path = Path(
        "docs/capstone/TradePilot-Sentinel-Capstone.pptx"
    )
    submission_media_dir: Path = Path("docs/capstone/media/slides")


@dataclass(frozen=True)
class CapstoneEvidenceManifest:
    generated_at: str
    eval_baseline: dict[str, Any]
    submission_assets: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "purpose": "Repo-safe capstone evidence manifest for TradePilot Sentinel.",
            "product_scope": {
                "mode": "governed_trading_workflow_platform",
                "capstone_execution_mode": "approval_gated_paper_simulation",
                "live_execution_status": "disabled_until_explicit_production_controls",
                "deployment_shape": "Docker or Podman Compose",
                "default_data_mode": "offline_safe_fixtures",
                "configured_data_mode": "read_only_provider_adapters",
            },
            "safety_boundaries": [
                "No live order placement.",
                "No live strategy enablement.",
                "No broker trading-token access.",
                "No provider secret disclosure.",
                "No local absolute paths, raw provider payloads, or real account data in evidence artifacts.",
                "Paper fills require human approval before simulation.",
            ],
            "verification_commands": [
                "uv run pytest tests",
                "cd apps/agent-service && uv run pytest tests/unit tests/integration",
                "podman compose config --quiet",
                "cd apps/web && npm run typecheck && npm run build",
                "uv run python scripts/run_agent_evals.py preflight --json",
                "uv run python scripts/run_agent_evals.py triage --json",
            ],
            "container_runtime": {
                "compose_commands": [
                    "docker compose up --build",
                    "podman compose up --build",
                ],
                "services": [
                    {
                        "id": "agent-service",
                        "url": "http://localhost:8000",
                        "role": "ADK agent and FastAPI console API",
                    },
                    {
                        "id": "mcp-server",
                        "url": "http://localhost:8081/mcp",
                        "role": "Safe MCP tool boundary",
                    },
                    {
                        "id": "web-console",
                        "url": "http://localhost:3000",
                        "role": "React workflow console",
                    },
                ],
                "optional_profiles": ["ollama"],
            },
            "workflow_evidence": _workflow_evidence(),
            "eval_baseline": self.eval_baseline,
            "submission_assets": self.submission_assets,
            "ci_cd_evidence": {
                "ci_workflow": ".github/workflows/ci.yml",
                "cd_workflow": ".github/workflows/cd.yml",
                "manual_eval_workflow": ".github/workflows/eval-baseline.yml",
                "release_boundary": "CD publishes images only on v* tags or explicit manual dispatch.",
            },
            "repo_safe_artifact_paths": [
                "apps/agent-service/artifacts/evals/baseline-summary.json",
                "apps/agent-service/artifacts/evals/triage-report.json",
                "artifacts/capstone/evidence-manifest.json",
                "docs/capstone/evidence/eval-summary.json",
                "docs/capstone/TradePilot-Sentinel-Capstone.pptx",
                "docs/capstone/media/slides",
            ],
            "remaining_gaps": _remaining_gaps(
                self.eval_baseline, self.submission_assets
            ),
        }


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _relative_artifact_names(payload: Mapping[str, Any], key: str) -> list[str]:
    artifacts = _as_dict(payload.get("artifacts"))
    return [
        str(item)
        for item in _safe_list(artifacts.get(key))
        if isinstance(item, str) and "/" not in item and "\\" not in item
    ]


def _workflow_evidence() -> list[dict[str, Any]]:
    return [
        {
            "id": "pre_market_briefing",
            "status": "implemented",
            "evidence": [
                "create_pre_market_briefing",
                "get_portfolio_summary",
                "get_watchlist_snapshot",
                "get_signal_summary",
                "get_research_digest",
                "get_risk_review",
            ],
        },
        {
            "id": "configured_provider_readiness",
            "status": "implemented",
            "evidence": [
                "list_data_providers",
                "get_data_provider_health",
                "validate_data_provider_imports",
                "list_provider_source_onboarding",
                "list_provider_import_previews",
                "list_provider_import_reconciliation",
                "get_provider_refresh_readiness",
            ],
        },
        {
            "id": "multi_factor_screener",
            "status": "implemented",
            "evidence": [
                "run_screener",
                "explain_candidate_evidence",
                "explain_factor_stack",
                "search_pattern_library",
                "cite_strategy_evidence",
            ],
        },
        {
            "id": "recommendation_to_pending_paper_order",
            "status": "implemented",
            "evidence": [
                "get_recommendation_explanation",
                "create_backtest_request",
                "get_backtest_result",
                "create_paper_order_proposal",
                "get_approval_queue",
                "get_audit_events",
            ],
        },
        {
            "id": "approval_gated_simulated_fill",
            "status": "implemented",
            "evidence": [
                "approve_paper_order_simulation",
                "simulate_approved_paper_fill",
                "get_paper_portfolio_accounting",
                "get_audit_events",
            ],
        },
        {
            "id": "paper_trading_report",
            "status": "implemented",
            "evidence": ["generate_paper_trading_report"],
        },
        {
            "id": "forbidden_live_trading_refusal",
            "status": "implemented",
            "evidence": [
                "forbidden_action_policy",
                "workflow_tool_trajectory_policy",
                "policy forbidden compatibility traps remain unregistered",
            ],
        },
    ]


def _build_eval_baseline(config: CapstoneEvidenceConfig) -> dict[str, Any]:
    summary = _as_dict(_load_json(config.repo_root / config.eval_summary))
    triage = _as_dict(_load_json(config.repo_root / config.triage_report))
    preflight = _as_dict(summary.get("preflight"))
    summary_readiness = _as_dict(summary.get("submission_readiness"))
    triage_readiness = _as_dict(triage.get("submission_readiness"))
    triage_summary = _as_dict(triage.get("summary"))
    trace_files = _relative_artifact_names(summary, "trace_files")
    grade_result_files = _relative_artifact_names(summary, "grade_result_files")
    failure_count = triage_summary.get("failure_count", 0)
    critical_failure_count = triage_summary.get("critical_failure_count", 0)

    return {
        "status": str(summary.get("status") or "not_run"),
        "schema_version": str(summary.get("schema_version") or ""),
        "preflight_status": str(preflight.get("status") or ""),
        "triage_status": str(triage.get("status") or "not_run"),
        "submission_readiness": _eval_submission_readiness(
            baseline_status=str(summary.get("status") or "not_run"),
            summary_readiness=summary_readiness,
            triage_status=str(triage.get("status") or "not_run"),
            triage_readiness=triage_readiness,
            trace_files=trace_files,
            grade_result_files=grade_result_files,
            failure_count=failure_count,
        ),
        "missing_environment": [
            str(item) for item in _safe_list(preflight.get("missing_environment"))
        ],
        "present_environment_keys": [
            str(item) for item in _safe_list(preflight.get("present_environment_keys"))
        ],
        "trace_files": trace_files,
        "grade_result_files": grade_result_files,
        "triage_failure_count": failure_count,
        "triage_critical_failure_count": critical_failure_count,
        "runbook": "docs/runbooks/model-eval-baseline.md",
    }


def _eval_submission_readiness(
    *,
    baseline_status: str,
    summary_readiness: Mapping[str, Any],
    triage_status: str,
    triage_readiness: Mapping[str, Any],
    trace_files: list[str],
    grade_result_files: list[str],
    failure_count: Any,
) -> dict[str, Any]:
    if baseline_status != "completed":
        return {
            "status": "blocked",
            "source": "baseline_summary",
            "blocking_reasons": _safe_string_list(
                summary_readiness.get("blocking_reasons")
            )
            or ["Credentialed model eval baseline has not completed."],
            "required_next_actions": _safe_string_list(
                summary_readiness.get("required_next_actions")
            )
            or [
                "Configure model credentials and run uv run python scripts/run_agent_evals.py run --fail-on-skip."
            ],
        }
    if not trace_files or not grade_result_files:
        missing = []
        if not trace_files:
            missing.append("No eval trace artifacts were listed.")
        if not grade_result_files:
            missing.append("No eval grade-result artifacts were listed.")
        return {
            "status": "artifact_gap",
            "source": "baseline_summary",
            "blocking_reasons": missing,
            "required_next_actions": [
                "Inspect agents-cli output and rerun uv run python scripts/run_agent_evals.py run --fail-on-skip."
            ],
        }
    if triage_status == "passed":
        return {
            "status": "ready_for_capstone_submission",
            "source": "triage_report",
            "blocking_reasons": _safe_string_list(
                triage_readiness.get("blocking_reasons")
            ),
            "required_next_actions": _safe_string_list(
                triage_readiness.get("required_next_actions")
            )
            or ["Keep eval artifacts with the capstone evidence package."],
        }
    if triage_status == "failures_detected":
        return {
            "status": "needs_hardening",
            "source": "triage_report",
            "blocking_reasons": _safe_string_list(
                triage_readiness.get("blocking_reasons")
            )
            or [f"{failure_count} eval failure(s) detected."],
            "required_next_actions": _safe_string_list(
                triage_readiness.get("required_next_actions")
            )
            or ["Fix triaged eval failures and rerun the credentialed baseline."],
        }
    return {
        "status": "needs_triage",
        "source": "baseline_summary",
        "blocking_reasons": ["Credentialed eval completed but triage has not passed."],
        "required_next_actions": [
            "Run uv run python scripts/run_agent_evals.py triage --json."
        ],
    }


def _safe_string_list(value: Any) -> list[str]:
    return [str(item) for item in _safe_list(value)]


def _build_submission_assets(config: CapstoneEvidenceConfig) -> dict[str, Any]:
    required_slides = [
        "01-cover.png",
        "03-system-architecture.png",
        "05-agentic-workflow.png",
        "06-safety-model.png",
        "08-evaluation-deployability.png",
    ]
    deck_path = config.repo_root / config.submission_deck
    media_dir = config.repo_root / config.submission_media_dir
    missing = [
        filename for filename in required_slides if not (media_dir / filename).is_file()
    ]
    if not deck_path.is_file():
        missing.append(config.submission_deck.name)
    return {
        "status": "ready" if not missing else "incomplete",
        "deck": config.submission_deck.as_posix(),
        "media_directory": config.submission_media_dir.as_posix(),
        "required_slides": required_slides,
        "missing": missing,
    }


def _remaining_gaps(
    eval_baseline: Mapping[str, Any],
    submission_assets: Mapping[str, Any],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    readiness = _as_dict(eval_baseline.get("submission_readiness"))
    readiness_status = str(readiness.get("status") or "blocked")
    if eval_baseline.get("status") != "completed":
        gaps.append(
            {
                "id": "credentialed_model_eval_baseline",
                "status": "blocked_without_model_credentials",
                "next_action": "Configure model or judge credentials and run uv run python scripts/run_agent_evals.py run --fail-on-skip.",
            }
        )
    elif readiness_status == "needs_triage":
        gaps.append(
            {
                "id": "eval_triage_report",
                "status": "pending_triage",
                "next_action": "Run uv run python scripts/run_agent_evals.py triage --json.",
            }
        )
    elif readiness_status == "needs_hardening":
        gaps.append(
            {
                "id": "eval_failure_hardening",
                "status": "pending_eval_fixes",
                "next_action": "Fix or disposition triaged eval failures, then rerun the credentialed baseline and triage.",
            }
        )
    elif readiness_status == "artifact_gap":
        gaps.append(
            {
                "id": "eval_artifact_gap",
                "status": "missing_eval_artifacts",
                "next_action": "Rerun the credentialed eval and confirm traces plus grade results are listed.",
            }
        )
    if not eval_baseline.get("grade_result_files"):
        gaps.append(
            {
                "id": "eval_grade_artifacts",
                "status": "pending_credentialed_eval",
                "next_action": "Upload or review grade artifacts after the first credentialed baseline.",
            }
        )
    if submission_assets.get("status") != "ready":
        gaps.append(
            {
                "id": "capstone_media_package",
                "status": "missing_repo_safe_submission_assets",
                "next_action": "Create the capstone deck and required 16:9 media slides under docs/capstone.",
            }
        )
    return gaps


def build_capstone_evidence(
    config: CapstoneEvidenceConfig | None = None,
    generated_at: str | None = None,
) -> CapstoneEvidenceManifest:
    resolved_config = CapstoneEvidenceConfig() if config is None else config
    return CapstoneEvidenceManifest(
        generated_at=generated_at or _utc_timestamp(),
        eval_baseline=_build_eval_baseline(resolved_config),
        submission_assets=_build_submission_assets(resolved_config),
    )


def write_capstone_evidence(
    manifest: CapstoneEvidenceManifest,
    output: Path,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a repo-safe capstone evidence manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/capstone/evidence-manifest.json"),
    )
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest = build_capstone_evidence()
    written = write_capstone_evidence(manifest, args.output)
    if args.json:
        print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"Capstone evidence manifest: {written.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
