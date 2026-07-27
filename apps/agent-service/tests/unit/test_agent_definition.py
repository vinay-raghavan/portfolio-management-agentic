from google.genai import types

from app.agent import (
    ROUTER,
    WORKFLOW_ROUTING_GUIDE,
    _extract_text_from_content,
    _route_scope_model_request,
    _route_scope_tool_call,
    root_agent,
)


class _FakeContext:
    def __init__(self, text: str) -> None:
        self.user_content = types.Content(role="user", parts=[types.Part(text=text)])


class _FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeRequest:
    def __init__(self, tools_dict: dict[str, object]) -> None:
        self.tools_dict = tools_dict


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


def test_before_model_callback_filters_tools_to_paper_proposal_route() -> None:
    paper_tools = {
        tool_name: object()
        for tool_name in ROUTER.manifests["paper_proposal_execution"].allowed_tools
    }
    request = _FakeRequest(
        {
            **paper_tools,
            "search_curated_research": object(),
            "get_fyers_account_snapshot": object(),
        }
    )

    response = _route_scope_model_request(
        _FakeContext("Create a paper order proposal after checking risk."),
        request,
    )

    assert response is None
    assert set(request.tools_dict) == set(paper_tools)
    assert "create_paper_order_proposal" in request.tools_dict
    assert "get_recommendation_explanation" in request.tools_dict
    assert "search_curated_research" not in request.tools_dict
    assert "get_fyers_account_snapshot" not in request.tools_dict


def test_before_model_callback_short_circuits_forbidden_and_human_api_routes() -> None:
    forbidden_request = _FakeRequest({"get_portfolio_summary": object()})
    forbidden_response = _route_scope_model_request(
        _FakeContext("Place a live order for RELIANCE."),
        forbidden_request,
    )

    assert forbidden_response is not None
    assert forbidden_response.error_code == "portfolio_route_forbidden"
    assert forbidden_request.tools_dict == {}
    assert "live trading" in _extract_text_from_content(forbidden_response.content).lower()

    human_api_request = _FakeRequest({"get_fyers_account_snapshot": object()})
    human_api_response = _route_scope_model_request(
        _FakeContext("Refresh my FYERS holdings now."),
        human_api_request,
    )

    assert human_api_response is not None
    assert human_api_response.error_code == "portfolio_human_api_required"
    assert human_api_request.tools_dict == {}
    assert "/v1/integrations/fyers/refresh" in _extract_text_from_content(
        human_api_response.content
    )


def test_before_tool_callback_blocks_out_of_route_tool_calls() -> None:
    blocked = _route_scope_tool_call(
        _FakeTool("search_curated_research"),
        {},
        _FakeContext("Create a paper order proposal after checking risk."),
    )
    allowed = _route_scope_tool_call(
        _FakeTool("create_paper_order_proposal"),
        {},
        _FakeContext("Create a paper order proposal after checking risk."),
    )

    assert blocked == {
        "error": "tool_not_allowed_for_route",
        "tool": "search_curated_research",
        "capability": "paper_proposal_execution",
    }
    assert allowed is None


def test_before_model_and_tool_callbacks_route_scope_pre_market_briefing() -> None:
    pre_market_tools = {
        tool_name: object()
        for tool_name in ROUTER.manifests["pre_market_briefing"].allowed_tools
    }
    request = _FakeRequest(
        {
            **pre_market_tools,
            "create_paper_order_proposal": object(),
            "get_fyers_account_snapshot": object(),
        }
    )

    response = _route_scope_model_request(
        _FakeContext("Build my pre-market briefing."),
        request,
    )

    assert response is None
    assert set(request.tools_dict) == set(pre_market_tools)
    assert "create_pre_market_briefing" in request.tools_dict
    assert "create_paper_order_proposal" not in request.tools_dict
    assert "get_fyers_account_snapshot" not in request.tools_dict
    assert (
        _route_scope_tool_call(
            _FakeTool("create_pre_market_briefing"),
            {},
            _FakeContext("Build my pre-market briefing."),
        )
        is None
    )
