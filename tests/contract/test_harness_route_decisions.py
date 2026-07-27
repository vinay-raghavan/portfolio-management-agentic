from __future__ import annotations

from portfolio_harness import (
    DeterministicRouter,
    RouteDecision,
    RouteDecisionType,
    RouteToolBundle,
)
from portfolio_mcp.tools import EXPOSED_TOOL_NAMES
from portfolio_policy import ActionTier


def test_forbidden_live_trading_routes_to_toolless_safety() -> None:
    decision = DeterministicRouter().route(
        "Place a live market order for RELIANCE using my broker token."
    )

    assert isinstance(decision, RouteDecision)
    assert decision.decision_type == RouteDecisionType.FORBIDDEN
    assert decision.capability_name == "safety"
    assert decision.model_classification_allowed is False
    assert decision.allowed_tools == ()
    assert decision.confidence == 1.0
    assert "place_live_order" in decision.forbidden_tools
    assert "get_broker_trading_token" in decision.forbidden_tools


def test_fyers_refresh_routes_to_human_api_without_model_url_or_credentials() -> None:
    decision = DeterministicRouter().route(
        "Refresh my FYERS holdings and account profile now."
    )

    assert decision.decision_type == RouteDecisionType.HUMAN_API_REQUIRED
    assert decision.capability_name == "fyers_data"
    assert decision.model_classification_allowed is False
    assert decision.human_api == "/v1/integrations/fyers/refresh"
    assert "oauth" not in " ".join(decision.allowed_tools).lower()
    assert "token" not in " ".join(decision.allowed_tools).lower()


def test_paper_approval_routes_to_human_api_not_model_tool() -> None:
    decision = DeterministicRouter().route(
        "Approve the pending paper order and mark it approved by me."
    )

    assert decision.decision_type == RouteDecisionType.HUMAN_API_REQUIRED
    assert decision.capability_name == "paper_proposal_execution"
    assert decision.human_api == "/v1/paper/batches/{id}/approve"
    assert decision.model_classification_allowed is False
    assert "approve_paper_order_simulation" not in decision.allowed_tools
    assert "simulate_approved_paper_fill" not in decision.allowed_tools


def test_paper_proposal_routes_to_draft_only_capability() -> None:
    decision = DeterministicRouter().route(
        "Create a paper order proposal after checking the backtest and risk review."
    )

    assert decision.decision_type == RouteDecisionType.CAPABILITY
    assert decision.capability_name == "paper_proposal_execution"
    assert decision.model_classification_allowed is False
    assert "create_paper_order_proposal" in decision.allowed_tools
    assert "get_recommendation_explanation" in decision.allowed_tools
    assert "approve_paper_order_simulation" not in decision.allowed_tools


def test_paper_proposal_tool_bundle_is_route_scoped_not_monolithic() -> None:
    router = DeterministicRouter()
    decision = router.route(
        "Create a paper order proposal after checking the backtest and risk review."
    )

    bundle = router.tool_bundle_for(decision, exposed_tool_names=EXPOSED_TOOL_NAMES)

    assert isinstance(bundle, RouteToolBundle)
    assert bundle.model_visible is True
    assert bundle.capability_name == "paper_proposal_execution"
    assert bundle.tool_names == decision.allowed_tools
    assert set(bundle.tool_names) < EXPOSED_TOOL_NAMES
    assert "create_paper_order_proposal" in bundle.tool_names
    assert "get_recommendation_explanation" in bundle.tool_names
    assert "search_curated_research" not in bundle.tool_names
    assert "get_fyers_account_snapshot" not in bundle.tool_names
    assert "simulate_approved_paper_fill" not in bundle.tool_names
    assert "approve_paper_order_simulation" not in bundle.tool_names
    assert bundle.max_action_tier == ActionTier.DRAFT_ONLY.value
    assert bundle.token_budget == {
        "input_tokens": 8000,
        "output_tokens": 1000,
        "tool_calls": 3,
    }
    assert bundle.unavailable_tools == ()


def test_human_api_and_forbidden_routes_have_empty_model_tool_bundle() -> None:
    router = DeterministicRouter()
    refresh_decision = router.route("Refresh my FYERS holdings now.")
    forbidden_decision = router.route("Place a live order for INFY.")

    refresh_bundle = router.tool_bundle_for(
        refresh_decision,
        exposed_tool_names=EXPOSED_TOOL_NAMES,
    )
    forbidden_bundle = router.tool_bundle_for(
        forbidden_decision,
        exposed_tool_names=EXPOSED_TOOL_NAMES,
    )

    assert refresh_bundle.model_visible is False
    assert refresh_bundle.tool_names == ()
    assert refresh_bundle.human_api == "/v1/integrations/fyers/refresh"
    assert forbidden_bundle.model_visible is False
    assert forbidden_bundle.tool_names == ()
    assert forbidden_bundle.forbidden_tools


def test_schema_classified_read_only_route_resolves_to_manifest_bundle() -> None:
    router = DeterministicRouter()
    decision = router.resolve_classified_capability(
        "research",
        confidence=0.84,
        reason="Schema-constrained read-only classifier selected research.",
    )

    bundle = router.tool_bundle_for(decision, exposed_tool_names=EXPOSED_TOOL_NAMES)

    assert decision.decision_type == RouteDecisionType.CAPABILITY
    assert decision.model_classification_allowed is True
    assert bundle.capability_name == "research"
    assert bundle.max_action_tier == ActionTier.READ_ONLY.value
    assert bundle.tool_names == (
        "cite_strategy_evidence",
        "get_pattern_playbook",
        "get_research_digest",
        "search_curated_research",
        "search_pattern_library",
    )
    assert "create_paper_order_proposal" not in bundle.tool_names
    assert "simulate_approved_paper_fill" not in bundle.tool_names


def test_ambiguous_read_only_request_can_fall_back_to_model_classification() -> None:
    decision = DeterministicRouter().route("Can you explain what looks interesting today?")

    assert decision.decision_type == RouteDecisionType.NEEDS_CLASSIFICATION
    assert decision.capability_name is None
    assert decision.allowed_tools == ()
    assert decision.model_classification_allowed is True
    assert decision.confidence < 1.0
