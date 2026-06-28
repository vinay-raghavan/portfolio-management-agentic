from portfolio_mcp.tools import (
    create_backtest_request,
    create_paper_order_proposal,
    draft_paper_strategy,
    get_approval_queue,
    get_audit_events,
    get_backtest_result,
    list_paper_orders,
    list_paper_positions,
)


def test_backtest_request_and_result_are_simulated_contracts() -> None:
    request = create_backtest_request(
        "TATAMOTORS",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )
    result = get_backtest_result(request["backtest_request"]["request_id"])

    assert request["status"] == "success"
    assert request["policy"]["tier"] == "draft_only"
    assert request["backtest_request"]["mode"] == "paper"
    assert request["backtest_request"]["status"] == "draft"
    assert request["backtest_request"]["source"] == "offline_fixture"
    assert "live trading is forbidden" in " ".join(
        request["backtest_request"]["notes"]
    ).lower()

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["backtest_result"]["mode"] == "paper"
    assert result["backtest_result"]["status"] == "simulated"
    assert result["backtest_result"]["source"] == "offline_fixture"
    assert result["backtest_result"]["metrics"]["trade_count"] >= 1
    assert "total_return_pct" in result["backtest_result"]["metrics"]
    assert "max_drawdown_pct" in result["backtest_result"]["metrics"]
    assert any(
        "not predictive" in warning.lower()
        for warning in result["backtest_result"]["warnings"]
    )


def test_paper_order_proposal_enters_approval_queue_without_fill() -> None:
    strategy = draft_paper_strategy(
        "TATAMOTORS",
        "Paper proposal requires recommendation readiness preflight.",
    )
    create_backtest_request(
        "TATAMOTORS",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )
    proposal = create_paper_order_proposal(
        strategy_id=strategy["strategy"]["strategy_id"],
        symbol="TATAMOTORS",
        side="buy",
        quantity=5,
        order_type="market",
    )
    orders = list_paper_orders()
    approvals = get_approval_queue()
    audit = get_audit_events()

    order = proposal["paper_order"]
    approval = proposal["approval_request"]
    preflight = proposal["readiness_preflight"]

    assert proposal["status"] == "pending_approval"
    assert proposal["policy"]["tier"] == "draft_only"
    assert preflight["schema_version"] == "paper-order-readiness-preflight/v1"
    assert preflight["status"] == "ready_for_approval"
    assert preflight["mode"] == "paper_only"
    assert preflight["required_approval"] == "human"
    assert preflight["recommendation"]["stance"] == "paper_draft_candidate"
    assert preflight["provider_import_reconciliation"]["status"] == "pass"
    assert preflight["provider_refresh_readiness"]["status"] == "pass"
    assert preflight["history"]["strategy_ids"] == [strategy["strategy"]["strategy_id"]]
    assert preflight["history"]["backtest_request_ids"]
    assert order["mode"] == "paper"
    assert order["status"] == "pending_approval"
    assert order["readiness_preflight"] == preflight
    assert order["approval_request_id"] == approval["approval_id"]
    assert order["filled_quantity"] == 0
    assert order["fill_ids"] == []
    assert any("preflight" in item.lower() for item in approval["risk_notes"])
    assert proposal["next_step"] == "human_approval_required"

    assert any(item["order_id"] == order["order_id"] for item in orders["orders"])
    persisted_order = next(
        item for item in orders["orders"] if item["order_id"] == order["order_id"]
    )
    assert persisted_order["readiness_preflight"]["status"] == "ready_for_approval"
    assert any(
        item["approval_id"] == approval["approval_id"]
        for item in approvals["approval_requests"]
    )
    audit_event = next(
        event
        for event in audit["audit_events"]
        if event["entity_id"] == order["order_id"]
        and event["event_type"] == "paper_order_proposed"
    )
    assert audit_event["redacted_payload"]["readiness_preflight"]["status"] == (
        "ready_for_approval"
    )
    assert audit_event["redacted_payload"]["readiness_preflight"][
        "required_approval"
    ] == "human"
    assert all(
        item["status"] != "filled"
        for item in orders["orders"]
        if item["order_id"] == order["order_id"]
    )


def test_paper_order_proposal_blocks_without_ready_preflight() -> None:
    result = create_paper_order_proposal(
        strategy_id="strategy-sunpharma-not-ready",
        symbol="SUNPHARMA",
        side="buy",
        quantity=2,
        order_type="market",
    )
    orders = list_paper_orders()

    assert result["status"] == "blocked"
    assert result["policy"]["tier"] == "draft_only"
    assert result["readiness_preflight"]["status"] == "blocked"
    assert result["readiness_preflight"]["required_approval"] == "human"
    assert "strategy_history" in {
        gate["name"] for gate in result["readiness_preflight"]["risk_gates"]
    }
    assert "paper_order" not in result
    assert not any(
        item["strategy_id"] == "strategy-sunpharma-not-ready"
        for item in orders["orders"]
    )


def test_paper_order_proposal_blocks_unknown_strategy_id_with_symbol_history() -> None:
    draft_paper_strategy(
        "SBIN",
        "Valid symbol history should not authorize arbitrary strategy ids.",
    )
    create_backtest_request(
        "SBIN",
        "pullback-to-support",
        "2026-03-01",
        "2026-06-22",
    )

    result = create_paper_order_proposal(
        strategy_id="strategy-sbin-not-persisted",
        symbol="SBIN",
        side="buy",
        quantity=2,
        order_type="market",
    )
    orders = list_paper_orders()

    assert result["status"] == "blocked"
    assert result["readiness_preflight"]["status"] == "blocked"
    submitted_strategy_gate = next(
        gate
        for gate in result["readiness_preflight"]["risk_gates"]
        if gate["name"] == "submitted_strategy"
    )
    assert submitted_strategy_gate["status"] == "fail"
    assert "paper_order" not in result
    assert not any(
        item["strategy_id"] == "strategy-sbin-not-persisted"
        for item in orders["orders"]
    )


def test_paper_positions_are_read_only_and_fixture_backed() -> None:
    positions = list_paper_positions()

    assert positions["status"] == "success"
    assert positions["policy"]["tier"] == "read_only"
    assert positions["source"] == "offline_fixture"
    assert positions["positions"]
    assert all(position["mode"] == "paper" for position in positions["positions"])


def test_invalid_paper_order_side_is_rejected_before_proposal() -> None:
    result = create_paper_order_proposal(
        strategy_id="strategy-invalid-side",
        symbol="TATAMOTORS",
        side="sell-short",
        quantity=1,
    )

    assert result["status"] == "error"
    assert result["policy"]["tier"] == "draft_only"
    assert "side" in result["error"].lower()
