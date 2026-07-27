from __future__ import annotations

from typing import Any

from portfolio_domain import (
    approve_fixture_paper_order_simulation,
    build_factor_stack_explanation,
    build_paper_trading_report,
    build_paper_order_readiness_preflight,
    build_recommendation_explanation,
    build_strategy_evidence_pack,
    create_demo_pre_market_briefing,
    create_fixture_backtest_request,
    create_fixture_paper_order_proposal,
    create_fixture_strategy_draft,
    get_fixture_backtest_request,
    get_fixture_backtest_result,
    get_fixture_strategy_draft,
    get_fyers_readonly_connector,
    get_fixture_paper_portfolio_accounting,
    get_data_provider_registry,
    get_market_data_storage_status,
    get_pattern_card,
    get_demo_portfolio_summary,
    get_demo_research_digest,
    get_demo_risk_review,
    get_demo_signal_summary,
    get_demo_watchlist_snapshot,
    get_provider_profile_storage_status,
    list_provider_refresh_readiness as list_domain_provider_refresh_readiness,
    list_provider_import_previews as list_domain_provider_import_previews,
    list_provider_import_reconciliation as list_domain_provider_import_reconciliation,
    list_configured_provider_source_templates,
    list_fixture_approval_queue,
    list_fixture_audit_events,
    list_fixture_backtest_requests,
    list_fixture_paper_fills,
    list_fixture_paper_orders,
    list_fixture_paper_positions,
    list_fixture_strategy_drafts,
    list_fixture_universes,
    list_provider_configuration_profiles,
    list_provider_import_jobs as list_domain_provider_import_jobs,
    list_stored_market_snapshots,
    list_stored_screener_runs,
    record_market_data_snapshot,
    record_screener_run,
    run_fixture_screener,
    run_demo_momentum_screener,
    search_research_documents,
    search_pattern_cards,
    simulate_fixture_approved_paper_fill,
    refresh_provider_import_profile_metadata,
    run_provider_refresh_schedule as run_domain_provider_refresh_schedule,
    validate_configured_provider_imports,
)
from portfolio_policy import ActionTier, authorize_tool_call, redact_sensitive

EXPOSED_TOOL_NAMES = {
    "get_portfolio_summary",
    "get_watchlist_snapshot",
    "get_signal_summary",
    "get_research_digest",
    "create_pre_market_briefing",
    "run_momentum_screener",
    "list_data_providers",
    "get_data_provider_health",
    "validate_data_provider_imports",
    "list_provider_profiles",
    "list_provider_source_templates",
    "list_provider_source_onboarding",
    "list_provider_import_previews",
    "list_provider_import_reconciliation",
    "list_provider_import_jobs",
    "get_provider_refresh_readiness",
    "refresh_provider_import_profile",
    "run_provider_refresh_schedule",
    "get_fyers_connection_health",
    "get_fyers_quote",
    "get_fyers_account_snapshot",
    "get_market_data_snapshot",
    "list_market_data_snapshots",
    "get_universe_members",
    "list_universes",
    "run_screener",
    "list_screener_runs",
    "explain_candidate_evidence",
    "search_pattern_library",
    "search_curated_research",
    "get_pattern_playbook",
    "cite_strategy_evidence",
    "explain_factor_stack",
    "get_recommendation_explanation",
    "generate_paper_trading_report",
    "create_backtest_request",
    "list_backtest_requests",
    "get_backtest_request",
    "get_backtest_result",
    "list_paper_orders",
    "list_paper_positions",
    "create_paper_order_proposal",
    "simulate_approved_paper_fill",
    "list_paper_fills",
    "get_paper_portfolio_accounting",
    "get_approval_queue",
    "get_audit_events",
    "get_risk_review",
    "draft_paper_strategy",
    "list_strategy_drafts",
    "get_strategy_draft",
    "create_paper_trade_proposal",
}


def _policy_payload(tool_name: str) -> dict[str, Any]:
    return authorize_tool_call(tool_name).to_dict()


def _blocked(tool_name: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "blocked",
        "policy": _policy_payload(tool_name),
        "details": redact_sensitive(details or {}),
    }


def get_portfolio_summary() -> dict[str, Any]:
    """Read-only portfolio summary for paper-trading analysis."""
    tool_name = "get_portfolio_summary"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "portfolio": get_demo_portfolio_summary().to_dict(),
    }


