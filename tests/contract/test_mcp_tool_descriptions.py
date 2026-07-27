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
        "always follow with get_data_provider_health",
        "before availability claims",
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
        "call explain_candidate_evidence or explain_factor_stack before explaining a candidate",
        "does not draft or place orders",
    ),
    "explain_candidate_evidence": (
        "candidate-explanation",
        "after a screener candidate",
        "call cite_strategy_evidence when pattern sources are requested",
        "does not create strategies or orders",
    ),
    "cite_strategy_evidence": (
        "source-grounded candidate",
        "paper-strategy explanation",
    ),
    "explain_factor_stack": (
        "deterministic factors",
        "follow with cite_strategy_evidence for source-grounded pattern citations",
        "paper-only next actions",
    ),
    "get_recommendation_explanation": (
        "recommendation-to-paper-order",
        "must precede any paper order proposal",
    ),
    "create_backtest_request": (
        "recommendation-to-paper-order",
        "before paper order proposals",
    ),
    "create_paper_order_proposal": (
        "recommendation-to-paper-order",
        "call get_recommendation_explanation first",
        "requires a ready recommendation preflight",
        "does not fill",
    ),
    "draft_paper_strategy": (
        "draft-only",
        "infer rationale from screener/backtest evidence",
        "without executing any trade",
    ),
    "get_approval_queue": (
        "first step before paper order",
        "post-approval inspection",
    ),
    "list_paper_orders": (
        "after get_approval_queue",
        "before fills/accounting",
        "without executing or filling",
    ),
    "list_paper_fills": (
        "after approval queue and paper order status inspection",
        "without touching any broker provider",
    ),
    "get_paper_portfolio_accounting": (
        "after simulated fills and paper order status inspection",
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
