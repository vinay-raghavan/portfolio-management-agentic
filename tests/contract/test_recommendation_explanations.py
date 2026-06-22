from portfolio_mcp.tools import (
    create_backtest_request,
    draft_paper_strategy,
    get_recommendation_explanation,
)


def test_recommendation_explanation_joins_evidence_history_and_ledger() -> None:
    strategy = draft_paper_strategy(
        "TATAMOTORS",
        "Top fixture candidate with breakout and factor confirmation.",
    )
    backtest = create_backtest_request(
        "TATAMOTORS",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )

    result = get_recommendation_explanation(
        "TATAMOTORS",
        "breakout-continuation",
    )
    recommendation = result["recommendation"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert recommendation["mode"] == "analysis_only"
    assert recommendation["stance"] == "paper_draft_candidate"
    assert recommendation["symbol"] == "TATAMOTORS"
    assert recommendation["setup"] == "breakout-continuation"

    assert "technical" in recommendation["factor_summary"]
    assert recommendation["factor_summary"]["technical"]["evidence"]
    assert (
        strategy["strategy"]["strategy_id"]
        in recommendation["history_refs"]["strategy_ids"]
    )
    assert (
        backtest["backtest_request"]["request_id"]
        in recommendation["history_refs"]["backtest_request_ids"]
    )
    assert (
        recommendation["backtest_summary"]["latest_request_id"]
        == backtest["backtest_request"]["request_id"]
    )
    assert recommendation["backtest_summary"]["metrics"]["total_return_pct"] > 0
    assert recommendation["ledger_context"]["positions"]
    assert recommendation["ledger_context"]["positions"][0]["symbol"] == "TATAMOTORS"
    assert any(
        gate["name"] == "live_trading_disabled" and gate["status"] == "pass"
        for gate in recommendation["risk_gates"]
    )
    assert recommendation["citations"]
    assert "create_paper_order_proposal" in recommendation["next_allowed_actions"]
    assert "place_live_order" not in recommendation["next_allowed_actions"]


def test_recommendation_explanation_marks_missing_history_as_needs_review() -> None:
    result = get_recommendation_explanation("SUNPHARMA", "quality-momentum")
    recommendation = result["recommendation"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert recommendation["stance"] == "needs_review"
    assert "strategy_draft_history" in recommendation["missing_data"]
    assert "backtest_request_history" in recommendation["missing_data"]
    assert "draft_paper_strategy" in recommendation["next_allowed_actions"]
    assert "create_backtest_request" in recommendation["next_allowed_actions"]
    assert "create_paper_order_proposal" not in recommendation["next_allowed_actions"]


def test_recommendation_explanation_rejects_unknown_fixture_symbol() -> None:
    result = get_recommendation_explanation("UNKNOWN", "breakout-continuation")

    assert result["status"] == "error"
    assert result["policy"]["tier"] == "read_only"
    assert "unknown fixture symbol" in result["error"].lower()