def get_watchlist_snapshot() -> dict[str, Any]:
    """Read-only pre-market watchlist context."""
    tool_name = "get_watchlist_snapshot"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "watchlist": get_demo_watchlist_snapshot().to_dict(),
    }


def get_signal_summary() -> dict[str, Any]:
    """Read-only market setup and signal context."""
    tool_name = "get_signal_summary"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "signal_summary": get_demo_signal_summary().to_dict(),
    }


def get_research_digest() -> dict[str, Any]:
    """Read-only research and pattern notes for pre-market review."""
    tool_name = "get_research_digest"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "research_digest": get_demo_research_digest().to_dict(),
    }


def create_pre_market_briefing() -> dict[str, Any]:
    """Read-only pre-market briefing from portfolio, watchlist, signal, research, and risk evidence."""
    tool_name = "create_pre_market_briefing"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "briefing": create_demo_pre_market_briefing().to_dict(),
    }


def run_momentum_screener(limit: int) -> dict[str, Any]:
    """Read-only momentum screener over demo symbols; does not draft or place orders."""
    tool_name = "run_momentum_screener"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "candidates": [
            candidate.to_dict() for candidate in run_demo_momentum_screener(limit)
        ],
    }


def list_data_providers() -> dict[str, Any]:
    """Read-only provider-readiness catalog to call before claiming configured data is available."""
    tool_name = "list_data_providers"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    registry = get_data_provider_registry()
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "providers": [descriptor.to_dict() for descriptor in registry.descriptors()],
    }


def get_data_provider_health() -> dict[str, Any]:
    """Read-only provider-readiness health check without exposing credential values."""
    tool_name = "get_data_provider_health"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    registry = get_data_provider_registry()
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "health": [item.to_dict() for item in registry.health()],
    }


def get_fyers_connection_health() -> dict[str, Any]:
    """Read-only FYERS connector health without exposing credential values."""
    tool_name = "get_fyers_connection_health"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "health": get_fyers_readonly_connector().connection_health().to_dict(),
    }


def get_fyers_quote(symbol: str) -> dict[str, Any]:
    """Read-only FYERS quote snapshot; no fallback source and no trading action."""
    tool_name = "get_fyers_quote"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name, {"symbol": symbol})
    try:
        quote = get_fyers_readonly_connector().get_quote(symbol)
    except ValueError as exc:
        return {
            "status": "unavailable",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "quote": quote.to_dict(),
    }


def get_fyers_account_snapshot() -> dict[str, Any]:
    """Read-only FYERS normalized account snapshot with signed quantities and no credential values."""
    tool_name = "get_fyers_account_snapshot"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "snapshot": get_fyers_readonly_connector().get_account_snapshot().to_dict(),
    }


def validate_data_provider_imports() -> dict[str, Any]:
    """Read-only provider-readiness import validation without exposing local paths."""
    tool_name = "validate_data_provider_imports"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    validations = [
        validation.to_dict() for validation in validate_configured_provider_imports()
    ]
    needs_attention = sum(
        1
        for validation in validations
        if validation["status"] not in {"valid", "not_configured"}
    )
    configured = sum(1 for validation in validations if validation["configured"])
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "summary": {
            "total": len(validations),
            "configured": configured,
            "valid": sum(
                1 for validation in validations if validation["status"] == "valid"
            ),
            "needs_attention": needs_attention,
        },
        "validations": validations,
    }


def list_provider_profiles() -> dict[str, Any]:
    """Read-only configured provider profiles without resolved paths."""
    tool_name = "list_provider_profiles"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    profiles = [profile.to_dict() for profile in list_provider_configuration_profiles()]
    needs_attention = sum(
        1
        for profile in profiles
        if profile["last_validation_status"] not in {"valid", "not_configured"}
    )
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_provider_profile_storage_status(),
        "summary": {
            "total": len(profiles),
            "configured": sum(1 for profile in profiles if profile["configured"]),
            "needs_attention": needs_attention,
        },
        "profiles": profiles,
    }


