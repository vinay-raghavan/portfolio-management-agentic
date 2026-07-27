from __future__ import annotations

import json
from pathlib import Path


WEB_ROOT = Path("apps/web")


def test_web_console_package_declares_build_and_preview_scripts() -> None:
    package = json.loads((WEB_ROOT / "package.json").read_text())

    assert package["private"] is True
    assert package["scripts"]["build"] == "vite build"
    assert package["scripts"]["preview"] == "vite preview --host 0.0.0.0 --port 3000"
    assert "react" in package["dependencies"]
    assert "vite" in package["devDependencies"]


def test_web_console_has_product_surfaces_and_no_live_trade_copy() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    for expected in (
        "Run pre-market briefing",
        "Review approval queue",
        "Generate paper report",
        "Focused workflow pages",
        "Screener preset",
        "Draft paper strategy",
        "Create backtest request",
        "Create paper order proposal",
        "Approve simulation",
        "Simulate paper fill",
        "Provider health",
        "Provider settings",
        "Provider profiles",
        "Import validation",
        "Import jobs",
        "Configured files",
        "Refresh profile",
        "Run full refresh",
        "Refresh readiness",
        "Backoff state",
        "Import gate",
        "Paper gate blocked",
        "Next attempt",
        "Last validation",
        "Needs attention",
        "Screener candidates",
        "Paper Ledger",
        "Live trading blocked",
    ):
        assert expected in source

    assert "Place live order" not in source
    assert "broker token" not in source.lower()


def test_web_console_exposes_provider_refresh_cycle_controls() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "/console/workflows/provider-profiles/refresh-schedule" in source
    assert "runProviderRefreshSchedule" in source
    assert "ProviderRefreshReadiness" in source
    assert "provider_refresh_readiness" in source
    assert "provider_refresh_actions" in source
    assert "retry_after_seconds" in source
    assert "next_attempt_at" in source
    assert "backoff" in source


def test_web_console_exposes_configured_provider_source_management() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "ProviderSourceSetup" in source
    assert "Source setup" in source
    assert "Required env keys" in source
    assert "Active mode" in source
    assert "Setup gaps" in source
    assert "required_env" in source
    assert "missing_env" in source
    assert "provider_mode" in source
    assert "source_label" in source


def test_web_console_exposes_provider_source_schema_guidance() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "ProviderSourceTemplates" in source
    assert "Schema guidance" in source
    assert "JSON template" in source
    assert "Accepted wrappers" in source
    assert "Required fields" in source
    assert "provider_source_templates" in source
    assert "template_json" in source
    assert "accepted_wrappers" in source


def test_web_console_exposes_guided_provider_source_onboarding() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "ProviderSourceOnboarding" in source
    assert "Onboarding flow" in source
    assert "Safe next step" in source
    assert "Validation" in source
    assert "Refresh readiness" in source
    assert "Operator steps" in source
    assert "provider_source_onboarding" in source
    assert "recommended_next_step" in source
    assert "safe_actions" in source


def test_web_console_exposes_provider_import_dry_run_previews() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "ProviderImportPreviews" in source
    assert "Dry-run preview" in source
    assert "Target store" in source
    assert "Normalized count" in source
    assert "Would write" in source
    assert "provider_import_previews" in source
    assert "sample_identifiers" in source
    assert "would_write" in source


def test_web_console_exposes_provider_import_reconciliation() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "ProviderImportReconciliation" in source
    assert "Import reconciliation" in source
    assert "Stored rows" in source
    assert "Latest job count" in source
    assert "Preview count" in source
    assert "provider_import_reconciliation" in source
    assert "reconciliation_status" in source
    assert "stored_count" in source


def test_web_console_exposes_paper_order_readiness_preflight() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    assert "PaperPreflightSummary" in source
    assert "PaperOrderList" in source
    assert "Readiness preflight" in source
    assert "Provider reconciliation" in source
    assert "Provider refresh" in source
    assert "Submitted strategy" in source
    assert "Human approval" in source
    assert "Blocking reasons" in source
    assert "readiness_preflight" in source
    assert "paper_order_readiness" in source
    assert "blocking_reasons" in source
    assert "submitted_strategy_gate" in source
    assert "proposalSuffix" not in source
    assert "-proposal-" not in source


