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
from typing import Any, Mapping
from urllib.parse import urlparse

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parents[3]
for relative_path in (
    "packages/policy",
    "packages/domain",
    "packages/capabilities",
    "packages/harness",
    "packages/model-provider",
    "apps/mcp-server",
):
    package_path = str(REPO_ROOT / relative_path)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from portfolio_mcp.tools import (  # noqa: E402
    EXPOSED_TOOL_NAMES,
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
    search_curated_research,
    search_pattern_library,
    refresh_provider_import_profile,
    run_provider_refresh_schedule,
    validate_data_provider_imports,
)
from portfolio_model_provider import (  # noqa: E402
    ModelProvider,
    load_model_provider_config,
)
from portfolio_harness import (  # noqa: E402
    DeterministicRouter,
    RouteDecisionType,
)


IN_PROCESS_AGENT_TOOLS = [
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
    search_curated_research,
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
    get_approval_queue,
    get_audit_events,
    get_risk_review,
    draft_paper_strategy,
    list_strategy_drafts,
    get_strategy_draft,
    create_paper_trade_proposal,
]


PRIVATE_MCP_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "mcp-server",
    "host.containers.internal",
}


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


def build_agent_tools(env: Mapping[str, str] | None = None) -> list[Any]:
    """Build the ADK tool surface for the configured transport.

    Local tests and offline development default to the in-process adapter. The
    production-like container path sets ``AGENT_TOOL_TRANSPORT=mcp`` so ADK
    talks to the policy-enforced MCP server through streamable HTTP while
    filtering to the repository's safe MCP catalog.
    """
    env = os.environ if env is None else env
    transport = env.get("AGENT_TOOL_TRANSPORT", "in_process").strip().lower()
    if transport in {"in_process", "in-process", "local"}:
        return list(IN_PROCESS_AGENT_TOOLS)
    if transport != "mcp":
        raise RuntimeError(f"agent_tool_transport_unsupported:{transport}")

    mcp_url = env.get("AGENT_MCP_URL", "http://mcp-server:8081/mcp").strip()
    if not _is_private_mcp_url(mcp_url):
        raise RuntimeError("agent_mcp_url_not_private")

    try:
        from google.adk.tools.mcp_tool.mcp_session_manager import (
            StreamableHTTPConnectionParams,
        )
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
    except ImportError as exc:  # pragma: no cover - exercised when deps omitted.
        raise RuntimeError(
            "agent_mcp_transport_unavailable: install mcp dependency in agent-service"
        ) from exc

    return [
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(url=mcp_url),
            tool_filter=sorted(EXPOSED_TOOL_NAMES),
        )
    ]


def _is_private_mcp_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "http":
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    return hostname in PRIVATE_MCP_HOSTS or hostname.endswith(".internal")