def list_provider_source_templates() -> dict[str, Any]:
    """Read-only sanitized JSON templates for configured local provider sources."""
    tool_name = "list_provider_source_templates"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    templates = list_configured_provider_source_templates()
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "template_version": "configured-provider-json/v1",
        "provider_mode_options": ["fixture", "json_file"],
        "summary": {
            "total": len(templates),
            "market_data": sum(1 for item in templates if item["kind"] == "market_data"),
            "context": sum(1 for item in templates if item["kind"] != "market_data"),
        },
        "templates": templates,
        "next_step": "set_provider_mode_and_json_path_env",
    }


def _onboarding_setup_state(
    validation: dict[str, Any],
    readiness: dict[str, Any],
) -> str:
    if validation["missing_env"]:
        return "needs_env"
    if validation["status"] == "not_configured":
        return "optional_fixture_mode"
    if validation["status"] != "valid":
        return "needs_valid_json"

    readiness_status = readiness.get("readiness_status", "unknown")
    if readiness_status in {"pending_refresh", "stale", "retry_due"}:
        return "ready_for_refresh"
    if readiness_status == "ready":
        return "ready_for_screener"
    if readiness_status == "backoff":
        return "refresh_backoff"
    return "review_refresh_readiness"


def _onboarding_next_step(setup_state: str) -> str:
    return {
        "needs_env": "set_required_env",
        "optional_fixture_mode": "configure_provider_env",
        "needs_valid_json": "repair_configured_json",
        "ready_for_refresh": "refresh_provider_profile",
        "ready_for_screener": "ready_for_configured_screening",
        "refresh_backoff": "wait_for_retry_window",
    }.get(setup_state, "review_provider_state")


def _onboarding_operator_steps(setup_state: str) -> list[str]:
    if setup_state == "needs_env":
        return [
            "Create JSON from the matching template.",
            "Set the provider mode and JSON path env keys.",
            "Run configured import validation.",
        ]
    if setup_state == "needs_valid_json":
        return [
            "Compare the configured source against the template.",
            "Fix missing fields or unsupported wrappers.",
            "Run configured import validation again.",
        ]
    if setup_state == "ready_for_refresh":
        return [
            "Run profile refresh",
            "Review the sanitized import job result.",
            "Confirm refresh readiness before configured screeners.",
        ]
    if setup_state == "ready_for_screener":
        return [
            "Configured data is refreshed.",
            "Run configured screeners.",
            "Keep stale-data readiness visible before paper decisions.",
        ]
    if setup_state == "refresh_backoff":
        return [
            "Wait until the next attempt window.",
            "Review validation status before retrying.",
            "Run profile refresh after backoff clears.",
        ]
    return [
        "Use fixture mode or configure JSON source env keys.",
        "Create JSON from the matching template.",
        "Validate imports before refresh.",
    ]


def _safe_onboarding_actions(setup_state: str) -> list[dict[str, Any]]:
    refresh_enabled = setup_state in {
        "ready_for_refresh",
        "ready_for_screener",
        "refresh_backoff",
    }
    return [
        {
            "label": "Review JSON template",
            "tool": "list_provider_source_templates",
            "tier": _policy_payload("list_provider_source_templates")["tier"],
            "enabled": True,
        },
        {
            "label": "Validate configured import",
            "tool": "validate_data_provider_imports",
            "tier": _policy_payload("validate_data_provider_imports")["tier"],
            "enabled": True,
        },
        {
            "label": "Refresh provider profile",
            "tool": "refresh_provider_import_profile",
            "tier": _policy_payload("refresh_provider_import_profile")["tier"],
            "enabled": refresh_enabled,
        },
    ]


