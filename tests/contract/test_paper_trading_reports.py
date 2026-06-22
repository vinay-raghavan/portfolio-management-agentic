from portfolio_mcp.tools import (
    approve_paper_order_simulation,
    create_backtest_request,
    create_paper_order_proposal,
    draft_paper_strategy,
    generate_paper_trading_report,
    simulate_approved_paper_fill,
)


def test_paper_trading_report_includes_review_sections_and_audit_export() -> None:
    strategy = draft_paper_strategy(
        "TATAMOTORS",
        "Report fixture strategy with breakout and factor confirmation.",
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
        quantity=3,
        order_type="market",
    )
    approve_paper_order_simulation(
        proposal["paper_order"]["order_id"],
        approved_by="contract-test-reviewer",
        approval_note="Approve report fixture simulation.",
    )
    simulate_approved_paper_fill(
        proposal["paper_order"]["order_id"],
        fill_price=981.25,
    )

    result = generate_paper_trading_report(
        "TATAMOTORS",
        "breakout-continuation",
    )
    report = result["report"]
    audit_export = report["audit_export"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert report["mode"] == "read_only"
    assert report["report_type"] == "paper_trading_review"
    assert report["summary"]["simulated_fills"] >= 1
    assert report["summary"]["audit_event_count"] >= 3
    assert report["sections"]["paper_accounting"]["simulated_fills"] >= 1
    assert report["sections"]["positions"]
    assert report["sections"]["orders"]
    assert report["sections"]["fills"]
    assert report["recommendation"]["stance"] == "paper_draft_candidate"

    assert audit_export["schema_version"] == "paper-audit-export/v1"
    assert audit_export["mode"] == "read_only"
    assert audit_export["redaction_status"] == "redacted"
    assert audit_export["row_count"] == len(audit_export["rows"])
    assert {
        "paper_order_proposed",
        "paper_order_approved",
        "paper_fill_simulated",
    }.issubset({row["event_type"] for row in audit_export["rows"]})
    assert "place_live_order" not in report["next_allowed_actions"]
    assert "get_broker_trading_token" not in str(report).lower()
    assert "/users/" not in str(report).lower()


def test_paper_trading_report_without_symbol_is_portfolio_scoped() -> None:
    result = generate_paper_trading_report()
    report = result["report"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert report["scope"] == "portfolio"
    assert report["recommendation"] is None
    assert report["sections"]["paper_accounting"]["source"] == "offline_fixture"
    assert "get_recommendation_explanation" in report["next_allowed_actions"]


def test_paper_trading_report_requires_setup_when_symbol_is_supplied() -> None:
    result = generate_paper_trading_report("TATAMOTORS")

    assert result["status"] == "error"
    assert result["policy"]["tier"] == "read_only"
    assert "setup" in result["error"].lower()
