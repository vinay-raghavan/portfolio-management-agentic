from app.agent import WORKFLOW_ROUTING_GUIDE, root_agent


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
    assert "validate_data_provider_imports" in tool_names
    assert "list_provider_source_templates" in tool_names
    assert "list_provider_source_onboarding" in tool_names
    assert "list_provider_import_previews" in tool_names
    assert "list_provider_import_reconciliation" in tool_names
    assert "get_market_data_snapshot" in tool_names
    assert "list_market_data_snapshots" in tool_names
    assert "get_universe_members" in tool_names
    assert "list_universes" in tool_names
    assert "run_screener" in tool_names
    assert "list_screener_runs" in tool_names
    assert "search_pattern_library" in tool_names
    assert "search_curated_research" in tool_names
    assert "get_pattern_playbook" in tool_names
    assert "cite_strategy_evidence" in tool_names
    assert "explain_factor_stack" in tool_names
    assert "get_recommendation_explanation" in tool_names
    assert "generate_paper_trading_report" in tool_names
    assert "create_backtest_request" in tool_names
    assert "list_backtest_requests" in tool_names
    assert "get_backtest_request" in tool_names
    assert "get_backtest_result" in tool_names
    assert "list_paper_orders" in tool_names
    assert "list_paper_positions" in tool_names
    assert "list_paper_fills" in tool_names
    assert "get_paper_portfolio_accounting" in tool_names
    assert "create_paper_order_proposal" in tool_names
    assert "get_approval_queue" in tool_names
    assert "get_audit_events" in tool_names
    assert "draft_paper_strategy" in tool_names
    assert "list_strategy_drafts" in tool_names
    assert "get_strategy_draft" in tool_names
    assert "place_live_order" not in tool_names
    assert "get_broker_trading_token" not in tool_names


def test_agent_instruction_has_eval_aligned_workflow_routes() -> None:
    instruction = root_agent.instruction

    required_routes = {
        "Pre-market briefing": (
            "create_pre_market_briefing",
            "get_portfolio_summary",
            "get_watchlist_snapshot",
            "get_signal_summary",
            "get_research_digest",
            "get_risk_review",
        ),
        "Provider readiness": (
            "list_data_providers",
            "get_data_provider_health",
            "validate_data_provider_imports",
            "list_provider_import_reconciliation",
            "get_provider_refresh_readiness",
        ),
        "Candidate explanation": (
            "run_screener",
            "explain_candidate_evidence",
            "pattern evidence, source grounding, citations, or relevant pattern sources",
            "search_pattern_library",
            "search_curated_research",
            "cite_strategy_evidence",
            "explain_factor_stack",
        ),
        "Recommendation to paper order": (
            "get_recommendation_explanation",
            "create_backtest_request",
            "get_backtest_result",
            "create_paper_order_proposal",
            "get_approval_queue",
            "get_audit_events",
        ),
        "Approval-gated simulated fill": (
            "verified human approval API",
            "protected paper-execution worker",
            "first call get_approval_queue and list_paper_orders",
            "list_paper_fills",
            "get_paper_portfolio_accounting",
        ),
        "Paper-trading report": (
            "generate_paper_trading_report",
            "get_audit_events",
        ),
    }

    for route_name, route_tools in required_routes.items():
        assert route_name in WORKFLOW_ROUTING_GUIDE
        assert route_name in instruction
        for tool_name in route_tools:
            assert tool_name in WORKFLOW_ROUTING_GUIDE
            assert tool_name in instruction


def test_agent_does_not_expose_human_approval_tool_to_model() -> None:
    tool_names = {
        getattr(tool, "name", getattr(tool, "__name__", ""))
        for tool in root_agent.tools
    }

    assert "approve_paper_order_simulation" not in tool_names
    assert "simulate_approved_paper_fill" not in tool_names
    assert "verified human approval API" in root_agent.instruction


def test_agent_instruction_refuses_forbidden_actions_without_tool_calls() -> None:
    instruction = root_agent.instruction.lower()

    assert "refuse without calling a tool" in instruction
    assert "live order" in instruction
    assert "live strategy" in instruction
    assert "broker trading token" in instruction
    assert "credential" in instruction
    assert "no live-trading fallback" in instruction