def list_provider_source_onboarding() -> dict[str, Any]:
    """Read-only provider-readiness onboarding for setup, validation, and refresh readiness."""
    tool_name = "list_provider_source_onboarding"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)

    templates = {
        template["provider_id"]: template
        for template in list_configured_provider_source_templates()
    }
    validations = {
        validation.provider_id: validation.to_dict()
        for validation in validate_configured_provider_imports()
    }
    profiles = {
        profile.provider_id: profile.to_dict()
        for profile in list_provider_configuration_profiles()
    }
    readiness = {
        item["provider_id"]: item
        for item in list_domain_provider_refresh_readiness()
    }
    cards = []
    for provider_id in templates:
        validation = validations[provider_id]
        profile = profiles[provider_id]
        refresh = readiness[provider_id]
        setup_state = _onboarding_setup_state(validation, refresh)
        template = templates[provider_id]
        cards.append(
            {
                "provider_id": provider_id,
                "kind": template["kind"],
                "display_name": template["display_name"],
                "provider_mode": validation["provider_mode"],
                "setup_state": setup_state,
                "recommended_next_step": _onboarding_next_step(setup_state),
                "operator_steps": _onboarding_operator_steps(setup_state),
                "required_env": validation["required_env"],
                "missing_env": validation["missing_env"],
                "template": {
                    "path_env": template["path_env"],
                    "accepted_wrappers": template["accepted_wrappers"],
                    "required_fields": template["required_fields"],
                    "optional_fields": template["optional_fields"],
                    "template_json": template["template_json"],
                },
                "validation": {
                    "status": validation["status"],
                    "configured": validation["configured"],
                    "message": validation["message"],
                    "payload_count": validation["payload_count"],
                    "sample_identifiers": validation["sample_identifiers"] or [],
                },
                "profile": {
                    "source_label": profile["source_label"],
                    "last_validation_status": profile["last_validation_status"],
                    "payload_count": profile["payload_count"],
                    "sample_identifiers": profile["sample_identifiers"],
                },
                "refresh_readiness": {
                    "status": refresh["readiness_status"],
                    "needs_refresh": refresh["needs_refresh"],
                    "latest_status": refresh["latest_status"],
                    "latest_job_id": refresh["latest_job_id"],
                    "retry_after_seconds": refresh["retry_after_seconds"],
                    "next_attempt_at": refresh["next_attempt_at"],
                },
                "safe_actions": _safe_onboarding_actions(setup_state),
            }
        )

    return {
        "status": "success",
        "policy": decision.to_dict(),
        "summary": {
            "total": len(cards),
            "configured": sum(1 for card in cards if card["validation"]["configured"]),
            "ready_for_refresh": sum(
                1 for card in cards if card["setup_state"] == "ready_for_refresh"
            ),
            "ready": sum(
                1 for card in cards if card["setup_state"] == "ready_for_screener"
            ),
            "needs_setup": sum(
                1
                for card in cards
                if card["setup_state"] in {"needs_env", "needs_valid_json"}
            ),
        },
        "onboarding_cards": cards,
        "next_step": "review_recommended_next_step_per_provider",
    }


def _safe_preview_actions(preview: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "label": "Refresh provider profile",
            "tool": "refresh_provider_import_profile",
            "tier": _policy_payload("refresh_provider_import_profile")["tier"],
            "enabled": bool(preview.get("would_write")),
        },
        {
            "label": "Validate configured import",
            "tool": "validate_data_provider_imports",
            "tier": _policy_payload("validate_data_provider_imports")["tier"],
            "enabled": True,
        },
    ]


def list_provider_import_previews() -> dict[str, Any]:
    """Read-only provider-readiness dry-run import previews before refresh without writing stores."""
    tool_name = "list_provider_import_previews"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    previews = list_domain_provider_import_previews()
    enriched_previews = [
        {
            **preview,
            "safe_actions": _safe_preview_actions(preview),
        }
        for preview in previews
    ]
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "summary": {
            "total": len(enriched_previews),
            "configured": sum(1 for preview in enriched_previews if preview["configured"]),
            "would_write": sum(1 for preview in enriched_previews if preview["would_write"]),
            "normalized_count": sum(
                int(preview["normalized_count"]) for preview in enriched_previews
            ),
            "needs_attention": sum(
                1 for preview in enriched_previews if preview["status"] == "needs_attention"
            ),
        },
        "previews": enriched_previews,
        "next_step": "review_dry_run_before_refresh",
    }


