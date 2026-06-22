from __future__ import annotations

from typing import Any

from portfolio_domain import (
    build_factor_stack_explanation,
    build_strategy_evidence_pack,
    create_demo_pre_market_briefing,
    create_fixture_backtest_request,
    create_fixture_paper_order_proposal,
    draft_strategy,
    get_fixture_backtest_result,
    get_data_provider_registry,
    get_pattern_card,
    get_demo_portfolio_summary,
    get_demo_research_digest,
    get_demo_risk_review,
    get_demo_signal_summary,
    get_demo_watchlist_snapshot,
    list_fixture_approval_queue,
    list_fixture_audit_events,
    list_fixture_paper_orders,
    list_fixture_paper_positions,
    list_fixture_universes,
    run_fixture_screener,
    run_demo_momentum_screener,
    search_pattern_cards,
)
from portfolio_policy import ActionTier, authorize_tool_call, redact_sensitive

EXPOSED_TOOL_NAMES = {
    "get_portfolio_summary",
    "get_watchlist_snapshot",
    "get_signal_summary",
    "get_research_digest",
    "create_pre_market_briefing",
    "run_momentum_screener",
    "list_data_providers",
    "get_data_provider_health",
    "get_market_data_snapshot",
    "get_universe_members",
    "list_universes",
    "run_screener",
    "explain_candidate_evidence",
    "search_pattern_library",
    "get_pattern_playbook",
    "cite_strategy_evidence",
    "explain_factor_stack",
    "create_backtest_request",
    "get_backtest_result",
    "list_paper_orders",
    "list_paper_positions",
    "create_paper_order_proposal",
    "get_approval_queue",
    "get_audit_events",
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


def get_watchlist_snapshot() -> dict[str, Any]:
    """Return synthetic pre-market watchlist context."""
    tool_name = "get_watchlist_snapshot"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "watchlist": get_demo_watchlist_snapshot().to_dict(),
    }


def get_signal_summary() -> dict[str, Any]:
    """Return synthetic market setup and signal context."""
    tool_name = "get_signal_summary"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "signal_summary": get_demo_signal_summary().to_dict(),
    }


def get_research_digest() -> dict[str, Any]:
    """Return synthetic research and pattern notes for pre-market review."""
    tool_name = "get_research_digest"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "research_digest": get_demo_research_digest().to_dict(),
    }


def create_pre_market_briefing() -> dict[str, Any]:
    """Compose a read-only synthetic pre-market briefing."""
    tool_name = "create_pre_market_briefing"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "briefing": create_demo_pre_market_briefing().to_dict(),
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


def list_data_providers() -> dict[str, Any]:
    """Return read-only provider catalog and configuration state."""
    tool_name = "list_data_providers"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    registry = get_data_provider_registry()
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "providers": [
            descriptor.to_dict() for descriptor in registry.descriptors()
        ],
    }


def get_data_provider_health() -> dict[str, Any]:
    """Return provider health without exposing credential values."""
    tool_name = "get_data_provider_health"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    registry = get_data_provider_registry()
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "health": [item.to_dict() for item in registry.health()],
    }


def get_market_data_snapshot(symbol: str) -> dict[str, Any]:
    """Return fixture-backed market data snapshot for one symbol."""
    tool_name = "get_market_data_snapshot"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        snapshot = get_data_provider_registry().market_data.get_snapshot(symbol)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "snapshot": snapshot.to_dict(),
    }


def get_universe_members(universe_id: str) -> dict[str, Any]:
    """Return fixture-backed universe members through the provider boundary."""
    tool_name = "get_universe_members"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        universe = get_data_provider_registry().universe.get_members(universe_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "universe": universe.to_dict(),
    }


def list_universes() -> dict[str, Any]:
    """Return fixture-backed universes with source metadata."""
    tool_name = "list_universes"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "universes": [universe.to_dict() for universe in list_fixture_universes()],
    }


