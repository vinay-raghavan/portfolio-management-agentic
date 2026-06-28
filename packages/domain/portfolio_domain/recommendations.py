from __future__ import annotations

from typing import Any

from .demo import get_demo_risk_review
from .models import (
    BacktestRequest,
    BacktestResult,
    GateResult,
    RecommendationExplanation,
)
from .paper_ledger import (
    get_fixture_backtest_result,
    get_fixture_paper_portfolio_accounting,
    list_fixture_backtest_requests,
    list_fixture_paper_fills,
    list_fixture_paper_orders,
    list_fixture_paper_positions,
    list_fixture_strategy_drafts,
)
from .product_data import build_factor_stack_explanation


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Symbol is required.")
    return normalized


def _normalize_setup(setup: str) -> str:
    normalized = setup.strip().lower()
    if not normalized:
        raise ValueError("Setup is required.")
    return normalized


def _factor_summary(
    sections: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for name, section in sections.items():
        summary[name] = {
            "score": section.get("score"),
            "weight": section.get("weight"),
            "evidence": list(section.get("evidence", [])),
            "counterevidence": list(section.get("counterevidence", [])),
            "citations": list(section.get("citations", [])),
        }
    return summary


def _weighted_confidence(factor_summary: dict[str, dict[str, Any]]) -> float:
    weighted = 0.0
    total_weight = 0.0
    for section in factor_summary.values():
        score = section.get("score")
        weight = section.get("weight")
        if isinstance(score, int | float) and isinstance(weight, int | float):
            weighted += score * weight
            total_weight += weight
    if not total_weight:
        return 0.0
    return round(weighted / total_weight, 2)


def _matching_backtests(
    symbol: str,
    setup: str,
) -> list[tuple[BacktestRequest, BacktestResult]]:
    matches: list[tuple[BacktestRequest, BacktestResult]] = []
    for request in list_fixture_backtest_requests():
        if request.symbol == symbol and request.setup == setup:
            matches.append((request, get_fixture_backtest_result(request.request_id)))
    return sorted(
        matches,
        key=lambda item: (
            item[0].end_date,
            item[0].start_date,
            item[0].request_id,
        ),
    )


def _backtest_summary(
    matches: list[tuple[BacktestRequest, BacktestResult]],
) -> dict[str, Any]:
    if not matches:
        return {
            "matched_request_count": 0,
            "latest_request_id": None,
            "metrics": {},
            "warnings": [],
            "generated_at": None,
        }
    latest_request, latest_result = matches[-1]
    return {
        "matched_request_count": len(matches),
        "latest_request_id": latest_request.request_id,
        "metrics": latest_result.metrics,
        "warnings": latest_result.warnings,
        "generated_at": latest_result.generated_at,
    }


def _ledger_context(symbol: str) -> dict[str, Any]:
    positions = [
        position
        for position in list_fixture_paper_positions()
        if position.symbol == symbol
    ]
    orders = [order for order in list_fixture_paper_orders() if order.symbol == symbol]
    fills = [fill for fill in list_fixture_paper_fills() if fill.symbol == symbol]
    accounting = get_fixture_paper_portfolio_accounting()
    return {
        "positions": [position.to_dict() for position in positions],
        "orders": [order.to_dict() for order in orders],
        "fills": [fill.to_dict() for fill in fills],
        "accounting": {
            "currency": accounting.currency,
            "total_market_value": accounting.total_market_value,
            "total_unrealized_pnl": accounting.total_unrealized_pnl,
            "open_positions": accounting.open_positions,
            "pending_orders": accounting.pending_orders,
            "approved_orders": accounting.approved_orders,
            "filled_orders": accounting.filled_orders,
            "simulated_fills": accounting.simulated_fills,
        },
    }


def _risk_gates(
    *,
    has_strategy_history: bool,
    has_backtest_history: bool,
    has_open_position: bool,
    provider_import_reconciliation_gate: GateResult,
) -> list[GateResult]:
    risk_review = get_demo_risk_review()
    return [
        GateResult(
            "live_trading_disabled",
            "pass"
            if risk_review.safety_switches.get("live_trading") == "disabled"
            else "fail",
            "Live trading must remain disabled for recommendation explanations.",
        ),
        GateResult(
            "broker_token_access_forbidden",
            "pass"
            if risk_review.safety_switches.get("broker_token_access") == "forbidden"
            else "fail",
            "Broker trading-token access must stay forbidden.",
        ),
        GateResult(
            "strategy_history",
            "pass" if has_strategy_history else "review",
            "A persisted paper strategy draft exists."
            if has_strategy_history
            else "No persisted paper strategy draft exists for this symbol.",
        ),
        GateResult(
            "backtest_history",
            "pass" if has_backtest_history else "review",
            "A persisted simulated backtest exists for this symbol and setup."
            if has_backtest_history
            else "No persisted simulated backtest exists for this symbol and setup.",
        ),
        GateResult(
            "open_position_review",
            "review" if has_open_position else "pass",
            "Existing paper position should be reviewed before any new paper proposal."
            if has_open_position
            else "No existing paper position found for this symbol.",
        ),
        provider_import_reconciliation_gate,
    ]


def _collect_section_text(
    factor_summary: dict[str, dict[str, Any]],
    key: str,
) -> list[str]:
    values: list[str] = []
    for section in factor_summary.values():
        values.extend(str(item) for item in section.get(key, []))
    return values


def _stance(
    *,
    has_strategy_history: bool,
    has_backtest_history: bool,
    latest_backtest_metrics: dict[str, Any],
    risk_gates: list[GateResult],
) -> str:
    if any(gate.status == "fail" for gate in risk_gates):
        return "blocked"
    if not has_strategy_history or not has_backtest_history:
        return "needs_review"
    total_return = latest_backtest_metrics.get("total_return_pct", 0)
    win_rate = latest_backtest_metrics.get("win_rate_pct", 0)
    if isinstance(total_return, int | float) and isinstance(win_rate, int | float):
        if total_return > 0 and win_rate >= 50:
            return "paper_draft_candidate"
    return "watch"


def _next_allowed_actions(
    *,
    stance: str,
    has_strategy_history: bool,
    has_backtest_history: bool,
) -> list[str]:
    actions = ["explain_factor_stack", "get_risk_review"]
    if not has_strategy_history:
        actions.append("draft_paper_strategy")
    if not has_backtest_history:
        actions.append("create_backtest_request")
    if stance == "paper_draft_candidate":
        actions.append("create_paper_order_proposal")
    actions.extend(["list_paper_orders", "get_paper_portfolio_accounting"])
    return actions


def _provider_import_reconciliation_gate(
    missing_data: list[str],
    factor_summary: dict[str, dict[str, Any]],
) -> GateResult:
    markers = [
        item
        for item in missing_data
        if "_import_" in item and "configured_" in item
    ]
    if any(
        marker.endswith("_import_source_changed")
        or marker.endswith("_import_store_mismatch")
        or marker.endswith("_import_needs_attention")
        for marker in markers
    ):
        return GateResult(
            "provider_import_reconciliation",
            "fail",
            "Configured provider import reconciliation is not safe for paper-order readiness.",
        )
    if any(marker.endswith("_import_pending_refresh") for marker in markers):
        return GateResult(
            "provider_import_reconciliation",
            "review",
            "Configured provider imports need refresh before paper-order readiness.",
        )
    if "provider_import_reconciliation" in factor_summary:
        return GateResult(
            "provider_import_reconciliation",
            "pass",
            "Configured provider imports are reconciled with structured storage.",
        )
    return GateResult(
        "provider_import_reconciliation",
        "pass",
        "No configured provider import reconciliation issues are active.",
    )


def _actions_after_provider_import_gate(
    actions: list[str],
    provider_import_gate: GateResult,
) -> list[str]:
    if provider_import_gate.status == "pass":
        return actions
    blocked_actions = {"create_paper_order_proposal"}
    if provider_import_gate.status == "fail":
        blocked_actions.update({"create_backtest_request", "draft_paper_strategy"})
    return [action for action in actions if action not in blocked_actions]


def build_recommendation_explanation(
    symbol: str,
    setup: str,
) -> RecommendationExplanation:
    normalized_symbol = _normalize_symbol(symbol)
    normalized_setup = _normalize_setup(setup)
    factor_stack = build_factor_stack_explanation(normalized_symbol, normalized_setup)
    factor_summary = _factor_summary(factor_stack.sections)

    strategy_matches = [
        strategy
        for strategy in list_fixture_strategy_drafts()
        if strategy.symbol == normalized_symbol
    ]
    backtest_matches = _matching_backtests(normalized_symbol, factor_stack.setup)
    backtest_summary = _backtest_summary(backtest_matches)
    ledger_context = _ledger_context(normalized_symbol)

    has_strategy_history = bool(strategy_matches)
    has_backtest_history = bool(backtest_matches)
    has_open_position = bool(ledger_context["positions"])
    provider_import_gate = _provider_import_reconciliation_gate(
        list(factor_stack.missing_data),
        factor_summary,
    )
    risk_gates = _risk_gates(
        has_strategy_history=has_strategy_history,
        has_backtest_history=has_backtest_history,
        has_open_position=has_open_position,
        provider_import_reconciliation_gate=provider_import_gate,
    )
    stance = _stance(
        has_strategy_history=has_strategy_history,
        has_backtest_history=has_backtest_history,
        latest_backtest_metrics=backtest_summary["metrics"],
        risk_gates=risk_gates,
    )

    evidence = _collect_section_text(factor_summary, "evidence")
    counterevidence = _collect_section_text(factor_summary, "counterevidence")
    missing_data = list(factor_stack.missing_data)
    if has_strategy_history:
        evidence.append(
            "Persisted paper strategy draft history exists for this symbol."
        )
    else:
        counterevidence.append(
            "No persisted paper strategy draft exists for this symbol."
        )
        missing_data.append("strategy_draft_history")
    if has_backtest_history:
        metrics = backtest_summary["metrics"]
        evidence.append(
            "Latest simulated backtest returned "
            f"{metrics.get('total_return_pct')} percent total return "
            f"with {metrics.get('win_rate_pct')} percent win rate."
        )
    else:
        counterevidence.append(
            "No persisted simulated backtest exists for this symbol and setup."
        )
        missing_data.append("backtest_request_history")
    if has_open_position:
        counterevidence.append(
            "Existing paper position requires exposure review before increasing size."
        )

    confidence = _weighted_confidence(factor_summary)
    if not has_strategy_history:
        confidence = round(max(0.0, confidence - 0.15), 2)
    if not has_backtest_history:
        confidence = round(max(0.0, confidence - 0.15), 2)
    if has_open_position:
        confidence = round(max(0.0, confidence - 0.05), 2)
    if provider_import_gate.status == "fail":
        confidence = round(max(0.0, confidence - 0.25), 2)
    elif provider_import_gate.status == "review":
        confidence = round(max(0.0, confidence - 0.10), 2)

    return RecommendationExplanation(
        symbol=normalized_symbol,
        setup=factor_stack.setup,
        mode="analysis_only",
        stance=stance,
        confidence=confidence,
        evidence=evidence,
        counterevidence=counterevidence,
        risk_gates=risk_gates,
        missing_data=sorted(set(missing_data)),
        factor_summary=factor_summary,
        history_refs={
            "strategy_ids": [strategy.strategy_id for strategy in strategy_matches],
            "backtest_request_ids": [
                request.request_id for request, _ in backtest_matches
            ],
            "paper_order_ids": [
                order["order_id"] for order in ledger_context["orders"]
            ],
            "paper_fill_ids": [fill["fill_id"] for fill in ledger_context["fills"]],
            "paper_position_symbols": [
                position["symbol"] for position in ledger_context["positions"]
            ],
        },
        backtest_summary=backtest_summary,
        ledger_context=ledger_context,
        citations=factor_stack.citations,
        next_allowed_actions=_actions_after_provider_import_gate(
            _next_allowed_actions(
                stance=stance,
                has_strategy_history=has_strategy_history,
                has_backtest_history=has_backtest_history,
            ),
            provider_import_gate,
        ),
        notes=[
            "Recommendation explanation is read-only analysis.",
            "Paper proposals remain draft-only and simulated fills require human approval.",
            "Live trading and broker trading-token access remain forbidden.",
        ],
    )
