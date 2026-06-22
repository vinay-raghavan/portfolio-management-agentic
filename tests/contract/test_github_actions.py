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
    assert "docker compose build agent-service mcp-server web" in ci
    assert "docker compose up -d agent-service mcp-server web" in ci
    assert "http://127.0.0.1:3000" in ci
    assert "streamable_http_client" in ci
    assert "create_pre_market_briefing" in ci
    assert "get_recommendation_explanation" in ci
    assert "generate_paper_trading_report" in ci
    assert "list_strategy_drafts" in ci
    assert "list_backtest_requests" in ci
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
    assert "packages: write" in cd
    assert "docker/build-push-action" in cd
    assert "portfolio-management-agentic-agent-service" in cd
    assert "portfolio-management-agentic-mcp-server" in cd
    assert "portfolio-management-agentic-web" in cd
    assert "fyers" not in cd.lower()
    assert "broker-token" in cd
