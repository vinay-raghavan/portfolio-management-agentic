# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parents[3]
for relative_path in (
    "packages/policy",
    "packages/domain",
    "packages/model-provider",
    "apps/mcp-server",
):
    package_path = str(REPO_ROOT / relative_path)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from portfolio_mcp.tools import (  # noqa: E402
    create_backtest_request,
    create_pre_market_briefing,
    create_paper_order_proposal,
    create_paper_trade_proposal,
    cite_strategy_evidence,
    draft_paper_strategy,
    explain_candidate_evidence,
    explain_factor_stack,
    generate_paper_trading_report,
    get_approval_queue,
    get_audit_events,
    get_backtest_request,
    get_backtest_result,
    get_data_provider_health,
    get_market_data_snapshot,
    get_pattern_playbook,
    get_paper_portfolio_accounting,
    get_portfolio_summary,
    get_provider_refresh_readiness,
    get_recommendation_explanation,
    get_research_digest,
    get_risk_review,
    get_signal_summary,
    get_strategy_draft,
    get_watchlist_snapshot,
    get_universe_members,
    list_data_providers,
    list_provider_import_previews,
    list_provider_import_reconciliation,
    list_provider_import_jobs,
    list_provider_profiles,
    list_provider_source_onboarding,
    list_provider_source_templates,
    list_market_data_snapshots,
    list_backtest_requests,
    list_paper_fills,
    list_paper_orders,
    list_paper_positions,
    list_screener_runs,
    list_strategy_drafts,
    list_universes,
    run_screener,
    run_momentum_screener,
    search_pattern_library,
    simulate_approved_paper_fill,
    refresh_provider_import_profile,
    run_provider_refresh_schedule,
    validate_data_provider_imports,
)
from portfolio_model_provider import (  # noqa: E402
    ModelProvider,
    load_model_provider_config,
)


def configure_model_environment() -> None:
    """Configure model auth mode without doing credential discovery at import."""
    if os.getenv("GOOGLE_API_KEY"):
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")
        return

    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    if os.getenv("GOOGLE_CLOUD_PROJECT"):
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
    else:
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")


def build_model():
    """Build the configured model adapter for ADK.

    Gemini is the default capstone provider. Other providers are routed through
    ADK's LiteLlm adapter when that optional dependency is installed.
    """
    config = load_model_provider_config(os.environ)

    if config.provider == ModelProvider.GEMINI:
        configure_model_environment()
        return Gemini(
            model=config.model,
            retry_options=types.HttpRetryOptions(attempts=3),
        )

    try:
        from google.adk.models.lite_llm import LiteLlm
    except ImportError as exc:  # pragma: no cover - only hit for non-Gemini providers.
        raise RuntimeError(
            "Non-Gemini providers require ADK LiteLlm support and its optional dependencies."
        ) from exc

    if config.provider == ModelProvider.OLLAMA:
        if config.base_url:
            os.environ.setdefault("OLLAMA_API_BASE", config.base_url)
        return LiteLlm(model=f"ollama_chat/{config.model}")
    if config.provider == ModelProvider.CLAUDE:
        return LiteLlm(model=f"anthropic/{config.model}")
    if config.provider == ModelProvider.OPENAI_COMPATIBLE:
        if config.base_url:
            os.environ.setdefault("OPENAI_API_BASE", config.base_url)
        return LiteLlm(model=f"openai/{config.model}")

    raise ValueError(f"Unsupported LLM_PROVIDER: {config.provider.value}")