def _safe_reconciliation_actions(item: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(item.get("reconciliation_status") or "")
    refresh_enabled = status in {
        "pending_refresh",
        "source_changed",
        "store_mismatch",
    }
    return [
        {
            "label": "Review dry-run preview",
            "tool": "list_provider_import_previews",
            "tier": _policy_payload("list_provider_import_previews")["tier"],
            "enabled": True,
        },
        {
            "label": "Refresh provider profile",
            "tool": "refresh_provider_import_profile",
            "tier": _policy_payload("refresh_provider_import_profile")["tier"],
            "enabled": refresh_enabled,
        },
        {
            "label": "Review import jobs",
            "tool": "list_provider_import_jobs",
            "tier": _policy_payload("list_provider_import_jobs")["tier"],
            "enabled": True,
        },
    ]


def list_provider_import_reconciliation() -> dict[str, Any]:
    """Read-only provider-readiness reconciliation before configured screeners or paper-order readiness."""
    tool_name = "list_provider_import_reconciliation"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    reconciliations = list_domain_provider_import_reconciliation()
    enriched = [
        {
            **item,
            "safe_actions": _safe_reconciliation_actions(item),
        }
        for item in reconciliations
    ]
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "summary": {
            "total": len(enriched),
            "in_sync": sum(
                1 for item in enriched if item["reconciliation_status"] == "in_sync"
            ),
            "pending_refresh": sum(
                1
                for item in enriched
                if item["reconciliation_status"] == "pending_refresh"
            ),
            "source_changed": sum(
                1
                for item in enriched
                if item["reconciliation_status"] == "source_changed"
            ),
            "store_mismatch": sum(
                1
                for item in enriched
                if item["reconciliation_status"] == "store_mismatch"
            ),
            "needs_attention": sum(
                1
                for item in enriched
                if item["reconciliation_status"] == "needs_attention"
            ),
        },
        "reconciliations": enriched,
        "next_step": "review_reconciliation_before_configured_screening",
    }


def list_provider_import_jobs(limit: int = 20) -> dict[str, Any]:
    """Read-only provider import-refresh job summaries without payloads or paths."""
    tool_name = "list_provider_import_jobs"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    bounded_limit = max(1, min(limit, 50))
    jobs = [
        job.to_dict() for job in list_domain_provider_import_jobs(limit=bounded_limit)
    ]
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_provider_profile_storage_status(),
        "summary": {
            "total": len(jobs),
            "needs_attention": sum(
                1 for job in jobs if job["status"] == "needs_attention"
            ),
        },
        "import_jobs": jobs,
    }


def get_provider_refresh_readiness(
    stale_after_seconds: int = 86_400,
) -> dict[str, Any]:
    """Read-only provider refresh readiness, stale state, and retry backoff."""
    tool_name = "get_provider_refresh_readiness"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    bounded_stale_after = max(0, min(stale_after_seconds, 2_592_000))
    readiness = list_domain_provider_refresh_readiness(
        stale_after_seconds=bounded_stale_after,
    )
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_provider_profile_storage_status(),
        "summary": {
            "total": len(readiness),
            "ready": sum(
                1 for item in readiness if item["readiness_status"] == "ready"
            ),
            "stale": sum(
                1 for item in readiness if item["readiness_status"] == "stale"
            ),
            "needs_attention": sum(
                1
                for item in readiness
                if item["readiness_status"]
                in {"needs_attention", "backoff", "retry_due"}
            ),
        },
        "readiness": readiness,
    }


def refresh_provider_import_profile(provider_id: str) -> dict[str, Any]:
    """Draft-only provider refresh that validates one configured provider and persists sanitized status."""
    tool_name = "refresh_provider_import_profile"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name, {"provider_id": provider_id})
    try:
        job = refresh_provider_import_profile_metadata(provider_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": job.status,
        "policy": decision.to_dict(),
        "job": job.to_dict(),
        "next_step": "review_provider_import_job"
        if job.status != "completed"
        else "ready",
    }


def run_provider_refresh_schedule(
    stale_after_seconds: int = 86_400,
) -> dict[str, Any]:
    """Draft-only bounded scheduled refresh cycle for configured providers."""
    tool_name = "run_provider_refresh_schedule"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    bounded_stale_after = max(0, min(stale_after_seconds, 2_592_000))
    result = run_domain_provider_refresh_schedule(
        stale_after_seconds=bounded_stale_after,
    )
    return {
        "status": result["status"],
        "policy": decision.to_dict(),
        "storage": get_provider_profile_storage_status(),
        "schedule": result,
        "next_step": "review_provider_refresh_readiness"
        if result["status"] != "completed"
        else "ready",
    }


