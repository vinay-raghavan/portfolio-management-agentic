from __future__ import annotations

import pytest

from portfolio_domain.paper_ledger import SQLitePaperLedgerStore
from portfolio_mcp.tools import (
    approve_paper_order_simulation,
    create_paper_order_proposal,
    get_audit_events,
    get_paper_portfolio_accounting,
    list_paper_fills,
    list_paper_orders,
    list_paper_positions,
    simulate_approved_paper_fill,
)


def test_sqlite_store_rejects_simulated_fill_before_approval(tmp_path) -> None:
    store = SQLitePaperLedgerStore(tmp_path / "paper-ledger.db")
    order, _, _ = store.create_order_proposal(
        strategy_id="strategy-fill-before-approval",
        symbol="TATAMOTORS",
        side="buy",
        quantity=4,
    )

    with pytest.raises(ValueError, match="approval"):
        store.simulate_approved_fill(order.order_id, fill_price=975.25)


def test_sqlite_store_approval_fill_and_accounting_survive_reload(tmp_path) -> None:
    db_path = tmp_path / "paper-ledger.db"
    store = SQLitePaperLedgerStore(db_path)
    order, _, _ = store.create_order_proposal(
        strategy_id="strategy-persistent-fill",
        symbol="TATAMOTORS",
        side="buy",
        quantity=7,
        order_type="limit",
        requested_price=970.25,
    )

    approved_order, approval, _ = store.approve_order_simulation(
        order.order_id,
        approved_by="human-review",
        approval_note="Fixture approval for contract test.",
    )
    fill, filled_order, position, _ = store.simulate_approved_fill(
        approved_order.order_id,
        fill_price=970.25,
    )

    reloaded = SQLitePaperLedgerStore(db_path)
    reloaded_order = reloaded.list_orders()[0]
    reloaded_position = next(
        item for item in reloaded.list_positions() if item.symbol == "TATAMOTORS"
    )
    accounting = reloaded.portfolio_accounting()
    audit_event_types = {event.event_type for event in reloaded.audit_events()}

    assert approval.status == "approved"
    assert filled_order.status == "filled"
    assert reloaded_order.status == "filled"
    assert reloaded_order.filled_quantity == 7
    assert reloaded_order.fill_ids == [fill.fill_id]
    assert position.quantity == 17
    assert reloaded_position.quantity == 17
    assert reloaded_position.average_price == 936.28
    assert reloaded_position.last_price == 970.25
    assert accounting.filled_orders == 1
    assert accounting.open_positions >= 2
    assert "paper_order_approved" in audit_event_types
    assert "paper_fill_simulated" in audit_event_types


def test_mcp_paper_fill_workflow_is_approval_gated_and_audited() -> None:
    proposal = create_paper_order_proposal(
        strategy_id="strategy-mcp-fill-workflow",
        symbol="TATAMOTORS",
        side="buy",
        quantity=2,
        order_type="market",
    )
    order_id = proposal["paper_order"]["order_id"]

    blocked_fill = simulate_approved_paper_fill(order_id, fill_price=980.0)
    approval = approve_paper_order_simulation(
        order_id,
        approved_by="human-review",
        approval_note="Approve paper simulation for MCP contract test.",
    )
    fill = simulate_approved_paper_fill(order_id, fill_price=980.0)
    fills = list_paper_fills()
    orders = list_paper_orders()
    positions = list_paper_positions()
    accounting = get_paper_portfolio_accounting()
    audit = get_audit_events()

    assert blocked_fill["status"] == "error"
    assert "approval" in blocked_fill["error"].lower()
    assert approval["status"] == "approved"
    assert approval["policy"]["tier"] == "approval_required"
    assert approval["approval_request"]["status"] == "approved"
    assert fill["status"] == "filled"
    assert fill["policy"]["tier"] == "approval_required"
    assert fill["paper_fill"]["mode"] == "paper"
    assert fill["paper_order"]["status"] == "filled"
    assert any(item["fill_id"] == fill["paper_fill"]["fill_id"] for item in fills["fills"])
    assert any(item["order_id"] == order_id and item["status"] == "filled" for item in orders["orders"])
    assert any(item["symbol"] == "TATAMOTORS" and item["quantity"] >= 12 for item in positions["positions"])
    assert accounting["accounting"]["filled_orders"] >= 1
    assert accounting["accounting"]["currency"] == "INR"
    assert {
        "paper_order_approved",
        "paper_fill_simulated",
    }.issubset({event["event_type"] for event in audit["audit_events"]})
