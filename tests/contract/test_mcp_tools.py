from portfolio_mcp.tools import (
    EXPOSED_TOOL_NAMES,
    assert_exposed_tools_are_safe,
    create_pre_market_briefing,
    create_paper_trade_proposal,
    cite_strategy_evidence,
    draft_paper_strategy,
    explain_factor_stack,
    get_data_provider_health,
    get_market_data_snapshot,
    get_pattern_playbook,
    get_broker_trading_token,
    get_portfolio_summary,
    get_research_digest,
    get_universe_members,
    list_data_providers,
    list_universes,
    place_live_order,
    run_screener,
    run_momentum_screener,
    search_pattern_library,
    get_signal_summary,
    get_watchlist_snapshot,
    validate_data_provider_imports,
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


def test_pre_market_briefing_workflow_uses_synthetic_read_only_sections() -> None:
    watchlist = get_watchlist_snapshot()
    signals = get_signal_summary()
    research = get_research_digest()
    briefing = create_pre_market_briefing()

    assert watchlist["status"] == "success"
    assert signals["status"] == "success"
    assert research["status"] == "success"
    assert briefing["status"] == "success"
    assert briefing["briefing"]["mode"] == "read_only"
    assert briefing["briefing"]["source"] == "synthetic_demo"
    assert briefing["briefing"]["portfolio"]["currency"] == "INR"
    assert briefing["briefing"]["watchlist"]["items"]
    assert briefing["briefing"]["signal_summary"]["regime"] == "constructive"
    assert briefing["briefing"]["research_digest"]["notes"]
    assert briefing["briefing"]["risk_review"]["safety_switches"]["live_trading"] == "disabled"
    assert all(
        "order" not in action.lower()
        for action in briefing["briefing"]["suggested_review_actions"]
    )


def test_screener_to_strategy_to_pending_paper_proposal() -> None:
    screener = run_momentum_screener(1)
    symbol = screener["candidates"][0]["symbol"]

    draft = draft_paper_strategy(symbol, "Top synthetic momentum candidate")
    proposal = create_paper_trade_proposal(draft["strategy"]["strategy_id"])

    assert draft["strategy"]["mode"] == "paper"
    assert draft["strategy"]["status"] == "draft"
    assert proposal["status"] == "pending_approval"
    assert proposal["proposal"]["mode"] == "paper"


def test_product_data_pattern_foundation_tools_are_read_only() -> None:
    universes = list_universes()
    screener = run_screener("fixture_nifty50", "momentum", 3)
    patterns = search_pattern_library("momentum", "", 2)
    playbook = get_pattern_playbook(patterns["patterns"][0]["pattern_id"])
    evidence = cite_strategy_evidence("TATAMOTORS", "breakout-continuation")
    factor_stack = explain_factor_stack("TATAMOTORS", "breakout-continuation")

    assert universes["policy"]["tier"] == "read_only"
    assert screener["policy"]["tier"] == "read_only"
    assert playbook["policy"]["tier"] == "read_only"
    assert evidence["evidence_pack"]["paper_only_status"] == "analysis_only"
    assert factor_stack["factor_stack"]["paper_only_status"] == "analysis_only"


def test_provider_adapter_tools_are_read_only_and_fixture_backed() -> None:
    providers = list_data_providers()
    health = get_data_provider_health()
    import_validation = validate_data_provider_imports()
    snapshot = get_market_data_snapshot("TATAMOTORS")
    universe = get_universe_members("fixture_nifty50")

    assert providers["policy"]["tier"] == "read_only"
    assert health["policy"]["tier"] == "read_only"
    assert import_validation["policy"]["tier"] == "read_only"
    assert import_validation["summary"]["total"] == 6
    assert snapshot["snapshot"]["source"] == "offline_fixture"
    assert universe["universe"]["provider_id"] == "fixture_universe"


def test_forbidden_compatibility_traps_are_blocked_and_redacted() -> None:
    live_order = place_live_order("INFY", 1, "buy")
    token = get_broker_trading_token("fyers")

    assert live_order["status"] == "blocked"
    assert token["status"] == "blocked"
    assert token["details"]["broker_token"] == "[REDACTED]"