def get_market_data_snapshot(symbol: str) -> dict[str, Any]:
    """Read-only market data snapshot for one symbol, with safe local cache persistence."""
    tool_name = "get_market_data_snapshot"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        snapshot = get_data_provider_registry().market_data.get_snapshot(symbol)
        record_market_data_snapshot(snapshot)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_market_data_storage_status(),
        "snapshot": snapshot.to_dict(),
    }


def list_market_data_snapshots(symbol: str = "", limit: int = 20) -> dict[str, Any]:
    """Read-only cached market data snapshots without exposing storage paths."""
    tool_name = "list_market_data_snapshots"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    snapshots = list_stored_market_snapshots(symbol.strip() or None, limit)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_market_data_storage_status(),
        "snapshots": [snapshot.to_dict() for snapshot in snapshots],
    }


def get_universe_members(universe_id: str) -> dict[str, Any]:
    """Read-only universe members through the provider boundary."""
    tool_name = "get_universe_members"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        universe = get_data_provider_registry().universe.get_members(universe_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "universe": universe.to_dict(),
    }


def list_universes() -> dict[str, Any]:
    """Read-only universes with source metadata."""
    tool_name = "list_universes"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "universes": [universe.to_dict() for universe in list_fixture_universes()],
    }


def run_screener(
    universe_id: str = "fixture_nifty50",
    preset: str = "momentum",
    limit: int = 10,
) -> dict[str, Any]:
    """Read-only candidate-discovery screener with hard gates; does not draft or place orders."""
    tool_name = "run_screener"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        screener_run = run_fixture_screener(universe_id, preset, limit)
        record_screener_run(screener_run)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_market_data_storage_status(),
        "screener_run": screener_run.to_dict(),
    }


def list_screener_runs(
    universe_id: str = "",
    preset: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Read-only cached screener runs without exposing storage paths."""
    tool_name = "list_screener_runs"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    runs = list_stored_screener_runs(
        universe_id.strip() or None,
        preset.strip() or None,
        limit,
    )
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "storage": get_market_data_storage_status(),
        "screener_runs": [run.to_dict() for run in runs],
    }


def explain_candidate_evidence(
    symbol: str,
    setup: str = "",
) -> dict[str, Any]:
    """Read-only candidate-explanation after a screener candidate; does not create strategies or orders."""
    tool_name = "explain_candidate_evidence"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        factor_stack = build_factor_stack_explanation(symbol, setup or None)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "factor_stack": factor_stack.to_dict(),
    }


def search_pattern_library(
    query: str,
    tags: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    """Read-only search over public-safe pattern cards and playbooks."""
    tool_name = "search_pattern_library"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    tag_values = [tag.strip() for tag in tags.split(",") if tag.strip()]
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "patterns": [
            pattern.to_dict()
            for pattern in search_pattern_cards(query, tag_values, limit)
        ],
    }


def search_curated_research(query: str, limit: int = 5) -> dict[str, Any]:
    """Read-only curated research search over allowlisted fixture-backed documents."""
    tool_name = "search_curated_research"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name, {"query": query, "limit": limit})
    bounded_limit = max(1, min(int(limit), 20))
    try:
        hits = search_research_documents(query, limit=bounded_limit)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "retrieval": {
            "mode": "file_backed_fixture",
            "backend": "lexical",
            "vector_retrieval": "disabled",
            "source_policy": "admin_allowlist_only",
        },
        "hits": [hit.to_dict() for hit in hits],
    }


def get_pattern_playbook(pattern_id: str) -> dict[str, Any]:
    """Read-only retrieval of one versioned public-safe pattern card."""
    tool_name = "get_pattern_playbook"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        pattern = get_pattern_card(pattern_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "pattern": pattern.to_dict(),
    }


def cite_strategy_evidence(symbol: str, setup: str) -> dict[str, Any]:
    """Read-only citation-backed evidence for a paper-strategy explanation."""
    tool_name = "cite_strategy_evidence"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        evidence_pack = build_strategy_evidence_pack(symbol, setup)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "evidence_pack": evidence_pack.to_dict(),
    }


def explain_factor_stack(symbol: str, setup: str = "") -> dict[str, Any]:
    """Read-only factor stack with deterministic factors, citations, and paper-only next actions."""
    tool_name = "explain_factor_stack"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        factor_stack = build_factor_stack_explanation(symbol, setup or None)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "factor_stack": factor_stack.to_dict(),
    }


def get_recommendation_explanation(symbol: str, setup: str) -> dict[str, Any]:
    """Read-only recommendation-to-paper-order explanation before any paper order proposal."""
    tool_name = "get_recommendation_explanation"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        recommendation = build_recommendation_explanation(symbol, setup)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "recommendation": recommendation.to_dict(),
    }


def generate_paper_trading_report(
    symbol: str = "",
    setup: str = "",
) -> dict[str, Any]:
    """Read-only paper-trading-report: read-only review with accounting, positions, and redacted audit export."""
    tool_name = "generate_paper_trading_report"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        report = build_paper_trading_report(symbol, setup)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "report": report.to_dict(),
    }


def create_backtest_request(
    symbol: str,
    setup: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Draft-only recommendation-to-paper-order backtest request before paper order proposals."""
    tool_name = "create_backtest_request"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        request = create_fixture_backtest_request(
            symbol,
            setup,
            start_date,
            end_date,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "backtest_request": request.to_dict(),
    }


def list_backtest_requests() -> dict[str, Any]:
    """Read-only persisted paper backtest request history."""
    tool_name = "list_backtest_requests"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "backtest_requests": [
            request.to_dict() for request in list_fixture_backtest_requests()
        ],
    }


