from app.agent import root_agent


def test_agent_imports_without_google_credentials() -> None:
    assert root_agent.name == "portfolio_management_agent"


def test_agent_exposes_only_safe_portfolio_tools() -> None:
    tool_names = {
        getattr(tool, "name", getattr(tool, "__name__", ""))
        for tool in root_agent.tools
    }

    assert "get_portfolio_summary" in tool_names
    assert "get_watchlist_snapshot" in tool_names
    assert "get_signal_summary" in tool_names
    assert "get_research_digest" in tool_names
    assert "create_pre_market_briefing" in tool_names
    assert "run_momentum_screener" in tool_names
    assert "list_data_providers" in tool_names
    assert "get_data_provider_health" in tool_names
    assert "get_market_data_snapshot" in tool_names
    assert "get_universe_members" in tool_names
    assert "list_universes" in tool_names
    assert "run_screener" in tool_names
    assert "search_pattern_library" in tool_names
    assert "get_pattern_playbook" in tool_names
    assert "cite_strategy_evidence" in tool_names
    assert "explain_factor_stack" in tool_names
    assert "create_backtest_request" in tool_names
    assert "list_backtest_requests" in tool_names
    assert "get_backtest_request" in tool_names
    assert "get_backtest_result" in tool_names
    assert "list_paper_orders" in tool_names
    assert "list_paper_positions" in tool_names
    assert "list_paper_fills" in tool_names
    assert "get_paper_portfolio_accounting" in tool_names
    assert "create_paper_order_proposal" in tool_names
    assert "approve_paper_order_simulation" in tool_names
    assert "simulate_approved_paper_fill" in tool_names
    assert "get_approval_queue" in tool_names
    assert "get_audit_events" in tool_names
    assert "draft_paper_strategy" in tool_names
    assert "list_strategy_drafts" in tool_names
    assert "get_strategy_draft" in tool_names
    assert "place_live_order" not in tool_names
    assert "get_broker_trading_token" not in tool_names
