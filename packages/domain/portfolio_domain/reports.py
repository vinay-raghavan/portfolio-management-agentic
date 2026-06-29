from __future__ import annotations

import re
from typing import Any

from .demo import get_demo_risk_review
from .models import PaperAuditExport, PaperTradingReport
from .paper_ledger import (
    FIXTURE_TIMESTAMP,
    OFFLINE_SOURCE,
    get_fixture_paper_portfolio_accounting,
    list_fixture_approval_queue,
    list_fixture_audit_events,
    list_fixture_paper_fills,
    list_fixture_paper_orders,
    list_fixture_paper_positions,
)
from .recommendations import build_recommendation_explanation

SENSITIVE_MARKERS = ("token", "secret", "password", "credential")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "portfolio"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if any(marker in key.lower() for marker in SENSITIVE_MARKERS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _audit_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in list_fixture_audit_events():
        rows.append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "message": event.message,
                "created_at": event.created_at,
                "actor": event.actor,
                "redacted_payload": _redact(event.redacted_payload),
            }
        )
    return rows


def _audit_export(scope_slug: str) -> PaperAuditExport:
    rows = _audit_rows()
    return PaperAuditExport(
        schema_version="paper-audit-export/v1",
        export_id=f"paper-audit-export-{scope_slug}",
        mode="read_only",
        source=OFFLINE_SOURCE,
        generated_at=FIXTURE_TIMESTAMP,
        row_count=len(rows),
        rows=rows,
        redaction_status="redacted",
        notes=[
            "Audit export is returned as JSON-ready data and does not write a file.",
            "Sensitive payload keys are redacted before export.",
            "Live trading and broker trading-token access remain forbidden.",
        ],
    )


def _gate_by_name(preflight: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in preflight.get("risk_gates", []):
        if gate.get("name") == name:
            return dict(gate)
    return {"name": name, "status": "unknown", "reason": "Gate was not recorded."}


def _readiness_projection(order: dict[str, Any]) -> dict[str, Any] | None:
    preflight = order.get("readiness_preflight")
    if not isinstance(preflight, dict) or not preflight:
        return None
    submitted_strategy_gate = preflight.get("submitted_strategy_gate")
    if not isinstance(submitted_strategy_gate, dict):
        submitted_strategy_gate = _gate_by_name(preflight, "submitted_strategy")
    return {
        "order_id": order.get("order_id"),
        "strategy_id": order.get("strategy_id"),
        "symbol": order.get("symbol"),
        "status": preflight.get("status", "unknown"),
        "required_approval": preflight.get("required_approval", "human"),
        "setup": preflight.get("setup"),
        "provider_import_reconciliation": preflight.get(
            "provider_import_reconciliation",
            {},
        ),
        "provider_refresh_readiness": preflight.get(
            "provider_refresh_readiness",
            {},
        ),
        "submitted_strategy_gate": submitted_strategy_gate,
        "paper_only_policy": preflight.get("paper_only_policy", {}),
        "blocking_reasons": list(preflight.get("blocking_reasons", [])),
    }


def _paper_order_readiness(orders: list[dict[str, Any]]) -> dict[str, Any]:
    preflights = [
        projection
        for order in orders
        if (projection := _readiness_projection(order)) is not None
    ]
    latest_preflight = None
    for item in reversed(preflights):
        if item["submitted_strategy_gate"].get("status") != "unknown":
            latest_preflight = item
            break
    if latest_preflight is None and preflights:
        latest_preflight = preflights[-1]
    return {
        "schema_version": "paper-order-readiness-report/v1",
        "preflight_count": len(preflights),
        "ready_for_approval_count": sum(
            1 for item in preflights if item["status"] == "ready_for_approval"
        ),
        "blocked_count": sum(1 for item in preflights if item["status"] == "blocked"),
        "latest_preflight": latest_preflight,
        "preflights": preflights,
        "notes": [
            "Readiness preflight is captured before paper order approval.",
            "Blocked preflights do not create paper orders.",
            "Human approval remains required before simulated fills.",
        ],
    }


def build_paper_trading_report(
    symbol: str = "",
    setup: str = "",
) -> PaperTradingReport:
    normalized_symbol = symbol.strip().upper()
    normalized_setup = setup.strip().lower()
    if bool(normalized_symbol) != bool(normalized_setup):
        raise ValueError(
            "Both symbol and setup are required for a symbol-scoped report."
        )

    positions = [position.to_dict() for position in list_fixture_paper_positions()]
    orders = [order.to_dict() for order in list_fixture_paper_orders()]
    fills = [fill.to_dict() for fill in list_fixture_paper_fills()]
    pending_approvals = [
        approval.to_dict() for approval in list_fixture_approval_queue()
    ]
    accounting = get_fixture_paper_portfolio_accounting().to_dict()
    risk_review = get_demo_risk_review().to_dict()
    recommendation = (
        build_recommendation_explanation(normalized_symbol, normalized_setup)
        if normalized_symbol
        else None
    )

    scope = "symbol" if normalized_symbol else "portfolio"
    scope_slug = (
        f"{_slug(normalized_symbol)}-{_slug(normalized_setup)}"
        if normalized_symbol
        else "portfolio"
    )
    audit_export = _audit_export(scope_slug)
    paper_order_readiness = _paper_order_readiness(orders)
    summary = {
        "position_count": len(positions),
        "order_count": len(orders),
        "fill_count": len(fills),
        "pending_approval_count": len(pending_approvals),
        "readiness_preflight_count": paper_order_readiness["preflight_count"],
        "ready_readiness_preflight_count": paper_order_readiness[
            "ready_for_approval_count"
        ],
        "blocked_readiness_preflight_count": paper_order_readiness[
            "blocked_count"
        ],
        "audit_event_count": audit_export.row_count,
        "open_positions": accounting["open_positions"],
        "pending_orders": accounting["pending_orders"],
        "approved_orders": accounting["approved_orders"],
        "filled_orders": accounting["filled_orders"],
        "simulated_fills": accounting["simulated_fills"],
        "total_market_value": accounting["total_market_value"],
        "total_unrealized_pnl": accounting["total_unrealized_pnl"],
    }
    sections = {
        "paper_accounting": accounting,
        "positions": positions,
        "orders": orders,
        "fills": fills,
        "pending_approvals": pending_approvals,
        "paper_order_readiness": paper_order_readiness,
        "risk_review": risk_review,
    }
    next_allowed_actions = [
        "get_recommendation_explanation",
        "list_paper_orders",
        "list_paper_positions",
        "list_paper_fills",
        "get_paper_portfolio_accounting",
        "get_audit_events",
    ]
    if pending_approvals:
        next_allowed_actions.append("approve_paper_order_simulation")

    return PaperTradingReport(
        report_id=f"paper-trading-report-{scope_slug}",
        report_type="paper_trading_review",
        scope=scope,
        mode="read_only",
        source=OFFLINE_SOURCE,
        generated_at=FIXTURE_TIMESTAMP,
        summary=summary,
        sections=sections,
        recommendation=recommendation,
        audit_export=audit_export,
        next_allowed_actions=next_allowed_actions,
        notes=[
            "Report generation is read-only and returns structured data only.",
            "Paper proposals remain draft-only and simulated fills require human approval.",
            "No broker API, live order, or trading credential is used.",
        ],
    )