def get_backtest_request(request_id: str) -> dict[str, Any]:
    """Read-only persisted paper backtest request by id."""
    tool_name = "get_backtest_request"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        request = get_fixture_backtest_request(request_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "backtest_request": request.to_dict(),
    }


def get_backtest_result(request_id: str) -> dict[str, Any]:
    """Read-only deterministic simulated result for a draft backtest request."""
    tool_name = "get_backtest_result"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        result = get_fixture_backtest_result(request_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "backtest_result": result.to_dict(),
    }


def list_paper_orders() -> dict[str, Any]:
    """Read-only paper order proposals without executing or filling them."""
    tool_name = "list_paper_orders"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "orders": [order.to_dict() for order in list_fixture_paper_orders()],
    }


def list_paper_positions() -> dict[str, Any]:
    """Read-only paper positions for analysis and exposure review."""
    tool_name = "list_paper_positions"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "positions": [
            position.to_dict() for position in list_fixture_paper_positions()
        ],
    }


def list_paper_fills() -> dict[str, Any]:
    """Read-only simulated paper fills without touching any broker provider."""
    tool_name = "list_paper_fills"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "fills": [fill.to_dict() for fill in list_fixture_paper_fills()],
    }


def get_paper_portfolio_accounting() -> dict[str, Any]:
    """Read-only paper portfolio accounting after simulated fills."""
    tool_name = "get_paper_portfolio_accounting"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "accounting": get_fixture_paper_portfolio_accounting().to_dict(),
    }


def create_paper_order_proposal(
    strategy_id: str,
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "market",
    requested_price: float | None = None,
) -> dict[str, Any]:
    """Draft-only recommendation-to-paper-order proposal; requires a ready recommendation preflight and does not fill."""
    tool_name = "create_paper_order_proposal"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        readiness_preflight = build_paper_order_readiness_preflight(
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            requested_price=requested_price,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    if readiness_preflight["status"] != "ready_for_approval":
        return {
            "status": "blocked",
            "policy": decision.to_dict(),
            "readiness_preflight": readiness_preflight,
            "next_step": "resolve_recommendation_readiness_before_order",
        }
    try:
        order, approval, audit_event = create_fixture_paper_order_proposal(
            strategy_id,
            symbol,
            side,
            quantity,
            order_type,
            requested_price,
            readiness_preflight=readiness_preflight,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "pending_approval",
        "policy": decision.to_dict(),
        "readiness_preflight": readiness_preflight,
        "paper_order": order.to_dict(),
        "approval_request": approval.to_dict(),
        "audit_event": audit_event.to_dict(),
        "next_step": "human_approval_required",
    }


def approve_paper_order_simulation(
    order_id: str,
    approved_by: str,
    approval_note: str = "",
) -> dict[str, Any]:
    """Approval-required approval-gated simulated fill step that must be called before simulate_approved_paper_fill."""
    tool_name = "approve_paper_order_simulation"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name, {"order_id": order_id})
    try:
        order, approval, audit_event = approve_fixture_paper_order_simulation(
            order_id,
            approved_by,
            approval_note,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "approved",
        "policy": decision.to_dict(),
        "paper_order": order.to_dict(),
        "approval_request": approval.to_dict(),
        "audit_event": audit_event.to_dict(),
        "next_step": "simulate_approved_paper_fill",
    }