WORKFLOW_ROUTING_GUIDE = """
Workflow routes:
- Pre-market briefing: prefer create_pre_market_briefing. If composing manually, call get_portfolio_summary, get_watchlist_snapshot, get_signal_summary, get_research_digest, and get_risk_review before answering. Return review actions only.
- Provider readiness: always call both list_data_providers and get_data_provider_health before claiming configured data is available; do not answer after the catalog alone. Use validate_data_provider_imports, list_provider_source_onboarding, list_provider_import_previews, list_provider_import_reconciliation, list_provider_import_jobs, get_provider_refresh_readiness, refresh_provider_import_profile, and run_provider_refresh_schedule for setup, preview, reconciliation, backoff, and refresh questions. Never expose file paths or credential values.
- Candidate explanation: use list_universes or get_universe_members when universe context matters, run_screener or run_momentum_screener for candidates, then call explain_candidate_evidence or explain_factor_stack before answering. If the user asks for pattern evidence, source grounding, citations, or relevant pattern sources, call cite_strategy_evidence or search_pattern_library/search_curated_research/get_pattern_playbook after the candidate/factor evidence; do not rely only on citations embedded inside factor output. Do not stop after the screener when explanation or citations are requested.
- Recommendation to paper order: always call get_recommendation_explanation before create_paper_order_proposal, even when the user starts from a backtest request. If the user asks for paper execution, create or inspect simulated backtest evidence with create_backtest_request, get_backtest_request, get_backtest_result, and list_backtest_requests, then call create_paper_order_proposal only when the readiness preflight can stay pending approval. Show get_approval_queue and get_audit_events after proposal attempts.
- Approval-gated simulated fill: approval and fill mutation must come from the verified human approval API or protected paper-execution worker, never from the model. The model cannot approve orders, simulate fills, or supply approver identity. For already-approved, externally approved, post-approval, or simulated-fill paper-state inspection, first call get_approval_queue and list_paper_orders to verify approval/order context, then list_paper_positions, list_paper_fills, get_paper_portfolio_accounting, and get_audit_events.
- Strategy and backtest history: use draft_paper_strategy for new paper strategy drafts. When a user explicitly asks to draft from screener/backtest evidence, infer a concise rationale from the observed tool evidence instead of asking a follow-up. Paper strategy draft responses must summarize the screener evidence, screener counterevidence, and returned strategy risk_notes, including elevated volatility, sizing, stop, approval, and paper-only constraints when present. Use list_strategy_drafts/get_strategy_draft for stored strategy context, and list_backtest_requests/get_backtest_request/get_backtest_result for stored simulation context.
- Paper-trading report: use generate_paper_trading_report for read-only review, accounting, positions, orders, fills, approvals, risk state, recommendation context, and redacted audit export requests. Use get_audit_events when the user asks for the raw redacted audit trail.
- Feature navigation: summarize dashboard, portfolio, watchlist, screeners, provider settings, strategy/backtest, recommendation, approvals, simulated fills, reports, risk, and audit capabilities as paper-only or read-only. Mention that configured data adapters are for data fetching only.
- Forbidden requests: for live order placement, live strategy enablement, broker trading token use, credential disclosure, provider secret disclosure, or approval bypass, refuse without calling a tool. State the safe paper-only alternative and the no live-trading fallback.
"""


ROUTER = DeterministicRouter()


def _extract_text_from_content(content: Any) -> str:
    if content is None:
        return ""
    parts = getattr(content, "parts", None) or ()
    text_parts: list[str] = []
    for part in parts:
        text = getattr(part, "text", None)
        if text:
            text_parts.append(str(text))
    return "\n".join(text_parts)


def _route_scope_model_request(
    context: Any | None = None,
    llm_request: Any | None = None,
    **kwargs: Any,
) -> LlmResponse | None:
    """Filter model-visible tools to the deterministic route bundle."""
    if context is None:
        context = kwargs.get("callback_context")
    if llm_request is None:
        llm_request = kwargs.get("llm_request")
    if llm_request is None:
        return _safe_route_response(
            error_code="portfolio_route_invalid_callback",
            message="The route-scope callback could not inspect the model request.",
            metadata={"model_visible": False, "tool_names": []},
        )
    user_text = _extract_text_from_content(getattr(context, "user_content", None))
    decision = ROUTER.route(user_text)
    if decision.decision_type == RouteDecisionType.NEEDS_CLASSIFICATION:
        decision = ROUTER.classify_read_only_request(user_text)
    tools_dict = getattr(llm_request, "tools_dict", {}) or {}
    bundle = ROUTER.tool_bundle_for(decision, exposed_tool_names=set(tools_dict))

    if decision.decision_type == RouteDecisionType.FORBIDDEN:
        llm_request.tools_dict = {}
        return _safe_route_response(
            error_code="portfolio_route_forbidden",
            message=(
                "I can’t help with live trading, live strategy enablement, "
                "broker-token use, credential disclosure, provider-secret "
                "disclosure, or approval bypass. There is no live-trading "
                "fallback in this agent. I can help with the safe paper-only "
                "workflow instead; approval and fill mutation belong to the "
                "verified human API or protected paper-execution worker."
            ),
            metadata=bundle.to_dict(),
        )

    if decision.decision_type == RouteDecisionType.HUMAN_API_REQUIRED:
        llm_request.tools_dict = {}
        return _safe_route_response(
            error_code="portfolio_human_api_required",
            message=(
                "That action must go through the authenticated human-facing API "
                f"{decision.human_api}; it is not model-visible."
            ),
            metadata=bundle.to_dict(),
        )

    if decision.decision_type == RouteDecisionType.CLARIFICATION_REQUIRED:
        llm_request.tools_dict = {}
        return _safe_route_response(
            error_code="portfolio_route_clarification_required",
            message=(
                "Please clarify whether you want research, technical analysis, "
                "provider readiness, FYERS read-only data, risk review, or "
                "paper-trading reporting. I won’t expose tools until the route "
                "is clear."
            ),
            metadata=bundle.to_dict(),
        )

    if decision.decision_type == RouteDecisionType.CAPABILITY:
        if not bundle.model_visible:
            llm_request.tools_dict = {}
            return _safe_route_response(
                error_code="portfolio_route_unavailable",
                message="This route is unavailable because its required tool bundle is incomplete.",
                metadata=bundle.to_dict(),
            )
        llm_request.tools_dict = {
            tool_name: tools_dict[tool_name]
            for tool_name in bundle.tool_names
            if tool_name in tools_dict
        }

    return None


