from __future__ import annotations

from typing import Any

from portfolio_domain import (
    draft_strategy,
    get_demo_portfolio_summary,
    get_demo_risk_review,
    run_demo_momentum_screener,
)
from portfolio_policy import ActionTier, authorize_tool_call, redact_sensitive

EXPOSED_TOOL_NAMES = {
    "get_portfolio_summary",
    "run_momentum_screener",
    "get_risk_review",
    "draft_paper_strategy",
    "create_paper_trade_proposal",
}


def _policy_payload(tool_name: str) -> dict[str, Any]:
    return authorize_tool_call(tool_name).to_dict()


def _blocked(tool_name: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "blocked",
        "policy": _policy_payload(tool_name),
        "details": redact_sensitive(details or {}),
    }


def get_portfolio_summary() -> dict[str, Any]:
    """Return a synthetic portfolio summary for paper-trading analysis."""
    tool_name = "get_portfolio_summary"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "portfolio": get_demo_portfolio_summary().to_dict(),
    }


def run_momentum_screener(limit: int) -> dict[str, Any]:
    """Run a synthetic momentum screener over demo symbols."""
    tool_name = "run_momentum_screener"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "candidates": [
            candidate.to_dict() for candidate in run_demo_momentum_screener(limit)
        ],
    }


def get_risk_review() -> dict[str, Any]:
    """Return current demo risk state and paper-trading safety switches."""
    tool_name = "get_risk_review"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "risk_review": get_demo_risk_review().to_dict(),
    }


def draft_paper_strategy(symbol: str, rationale: str) -> dict[str, Any]:
    """Draft a paper-trading strategy without executing any trade."""
    tool_name = "draft_paper_strategy"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "strategy": draft_strategy(symbol, rationale).to_dict(),
    }


def create_paper_trade_proposal(strategy_id: str) -> dict[str, Any]:
    """Create a pending paper-trade proposal that requires human approval."""
    tool_name = "create_paper_trade_proposal"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "pending_approval",
        "policy": decision.to_dict(),
        "proposal": {
            "proposal_id": f"proposal-{strategy_id}",
            "strategy_id": strategy_id,
            "mode": "paper",
            "next_step": "human_approval_required",
        },
    }


def place_live_order(symbol: str, quantity: int, side: str) -> dict[str, Any]:
    """Blocked compatibility trap for forbidden live-order requests."""
    return _blocked(
        "place_live_order",
        {"symbol": symbol, "quantity": quantity, "side": side},
    )


def get_broker_trading_token(provider: str) -> dict[str, Any]:
    """Blocked compatibility trap for broker trading-token requests."""
    return _blocked(
        "get_broker_trading_token",
        {"provider": provider, "broker_token": "never-return-this"},
    )


def assert_exposed_tools_are_safe() -> None:
    for tool_name in EXPOSED_TOOL_NAMES:
        decision = authorize_tool_call(tool_name)
        if decision.tier == ActionTier.FORBIDDEN or not decision.allowed:
            raise AssertionError(f"Unsafe exposed tool: {tool_name}")