def simulate_approved_paper_fill(
    order_id: str,
    fill_price: float | None = None,
) -> dict[str, Any]:
    """Approval-required approval-gated simulated fill only after verified human approval, never live."""
    tool_name = "simulate_approved_paper_fill"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name, {"order_id": order_id})
    try:
        fill, order, position, audit_event = simulate_fixture_approved_paper_fill(
            order_id,
            fill_price,
        )
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "filled",
        "policy": decision.to_dict(),
        "paper_fill": fill.to_dict(),
        "paper_order": order.to_dict(),
        "paper_position": position.to_dict(),
        "audit_event": audit_event.to_dict(),
    }


def get_approval_queue() -> dict[str, Any]:
    """Read-only pending human approvals for paper-only actions."""
    tool_name = "get_approval_queue"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "approval_requests": [
            approval.to_dict() for approval in list_fixture_approval_queue()
        ],
    }


def get_audit_events() -> dict[str, Any]:
    """Read-only redacted paper-ledger audit events."""
    tool_name = "get_audit_events"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "audit_events": [event.to_dict() for event in list_fixture_audit_events()],
    }


def get_risk_review() -> dict[str, Any]:
    """Read-only risk state and paper-trading safety switches."""
    tool_name = "get_risk_review"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "risk_review": get_demo_risk_review().to_dict(),
    }


def draft_paper_strategy(symbol: str, rationale: str) -> dict[str, Any]:
    """Draft-only paper-trading strategy without executing any trade."""
    tool_name = "draft_paper_strategy"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        strategy = create_fixture_strategy_draft(symbol, rationale)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "strategy": strategy.to_dict(),
    }


def list_strategy_drafts() -> dict[str, Any]:
    """Read-only persisted paper strategy draft history."""
    tool_name = "list_strategy_drafts"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "source": "offline_fixture",
        "strategy_drafts": [
            strategy.to_dict() for strategy in list_fixture_strategy_drafts()
        ],
    }


def get_strategy_draft(strategy_id: str) -> dict[str, Any]:
    """Read-only persisted paper strategy draft by id."""
    tool_name = "get_strategy_draft"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    try:
        strategy = get_fixture_strategy_draft(strategy_id)
    except ValueError as exc:
        return {
            "status": "error",
            "policy": decision.to_dict(),
            "error": str(exc),
        }
    return {
        "status": "success",
        "policy": decision.to_dict(),
        "strategy": strategy.to_dict(),
    }


def create_paper_trade_proposal(strategy_id: str) -> dict[str, Any]:
    """Draft-only pending paper-trade proposal that requires human approval."""
    tool_name = "create_paper_trade_proposal"
    decision = authorize_tool_call(tool_name)
    if not decision.allowed:
        return _blocked(tool_name)
    return {
        "status": "pending_approval",
        "policy": decision.to_dict(),
        "proposal": {
            "proposal_id": f"proposal-{strategy_id}",
            "strategy_id": strategy_id,
            "mode": "paper",
            "next_step": "human_approval_required",
        },
    }


def place_live_order(symbol: str, quantity: int, side: str) -> dict[str, Any]:
    """Blocked compatibility trap for forbidden live-order requests."""
    return _blocked(
        "place_live_order",
        {"symbol": symbol, "quantity": quantity, "side": side},
    )


def get_broker_trading_token(provider: str) -> dict[str, Any]:
    """Blocked compatibility trap for broker trading-token requests."""
    return _blocked(
        "get_broker_trading_token",
        {"provider": provider, "broker_token": "never-return-this"},
    )


def assert_exposed_tools_are_safe() -> None:
    for tool_name in EXPOSED_TOOL_NAMES:
        decision = authorize_tool_call(tool_name)
        if decision.tier == ActionTier.FORBIDDEN or not decision.allowed:
            raise AssertionError(f"Unsafe exposed tool: {tool_name}")
