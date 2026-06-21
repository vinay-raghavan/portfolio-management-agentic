from portfolio_mcp.tools import (
    EXPOSED_TOOL_NAMES,
    assert_exposed_tools_are_safe,
    create_paper_trade_proposal,
    draft_paper_strategy,
    get_broker_trading_token,
    get_portfolio_summary,
    place_live_order,
    run_momentum_screener,
)


def test_exposed_tool_catalog_contains_no_forbidden_tools() -> None:
    assert_exposed_tools_are_safe()
    assert "place_live_order" not in EXPOSED_TOOL_NAMES
    assert "get_broker_trading_token" not in EXPOSED_TOOL_NAMES


def test_portfolio_summary_uses_demo_data_only() -> None:
    result = get_portfolio_summary()

    assert result["status"] == "success"
    assert result["portfolio"]["currency"] == "INR"
    assert result["portfolio"]["notes"][0].startswith("Synthetic demo portfolio")


def test_screener_to_strategy_to_pending_paper_proposal() -> None:
    screener = run_momentum_screener(1)
    symbol = screener["candidates"][0]["symbol"]

    draft = draft_paper_strategy(symbol, "Top synthetic momentum candidate")
    proposal = create_paper_trade_proposal(draft["strategy"]["strategy_id"])

    assert draft["strategy"]["mode"] == "paper"
    assert draft["strategy"]["status"] == "draft"
    assert proposal["status"] == "pending_approval"
    assert proposal["proposal"]["mode"] == "paper"


def test_forbidden_compatibility_traps_are_blocked_and_redacted() -> None:
    live_order = place_live_order("INFY", 1, "buy")
    token = get_broker_trading_token("fyers")

    assert live_order["status"] == "blocked"
    assert token["status"] == "blocked"
    assert token["details"]["broker_token"] == "[REDACTED]"