def test_web_console_does_not_send_approver_identity_in_approval_body() -> None:
    source = (WEB_ROOT / "src" / "App.tsx").read_text()

    approval_call = source.split("runApproval", 1)[1].split("const runSimulatedFill", 1)[0]

    assert "approval_note" in approval_call
    assert "approved_by" not in approval_call


def test_web_console_uses_rounded_widget_design_contract() -> None:
    styles = (WEB_ROOT / "src" / "styles.css").read_text()
    rounded_refinement = styles.split("/* Rounded widget refinement", 1)[1]

    assert "--radius-lg: 64px;" in styles
    assert "--radius-xl: 84px;" in styles
    assert "--widget-radius: var(--radius-lg);" in styles
    assert "--widget-radius-soft: var(--radius-xl);" in styles
    assert "--control-radius: 36px;" in styles
    assert "border-radius: var(--widget-radius-soft);" in rounded_refinement
    assert ".candidate-table" in rounded_refinement
    assert ".flow-step i::after" in styles
    assert "border-radius: var(--widget-radius);" in rounded_refinement
    assert ".app-shell[data-theme=\"light\"] .selected-workflow" in rounded_refinement
    assert ".topbar," in rounded_refinement
    assert ".page-strip" in rounded_refinement
    assert "border-left-width: 1px;" in rounded_refinement
    assert ".action-chip-list span" in rounded_refinement
    assert "border-left: 9px solid" not in styles
    assert ".selected-workflow" in rounded_refinement
    assert "border-radius: 0 0" not in rounded_refinement


def test_web_console_uses_uniform_widget_rounding_for_rows_and_controls() -> None:
    styles = (WEB_ROOT / "src" / "styles.css").read_text()
    rounded_refinement = styles.split("/* Rounded widget refinement", 1)[1]

    soft_widget_selectors = (
        ".index-strip div",
        ".table-row",
        ".preflight-grid div",
        ".preflight-policy",
        ".preflight-blockers",
        ".selected-workflow",
        ".action-chip-list span",
        ".setup-gap-list span",
    )
    control_selectors = (
        ".segment-button",
        ".command-button",
        ".env-chip-list code",
        ".template-row pre",
    )

    for selector in soft_widget_selectors:
        assert selector in rounded_refinement
    for selector in control_selectors:
        assert selector in rounded_refinement

    assert ".index-strip div,\n.workflow-button" in rounded_refinement
    assert ".app-shell[data-theme=\"light\"] .index-strip div" in rounded_refinement
    assert ".table-row {\n  grid-template-columns" in rounded_refinement
    assert ".metric-tile.good,\n.metric-tile.warn" in rounded_refinement
    assert "border-left-width: 1px;" in rounded_refinement


def test_web_console_uses_pillowed_widget_polish_for_both_themes() -> None:
    styles = (WEB_ROOT / "src" / "styles.css").read_text()
    polish = styles.split("/* Rounded cockpit polish", 1)[1]

    for expected in (
        "--widget-surface-halo",
        "--widget-inset-radius",
        "background-clip: padding-box;",
        ".workflow-list",
        ".provider-list",
        ".validation-stack",
        ".detail-list",
        ".app-shell[data-theme=\"light\"] .workflow-list",
        "@media (max-width: 760px)",
        "--widget-radius-soft: 46px;",
    ):
        assert expected in polish

    assert "--widget-inset-radius: max(24px, calc(var(--widget-radius) - 18px));" in polish
    assert "border-radius: var(--widget-inset-radius);" in polish
    assert "border-radius: 4px" not in polish
    assert "border-radius: 0" not in polish


def test_compose_exposes_web_console_without_secrets() -> None:
    compose = Path("docker-compose.yml").read_text()

    assert "web:" in compose
    assert "apps/web/Dockerfile" in compose
    assert '"3000:3000"' in compose
    assert "VITE_AGENT_API_URL" in compose
    assert "GOOGLE_API_KEY" not in compose.split("web:", 1)[1]
    assert "ANTHROPIC_API_KEY" not in compose.split("web:", 1)[1]
