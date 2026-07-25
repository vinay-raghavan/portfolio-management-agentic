from __future__ import annotations

from portfolio_harness import DeterministicRouter, RouteDecision, RouteDecisionType


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


def test_ambiguous_read_only_request_can_fall_back_to_model_classification() -> None:
    decision = DeterministicRouter().route("Can you explain what looks interesting today?")

    assert decision.decision_type == RouteDecisionType.NEEDS_CLASSIFICATION
    assert decision.capability_name is None
    assert decision.allowed_tools == ()
    assert decision.model_classification_allowed is True
    assert decision.confidence < 1.0
