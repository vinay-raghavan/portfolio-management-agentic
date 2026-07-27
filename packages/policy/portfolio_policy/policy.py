from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class ActionTier(StrEnum):
    READ_ONLY = "read_only"
    DRAFT_ONLY = "draft_only"
    APPROVAL_REQUIRED = "approval_required"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class PolicyDecision:
    tool_name: str
    tier: ActionTier
    allowed: bool
    requires_approval: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tier"] = self.tier.value
        return payload


ACTION_TIERS: dict[str, ActionTier] = {
    "get_portfolio_summary": ActionTier.READ_ONLY,
    "get_watchlist_snapshot": ActionTier.READ_ONLY,
    "get_signal_summary": ActionTier.READ_ONLY,
    "get_research_digest": ActionTier.READ_ONLY,
    "create_pre_market_briefing": ActionTier.READ_ONLY,
    "run_momentum_screener": ActionTier.READ_ONLY,
    "list_data_providers": ActionTier.READ_ONLY,
    "get_data_provider_health": ActionTier.READ_ONLY,
    "validate_data_provider_imports": ActionTier.READ_ONLY,
    "list_provider_profiles": ActionTier.READ_ONLY,
    "list_provider_source_templates": ActionTier.READ_ONLY,
    "list_provider_source_onboarding": ActionTier.READ_ONLY,
    "list_provider_import_previews": ActionTier.READ_ONLY,
    "list_provider_import_reconciliation": ActionTier.READ_ONLY,
    "list_provider_import_jobs": ActionTier.READ_ONLY,
    "get_provider_refresh_readiness": ActionTier.READ_ONLY,
    "refresh_provider_import_profile": ActionTier.DRAFT_ONLY,
    "run_provider_refresh_schedule": ActionTier.DRAFT_ONLY,
    "get_fyers_connection_health": ActionTier.READ_ONLY,
    "get_fyers_quote": ActionTier.READ_ONLY,
    "get_fyers_ohlcv_history": ActionTier.READ_ONLY,
    "get_fyers_depth": ActionTier.READ_ONLY,
    "get_fyers_instrument_metadata": ActionTier.READ_ONLY,
    "get_fyers_option_chain": ActionTier.READ_ONLY,
    "get_fyers_account_snapshot": ActionTier.READ_ONLY,
    "get_market_data_snapshot": ActionTier.READ_ONLY,
    "list_market_data_snapshots": ActionTier.READ_ONLY,
    "get_universe_members": ActionTier.READ_ONLY,
    "list_universes": ActionTier.READ_ONLY,
    "run_screener": ActionTier.READ_ONLY,
    "list_screener_runs": ActionTier.READ_ONLY,
    "explain_candidate_evidence": ActionTier.READ_ONLY,
    "search_pattern_library": ActionTier.READ_ONLY,
    "search_curated_research": ActionTier.READ_ONLY,
    "get_pattern_playbook": ActionTier.READ_ONLY,
    "cite_strategy_evidence": ActionTier.READ_ONLY,
    "explain_factor_stack": ActionTier.READ_ONLY,
    "get_recommendation_explanation": ActionTier.READ_ONLY,
    "generate_paper_trading_report": ActionTier.READ_ONLY,
    "create_backtest_request": ActionTier.DRAFT_ONLY,
    "list_backtest_requests": ActionTier.READ_ONLY,
    "get_backtest_request": ActionTier.READ_ONLY,
    "get_backtest_result": ActionTier.READ_ONLY,
    "list_paper_orders": ActionTier.READ_ONLY,
    "list_paper_positions": ActionTier.READ_ONLY,
    "create_paper_order_proposal": ActionTier.DRAFT_ONLY,
    "approve_paper_order_simulation": ActionTier.APPROVAL_REQUIRED,
    "simulate_approved_paper_fill": ActionTier.APPROVAL_REQUIRED,
    "list_paper_fills": ActionTier.READ_ONLY,
    "get_paper_portfolio_accounting": ActionTier.READ_ONLY,
    "get_approval_queue": ActionTier.READ_ONLY,
    "get_audit_events": ActionTier.READ_ONLY,
    "get_risk_review": ActionTier.READ_ONLY,
    "draft_paper_strategy": ActionTier.DRAFT_ONLY,
    "list_strategy_drafts": ActionTier.READ_ONLY,
    "get_strategy_draft": ActionTier.READ_ONLY,
    "create_paper_trade_proposal": ActionTier.DRAFT_ONLY,
    "request_paper_trade_approval": ActionTier.APPROVAL_REQUIRED,
    "update_paper_risk_setting": ActionTier.APPROVAL_REQUIRED,
    "place_live_order": ActionTier.FORBIDDEN,
    "enable_live_strategy": ActionTier.FORBIDDEN,
    "get_broker_trading_token": ActionTier.FORBIDDEN,
    "print_all_credentials": ActionTier.FORBIDDEN,
}

SENSITIVE_KEYS = {
    "api_key",
    "access_token",
    "auth_token",
    "broker_token",
    "client_secret",
    "fyers_token",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def classify_tool(tool_name: str) -> ActionTier:
    """Return the configured action tier for a tool.

    Unknown tools are forbidden by default. New tools must be explicitly classified
    before they can be exposed to any agent platform.
    """
    return ACTION_TIERS.get(tool_name, ActionTier.FORBIDDEN)


def authorize_tool_call(tool_name: str) -> PolicyDecision:
    """Authorize a tool call against the action-tier policy."""
    tier = classify_tool(tool_name)

    if tier == ActionTier.FORBIDDEN:
        return PolicyDecision(
            tool_name=tool_name,
            tier=tier,
            allowed=False,
            requires_approval=False,
            reason="Forbidden by policy: live trading, credential access, or unclassified action.",
        )

    if tier == ActionTier.APPROVAL_REQUIRED:
        return PolicyDecision(
            tool_name=tool_name,
            tier=tier,
            allowed=True,
            requires_approval=True,
            reason="Allowed only as a pending paper-trading action with human approval.",
        )

    return PolicyDecision(
        tool_name=tool_name,
        tier=tier,
        allowed=True,
        requires_approval=False,
        reason=f"Allowed {tier.value} action.",
    )


def redact_sensitive(value: Any) -> Any:
    """Redact sensitive keys from nested dict/list payloads."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS or any(
                marker in key.lower() for marker in ("token", "secret", "password")
            ):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted

    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]

    return value