def _route_scope_tool_call(
    tool: Any | None = None,
    args: dict[str, Any] | None = None,
    context: Any | None = None,
    **kwargs: Any,
) -> dict | None:
    del args
    if tool is None:
        tool = kwargs.get("tool")
    if context is None:
        context = kwargs.get("tool_context") or kwargs.get("context")
    user_text = _extract_text_from_content(getattr(context, "user_content", None))
    decision = ROUTER.route(user_text)
    if decision.decision_type == RouteDecisionType.NEEDS_CLASSIFICATION:
        decision = ROUTER.classify_read_only_request(user_text)
    tool_name = getattr(tool, "name", getattr(tool, "__name__", ""))

    if decision.decision_type != RouteDecisionType.CAPABILITY:
        return {
            "error": "tool_not_allowed_for_route",
            "tool": tool_name,
            "capability": decision.capability_name,
        }
    if tool_name not in decision.allowed_tools:
        return {
            "error": "tool_not_allowed_for_route",
            "tool": tool_name,
            "capability": decision.capability_name,
        }
    return None


def _safe_route_response(
    *,
    error_code: str,
    message: str,
    metadata: dict[str, object],
) -> LlmResponse:
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text=message)]),
        error_code=error_code,
        custom_metadata={"route_gate": metadata},
    )


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
- Use curated research search only for allowlisted read-only research context; do not browse or ingest arbitrary URLs.
- Use recommendation explanations to join screener, factor, strategy-history, backtest, risk, and paper-ledger evidence before proposing next steps or paper orders.
- Use strategy draft history, backtest request/result tools, and paper-ledger tools for simulation review, pending approvals, and audit context.
- Use paper-trading reports for read-only review summaries and redacted audit exports.
- Keep deterministic tool outputs, citations, risk checks, and policy ahead of model intuition.
- Paper trading and simulation only.
- Never place live trades.
- Never enable live strategies.
- Never request, reveal, or use broker trading tokens.
- Refuse forbidden live order, live strategy, broker trading token, credential disclosure, provider secret disclosure, and approval-bypass requests without calling a tool; offer the safe paper-only alternative and note the no live-trading fallback.
- Draft strategies and paper orders may be created, but approval and simulated-fill mutation stay outside the model-visible tool bundle.
- Explain uncertainty, counterevidence, and risk in plain language.

{WORKFLOW_ROUTING_GUIDE}
""",
    before_model_callback=_route_scope_model_request,
    before_tool_callback=_route_scope_tool_call,
    tools=build_agent_tools(),
)

app = App(
    root_agent=root_agent,
    name="app",
)