def run_screener(
    universe_id: str = "fixture_nifty50",
    preset: str = "momentum",
    limit: int = 10,
) -> dict[str, Any]:
    """Run a deterministic read-only screener over fixture data."""
    tool_name = "run_screener"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        screener_run = run_fixture_screener(universe_id, preset, limit)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "screener_run": screener_run.to_dict(),
    }


def explain_candidate_evidence(
    symbol: str,
    setup: str = "",
) -> dict[str, Any]:
    """Explain deterministic fixture evidence for a screener candidate."""
    tool_name = "explain_candidate_evidence"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        factor_stack = build_factor_stack_explanation(symbol, setup or None)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "factor_stack": factor_stack.to_dict(),
    }


def search_pattern_library(
    query: str,
    tags: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    """Search public-safe pattern cards and playbooks."""
    tool_name = "search_pattern_library"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    tag_values = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "patterns": [
            pattern.to_dict()
            for pattern in search_pattern_cards(query, tag_values, limit)
        ],
    }


def get_pattern_playbook(pattern_id: str) -> dict[str, Any]:
    """Retrieve one versioned public-safe pattern card."""
    tool_name = "get_pattern_playbook"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        pattern = get_pattern_card(pattern_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "pattern": pattern.to_dict(),
    }


def cite_strategy_evidence(symbol: str, setup: str) -> dict[str, Any]:
    """Return citation-backed evidence for a paper-strategy explanation."""
    tool_name = "cite_strategy_evidence"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        evidence_pack = build_strategy_evidence_pack(symbol, setup)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
    }


def explain_factor_stack(symbol: str, setup: str = "") -> dict[str, Any]:
    """Compose deterministic factors, citations, and paper-only next actions."""
    tool_name = "explain_factor_stack"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        factor_stack = build_factor_stack_explanation(symbol, setup or None)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "factor_stack": factor_stack.to_dict(),
    }


def create_backtest_request(
    symbol: str,
    setup: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Draft an offline paper backtest request without running live systems."""
    tool_name = "create_backtest_request"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        request = create_fixture_backtest_request(
            symbol,
            setup,
            start_date,
            end_date,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "backtest_request": request.to_dict(),
    }


def get_backtest_result(request_id: str) -> dict[str, Any]:
    """Return the deterministic simulated result for a draft backtest request."""
    tool_name = "get_backtest_result"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        result = get_fixture_backtest_result(request_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "backtest_result": result.to_dict(),
    }


def list_paper_orders() -> dict[str, Any]:
    """Return paper order proposals without executing or filling them."""
    tool_name = "list_paper_orders"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "orders": [order.to_dict() for order in list_fixture_paper_orders()],
    }


def list_paper_positions() -> dict[str, Any]:
    """Return fixture paper positions for analysis and exposure review."""
    tool_name = "list_paper_positions"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "positions": [
            position.to_dict() for position in list_fixture_paper_positions()
        ],
    }


def create_paper_order_proposal(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    requested_price: float | None = None,
) -> dict[str, Any]:
    """Create a pending paper order proposal without a fill or live order."""
    tool_name = "create_paper_order_proposal"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        order, approval, audit_event = create_fixture_paper_order_proposal(
            strategy_id,
            symbol,
            side,
            quantity,
            order_type,
            requested_price,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "pending_approval",
        "policy": decision.to_dict(),
        "paper_order": order.to_dict(),
        "approval_request": approval.to_dict(),
        "audit_event": audit_event.to_dict(),
        "next_step": "human_approval_required",
    }


def get_approval_queue() -> dict[str, Any]:
    """Return pending human approvals for paper-only actions."""
    tool_name = "get_approval_queue"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "approval_requests": [
            approval.to_dict() for approval in list_fixture_approval_queue()
        ],
    }


def get_audit_events() -> dict[str, Any]:
    """Return redacted paper-ledger audit events."""
    tool_name = "get_audit_events"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "audit_events": [
            event.to_dict() for event in list_fixture_audit_events()
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