WORKFLOW_ROUTING_GUIDE = """
Workflow routes:
- Pre-market briefing: prefer create_pre_market_briefing. If composing manually, call get_portfolio_summary, get_watchlist_snapshot, get_signal_summary, get_research_digest, and get_risk_review before answering. Return review actions only.
- Provider readiness: call list_data_providers and get_data_provider_health before claiming configured data is available. Use validate_data_provider_imports, list_provider_source_onboarding, list_provider_import_previews, list_provider_import_reconciliation, list_provider_import_jobs, get_provider_refresh_readiness, refresh_provider_import_profile, and run_provider_refresh_schedule for setup, preview, reconciliation, backoff, and refresh questions. Never expose file paths or credential values.
- Candidate explanation: use list_universes or get_universe_members when universe context matters, run_screener or run_momentum_screener for candidates, explain_candidate_evidence for factor details, search_pattern_library/get_pattern_playbook/cite_strategy_evidence for citations, and explain_factor_stack for the final evidence stack.
- Recommendation to paper order: call get_recommendation_explanation first. If the user asks for paper execution, create or inspect simulated backtest evidence with create_backtest_request, get_backtest_request, get_backtest_result, and list_backtest_requests, then call create_paper_order_proposal only when the readiness preflight can stay pending approval. Show get_approval_queue and get_audit_events after proposal attempts.
- Approval-gated simulated fill: approval must come from the verified human approval API before any simulated fill. The model cannot approve orders or supply approver identity. Use get_approval_queue, simulate_approved_paper_fill, list_paper_orders, list_paper_positions, list_paper_fills, get_paper_portfolio_accounting, and get_audit_events when the user explicitly asks to inspect approved simulations.
- Strategy and backtest history: use draft_paper_strategy for new paper strategy drafts, list_strategy_drafts/get_strategy_draft for stored strategy context, and list_backtest_requests/get_backtest_request/get_backtest_result for stored simulation context.
- Paper-trading report: use generate_paper_trading_report for read-only review, accounting, positions, orders, fills, approvals, risk state, recommendation context, and redacted audit export requests. Use get_audit_events when the user asks for the raw redacted audit trail.
- Feature navigation: summarize dashboard, portfolio, watchlist, screeners, provider settings, strategy/backtest, recommendation, approvals, simulated fills, reports, risk, and audit capabilities as paper-only or read-only. Mention that configured data adapters are for data fetching only.
- Forbidden requests: for live order placement, live strategy enablement, broker trading token use, credential disclosure, provider secret disclosure, or approval bypass, refuse without calling a tool. State the safe paper-only alternative and the no live-trading fallback.
"""


root_agent = Agent(
    name="portfolio_management_agent",
    model=build_model(),
    instruction=f"""You are TradePilot Sentinel, a trading workflow and portfolio risk copilot.

Core rules:
- Use tools for portfolio, watchlist, signal, research, screener, strategy, and risk facts.
- For pre-market briefing requests, use the pre-market briefing tool or collect portfolio, watchlist, signal, research, and risk context before answering.
- Treat fixture data as offline-safe evidence, and clearly distinguish it from configured live data adapters.
- Use provider catalog, health, and import-validation tools before claiming configured data is available.
- Use provider source onboarding, dry-run import previews, import reconciliation, profiles, source templates, refresh readiness, and import-job history to explain configured local data readiness without exposing file paths.
- Use market snapshot and screener-run history tools when users ask what data has been cached or already screened.
- Use screener, pattern-library, and factor-stack tools when explaining candidate setups.
- Use recommendation explanations to join screener, factor, strategy-history, backtest, risk, and paper-ledger evidence before proposing next steps.
- Use strategy draft history, backtest request/result tools, and paper-ledger tools for simulation review, pending approvals, and audit context.
- Use paper-trading reports for read-only review summaries and redacted audit exports.
- Keep deterministic tool outputs, citations, risk checks, and policy ahead of model intuition.
- Paper trading and simulation only.
- Never place live trades.
- Never enable live strategies.
- Never request, reveal, or use broker trading tokens.
- Refuse forbidden live order, live strategy, broker trading token, credential disclosure, provider secret disclosure, and approval-bypass requests without calling a tool; offer the safe paper-only alternative and note the no live-trading fallback.
- Draft strategies and paper orders may be created, but simulated fills require human approval first.
- Explain uncertainty, counterevidence, and risk in plain language.

{WORKFLOW_ROUTING_GUIDE}
""",
    tools=[
        get_portfolio_summary,
        get_watchlist_snapshot,
        get_signal_summary,
        get_research_digest,
        create_pre_market_briefing,
        run_momentum_screener,
        list_data_providers,
        get_data_provider_health,
        validate_data_provider_imports,
        list_provider_profiles,
        list_provider_source_templates,
        list_provider_source_onboarding,
        list_provider_import_previews,
        list_provider_import_reconciliation,
        list_provider_import_jobs,
        get_provider_refresh_readiness,
        refresh_provider_import_profile,
        run_provider_refresh_schedule,
        get_market_data_snapshot,
        list_market_data_snapshots,
        get_universe_members,
        list_universes,
        run_screener,
        list_screener_runs,
        explain_candidate_evidence,
        search_pattern_library,
        get_pattern_playbook,
        cite_strategy_evidence,
        explain_factor_stack,
        get_recommendation_explanation,
        generate_paper_trading_report,
        create_backtest_request,
        list_backtest_requests,
        get_backtest_request,
        get_backtest_result,
        list_paper_orders,
        list_paper_positions,
        list_paper_fills,
        get_paper_portfolio_accounting,
        create_paper_order_proposal,
        simulate_approved_paper_fill,
        get_approval_queue,
        get_audit_events,
        get_risk_review,
        draft_paper_strategy,
        list_strategy_drafts,
        get_strategy_draft,
        create_paper_trade_proposal,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
