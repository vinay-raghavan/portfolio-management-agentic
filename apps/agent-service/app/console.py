from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
for relative_path in (
    "packages/policy",
    "packages/domain",
    "apps/mcp-server",
):
    package_path = str(REPO_ROOT / relative_path)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from portfolio_mcp.tools import (  # noqa: E402
    approve_paper_order_simulation,
    cite_strategy_evidence,
    create_backtest_request,
    create_paper_order_proposal,
    create_pre_market_briefing,
    draft_paper_strategy,
    explain_factor_stack,
    generate_paper_trading_report,
    get_approval_queue,
    get_audit_events,
    get_backtest_result,
    get_data_provider_health,
    get_paper_portfolio_accounting,
    get_recommendation_explanation,
    get_risk_review,
    list_backtest_requests,
    list_data_providers,
    list_paper_fills,
    list_paper_orders,
    list_paper_positions,
    list_strategy_drafts,
    list_universes,
    run_screener,
    search_pattern_library,
    simulate_approved_paper_fill,
)
from portfolio_policy import authorize_tool_call  # noqa: E402

DEFAULT_SYMBOL = "TATAMOTORS"
DEFAULT_SETUP = "breakout-continuation"
DEFAULT_UNIVERSE_ID = "fixture_nifty50"
DEFAULT_SCREENER_PRESET = "momentum"
DEFAULT_BACKTEST_START = "2026-01-02"
DEFAULT_BACKTEST_END = "2026-06-22"


def _safety_payload() -> dict[str, str]:
    return {
        "live_trading": "blocked",
        "broker_trading_tokens": "forbidden",
        "simulated_fills": "approval_required",
    }


def _action_policy(tool_name: str) -> dict[str, Any]:
    return authorize_tool_call(tool_name).to_dict()


def _page(
    page_id: str,
    label: str,
    primary_tool: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "id": page_id,
        "label": label,
        "primary_tool": primary_tool,
        "tier": _action_policy(primary_tool)["tier"],
        "summary": summary,
    }


def _workflow_actions() -> list[dict[str, str]]:
    return [
        {
            "label": "Run pre-market briefing",
            "tool": "create_pre_market_briefing",
            "tier": "read_only",
        },
        {
            "label": "Review approval queue",
            "tool": "get_approval_queue",
            "tier": "read_only",
        },
        {
            "label": "Generate paper report",
            "tool": "generate_paper_trading_report",
            "tier": "read_only",
        },
    ]


def _primary_candidate(screener_payload: dict[str, Any]) -> tuple[str, str]:
    candidates = screener_payload.get("screener_run", {}).get("candidates", [])
    if not candidates:
        return DEFAULT_SYMBOL, DEFAULT_SETUP
    candidate = candidates[0]
    return (
        str(candidate.get("symbol") or DEFAULT_SYMBOL),
        str(candidate.get("setup") or DEFAULT_SETUP),
    )


def _latest_backtest_result(backtests_payload: dict[str, Any]) -> dict[str, Any]:
    requests = backtests_payload.get("backtest_requests", [])
    if not requests:
        return {
            "status": "empty",
            "message": "No backtest requests have been drafted yet.",
        }
    latest_request = requests[-1]
    return get_backtest_result(str(latest_request["request_id"]))


