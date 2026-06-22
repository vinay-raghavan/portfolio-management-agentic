from app.agent import root_agent


def test_agent_imports_without_google_credentials() -> None:
    assert root_agent.name == "portfolio_management_agent"


def test_agent_exposes_only_safe_portfolio_tools() -> None:
    tool_names = {
        getattr(tool, "name", getattr(tool, "__name__", "")) for tool in root_agent.tools
    }

    assert "get_portfolio_summary" in tool_names
    assert "get_watchlist_snapshot" in tool_names
    assert "get_signal_summary" in tool_names
    assert "get_research_digest" in tool_names
    assert "create_pre_market_briefing" in tool_names
    assert "run_momentum_screener" in tool_names
    assert "list_universes" in tool_names
    assert "run_screener" in tool_names
    assert "search_pattern_library" in tool_names
    assert "get_pattern_playbook" in tool_names
    assert "cite_strategy_evidence" in tool_names
    assert "explain_factor_stack" in tool_names
    assert "draft_paper_strategy" in tool_names
    assert "place_live_order" not in tool_names
    assert "get_broker_trading_token" not in tool_names
