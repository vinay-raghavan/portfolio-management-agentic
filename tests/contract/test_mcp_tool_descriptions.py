from inspect import getdoc

from portfolio_mcp import tools
from portfolio_mcp.tools import EXPOSED_TOOL_NAMES
from portfolio_policy import ActionTier, classify_tool


TIER_DESCRIPTION_PHRASES = {
    ActionTier.READ_ONLY: "read-only",
    ActionTier.DRAFT_ONLY: "draft-only",
    ActionTier.APPROVAL_REQUIRED: "approval-required",
}

WORKFLOW_DESCRIPTION_REQUIREMENTS = {
    "list_data_providers": (
        "provider-readiness",
        "before claiming configured data is available",
    ),
    "get_data_provider_health": (
        "provider-readiness",
        "without exposing credential values",
    ),
    "validate_data_provider_imports": (
        "provider-readiness",
        "without exposing local paths",
    ),
    "list_provider_import_previews": (
        "provider-readiness",
        "dry-run",
        "before refresh",
    ),
    "list_provider_import_reconciliation": (
        "provider-readiness",
        "before configured screeners or paper-order readiness",
    ),
    "run_screener": (
        "candidate-discovery",
        "hard gates",
        "does not draft or place orders",
    ),
    "explain_candidate_evidence": (
        "candidate-explanation",
        "after a screener candidate",
        "does not create strategies or orders",
    ),
    "get_recommendation_explanation": (
        "recommendation-to-paper-order",
        "before any paper order proposal",
    ),
    "create_backtest_request": (
        "recommendation-to-paper-order",
        "before paper order proposals",
    ),
    "create_paper_order_proposal": (
        "recommendation-to-paper-order",
        "requires a ready recommendation preflight",
        "does not fill",
    ),
    "simulate_approved_paper_fill": (
        "approval-gated simulated fill",
        "only after verified human approval",
        "never live",
    ),
    "generate_paper_trading_report": (
        "paper-trading-report",
        "read-only review",
        "redacted audit",
    ),
}


def _doc(tool_name: str) -> str:
    return (getdoc(getattr(tools, tool_name)) or "").lower()


def test_exposed_tool_descriptions_name_policy_tier() -> None:
    for tool_name in EXPOSED_TOOL_NAMES:
        tier = classify_tool(tool_name)
        assert tier in TIER_DESCRIPTION_PHRASES
        assert TIER_DESCRIPTION_PHRASES[tier] in _doc(tool_name)


def test_workflow_tool_descriptions_explain_safe_trajectory() -> None:
    for tool_name, required_phrases in WORKFLOW_DESCRIPTION_REQUIREMENTS.items():
        doc = _doc(tool_name)
        for phrase in required_phrases:
            assert phrase in doc