def build_console_workflows(
    universe_id: str = DEFAULT_UNIVERSE_ID,
    preset: str = DEFAULT_SCREENER_PRESET,
    limit: int = 5,
) -> dict[str, Any]:
    """Build focused workflow page payloads from policy-controlled tools."""
    bounded_limit = max(1, min(limit, 20))
    screener_run = run_screener(
        universe_id=universe_id,
        preset=preset,
        limit=bounded_limit,
    )
    symbol, setup = _primary_candidate(screener_run)
    strategy_drafts = list_strategy_drafts()
    backtest_requests = list_backtest_requests()
    orders = list_paper_orders()
    positions = list_paper_positions()
    fills = list_paper_fills()
    accounting = get_paper_portfolio_accounting()
    approvals = get_approval_queue()
    audit = get_audit_events()
    report = generate_paper_trading_report(symbol, setup)

    return {
        "mode": "paper_only",
        "safety": _safety_payload(),
        "pages": [
            _page(
                "dashboard",
                "Dashboard",
                "create_pre_market_briefing",
                "Overview of briefing, screener, ledger, risk, and reports.",
            ),
            _page(
                "screener",
                "Screener",
                "run_screener",
                "Run deterministic screeners and inspect factor evidence.",
            ),
            _page(
                "strategy-backtest",
                "Strategies & Backtests",
                "draft_paper_strategy",
                "Draft paper strategies and simulated backtest requests.",
            ),
            _page(
                "paper-approvals",
                "Paper Approvals",
                "approve_paper_order_simulation",
                "Approve and simulate paper fills through human-gated actions.",
            ),
            _page(
                "reports",
                "Reports",
                "generate_paper_trading_report",
                "Read paper trading reports and redacted audit exports.",
            ),
            _page(
                "settings",
                "Provider settings",
                "get_data_provider_health",
                "Review fixture and configured provider health without credential values.",
            ),
        ],
        "workflow_actions": _workflow_actions(),
        "screener": {
            "selected_universe": universe_id,
            "selected_preset": preset,
            "universes": list_universes(),
            "run": screener_run,
            "factor_stack": explain_factor_stack(symbol, setup),
            "patterns": search_pattern_library(setup, tags=preset, limit=4),
            "allowed_actions": [
                "explain_factor_stack",
                "draft_paper_strategy",
                "create_backtest_request",
            ],
        },
        "strategy_backtest": {
            "symbol": symbol,
            "setup": setup,
            "recommendation": get_recommendation_explanation(symbol, setup),
            "evidence": cite_strategy_evidence(symbol, setup),
            "strategy_drafts": strategy_drafts,
            "backtest_requests": backtest_requests,
            "latest_backtest": _latest_backtest_result(backtest_requests),
            "actions": {
                "draft_strategy": _action_policy("draft_paper_strategy"),
                "create_backtest": _action_policy("create_backtest_request"),
                "create_paper_order": _action_policy("create_paper_order_proposal"),
            },
            "defaults": {
                "symbol": symbol,
                "setup": setup,
                "start_date": DEFAULT_BACKTEST_START,
                "end_date": DEFAULT_BACKTEST_END,
            },
        },
        "paper_approvals": {
            "orders": orders,
            "positions": positions,
            "fills": fills,
            "accounting": accounting,
            "approvals": approvals,
            "audit": audit,
            "actions": {
                "approve_simulation": _action_policy("approve_paper_order_simulation"),
                "simulate_fill": _action_policy("simulate_approved_paper_fill"),
            },
        },
        "reports": {
            "report": report,
            "audit": audit,
            "actions": {
                "generate_report": _action_policy("generate_paper_trading_report"),
                "read_audit": _action_policy("get_audit_events"),
            },
        },
        "settings": {
            "providers": list_data_providers(),
            "health": get_data_provider_health(),
            "risk": get_risk_review(),
            "safety": _safety_payload(),
        },
    }


def draft_console_strategy(symbol: str, rationale: str) -> dict[str, Any]:
    action = draft_paper_strategy(symbol, rationale)
    return {"action": action, "state": build_console_workflows()}


def create_console_backtest(
    symbol: str,
    setup: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    action = create_backtest_request(symbol, setup, start_date, end_date)
    return {"action": action, "state": build_console_workflows(preset=DEFAULT_SCREENER_PRESET)}


def create_console_paper_order(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str,
    requested_price: float | None,
) -> dict[str, Any]:
    action = create_paper_order_proposal(
        strategy_id,
        symbol,
        side,
        quantity,
        order_type,
        requested_price,
    )
    return {"action": action, "state": build_console_workflows()}


def approve_console_paper_order(
    order_id: str,
    approved_by: str,
    approval_note: str = "",
) -> dict[str, Any]:
    action = approve_paper_order_simulation(order_id, approved_by, approval_note)
    return {"action": action, "state": build_console_workflows()}


def simulate_console_paper_fill(
    order_id: str,
    fill_price: float | None = None,
) -> dict[str, Any]:
    action = simulate_approved_paper_fill(order_id, fill_price)
    return {"action": action, "state": build_console_workflows()}


def build_console_overview() -> dict[str, Any]:
    """Build the first web-console payload from policy-controlled tools."""
    return {
        "mode": "paper_only",
        "safety": _safety_payload(),
        "workflow_actions": _workflow_actions(),
        "briefing": create_pre_market_briefing(),
        "providers": get_data_provider_health(),
        "screener": run_screener(
            universe_id="fixture_nifty50",
            preset="momentum",
            limit=5,
        ),
        "recommendation": get_recommendation_explanation(
            "TATAMOTORS",
            "breakout-continuation",
        ),
        "paper_ledger": {
            "orders": list_paper_orders(),
            "positions": list_paper_positions(),
            "fills": list_paper_fills(),
            "accounting": get_paper_portfolio_accounting(),
            "approvals": get_approval_queue(),
        },
        "risk": get_risk_review(),
        "report": generate_paper_trading_report(
            "TATAMOTORS",
            "breakout-continuation",
        ),
        "audit": get_audit_events(),
    }
