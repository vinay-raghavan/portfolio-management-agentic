from __future__ import annotations

from pathlib import Path


WORKFLOWS = Path(".github/workflows")


def test_ci_workflow_runs_required_deterministic_checks() -> None:
    ci = (WORKFLOWS / "ci.yml").read_text()

    assert "uv run pytest tests" in ci
    assert "scripts/run_agent_evals.py preflight --json" in ci
    assert "uv run pytest tests/unit tests/integration" in ci
    assert "working-directory: apps/web" in ci
    assert "npm ci" in ci
    assert "npm audit --audit-level=moderate" in ci
    assert "npm run typecheck" in ci
    assert "npm run build" in ci
    assert "docker compose config --quiet" in ci
    assert "docker compose build agent-service paper-execution-worker mcp-server web" in ci
    assert "docker compose up -d agent-service paper-execution-worker mcp-server web" in ci
    assert "http://127.0.0.1:3000" in ci
    assert "streamable_http_client" in ci
    assert "from portfolio_mcp.tools import EXPOSED_TOOL_NAMES" in ci
    assert "assert tool_names == EXPOSED_TOOL_NAMES" in ci
    assert "place_live_order" in ci
    assert "get_broker_trading_token" in ci


def test_ci_workflow_uses_read_only_repository_permissions() -> None:
    ci = (WORKFLOWS / "ci.yml").read_text()

    assert "permissions:\n  contents: read" in ci
    assert "packages: write" not in ci
    assert "secrets." not in ci


def test_cd_workflow_is_release_gated_and_publishes_only_images() -> None:
    cd = (WORKFLOWS / "cd.yml").read_text()

    assert 'tags:\n      - "v*"' in cd
    assert "workflow_dispatch:" in cd
    assert "actions: read" in cd
    assert "verify-eval-artifact:" in cd
    assert "needs: verify-eval-artifact" in cd
    assert "portfolio-agentic-eval-artifacts-${GITHUB_SHA}" in cd
    assert "workflow_run.head_sha == env.GITHUB_SHA" in cd
    assert "Eval artifact workflow run did not conclude successfully" in cd
    assert 'load_required("baseline-summary.json")' in cd
    assert 'load_required("triage-report.json")' in cd
    assert 'baseline.get("candidate_commit") != expected_commit' in cd
    assert 'triage.get("candidate_commit") != expected_commit' in cd
    assert 'baseline.get("status") != "completed"' in cd
    assert 'triage.get("status") != "passed"' in cd
    assert 'readiness.get("status") != "ready_for_capstone_submission"' in cd
    assert 'metric_coverage.get("observed_total_metric_results") != 45' in cd
    assert 'artifact_dir.rglob("traces/*.json")' in cd
    assert 'artifact_dir.rglob("grade-results/*.json")' in cd
    assert "packages: write" in cd
    assert "docker/build-push-action" in cd
    assert "portfolio-management-agentic-agent-service" in cd
    assert "portfolio-management-agentic-mcp-server" in cd
    assert "portfolio-management-agentic-web" in cd
    assert "fyers" not in cd.lower()
    assert "broker-token" in cd


def test_eval_baseline_workflow_is_manual_and_uploads_safe_artifacts() -> None:
    workflow = (WORKFLOWS / "eval-baseline.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "uv tool install google-agents-cli" in workflow
    assert "scripts/run_agent_evals.py preflight --json" in workflow
    assert "scripts/run_agent_evals.py run" in workflow
    assert "scripts/run_agent_evals.py triage --json" in workflow
    assert "actions/upload-artifact" in workflow
    assert "portfolio-agentic-eval-artifacts-${{ github.sha }}" in workflow
    assert "GOOGLE_API_KEY" in workflow
    assert "ANTHROPIC_API_KEY" in workflow
    assert "OPENAI_API_KEY" in workflow
    assert "broker" not in workflow.lower()
    assert "fyers" not in workflow.lower()
