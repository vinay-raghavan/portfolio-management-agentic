from portfolio_policy import (
    ActionTier,
    authorize_tool_call,
    classify_tool,
    redact_sensitive,
)


def test_unknown_tools_are_forbidden_by_default() -> None:
    decision = authorize_tool_call("surprise_live_trade_tool")

    assert decision.allowed is False
    assert decision.tier == ActionTier.FORBIDDEN


def test_live_order_and_broker_token_tools_are_forbidden() -> None:
    for tool_name in ("place_live_order", "get_broker_trading_token"):
        decision = authorize_tool_call(tool_name)

        assert decision.allowed is False
        assert decision.requires_approval is False
        assert decision.tier == ActionTier.FORBIDDEN


def test_draft_and_read_only_tools_are_allowed_without_approval() -> None:
    for tool_name in (
        "get_portfolio_summary",
        "get_watchlist_snapshot",
        "get_signal_summary",
        "get_research_digest",
        "create_pre_market_briefing",
        "list_data_providers",
        "get_data_provider_health",
        "validate_data_provider_imports",
        "list_provider_profiles",
        "list_provider_source_templates",
        "list_provider_source_onboarding",
        "list_provider_import_previews",
        "list_provider_import_jobs",
        "get_provider_refresh_readiness",
        "get_market_data_snapshot",
        "get_universe_members",
        "list_universes",
        "run_screener",
        "explain_candidate_evidence",
        "search_pattern_library",
        "get_pattern_playbook",
        "cite_strategy_evidence",
        "explain_factor_stack",
        "get_recommendation_explanation",
        "generate_paper_trading_report",
        "create_backtest_request",
        "refresh_provider_import_profile",
        "run_provider_refresh_schedule",
        "list_backtest_requests",
        "get_backtest_request",
        "get_backtest_result",
        "list_paper_orders",
        "list_paper_positions",
        "list_paper_fills",
        "get_paper_portfolio_accounting",
        "create_paper_order_proposal",
        "get_approval_queue",
        "get_audit_events",
        "draft_paper_strategy",
        "list_strategy_drafts",
        "get_strategy_draft",
    ):
        decision = authorize_tool_call(tool_name)

        assert decision.allowed is True
        assert decision.requires_approval is False
        assert classify_tool(tool_name) in {ActionTier.READ_ONLY, ActionTier.DRAFT_ONLY}


def test_approval_required_tools_are_marked_for_human_review() -> None:
    for tool_name in (
        "request_paper_trade_approval",
        "approve_paper_order_simulation",
        "simulate_approved_paper_fill",
    ):
        decision = authorize_tool_call(tool_name)

        assert decision.allowed is True
        assert decision.requires_approval is True
        assert decision.tier == ActionTier.APPROVAL_REQUIRED


def test_redaction_removes_sensitive_values() -> None:
    payload = {
        "provider": "fyers",
        "token": "abc",
        "nested": {"client_secret": "def", "safe": "value"},
    }

    assert redact_sensitive(payload) == {
        "provider": "fyers",
        "token": "[REDACTED]",
        "nested": {"client_secret": "[REDACTED]", "safe": "value"},
    }
