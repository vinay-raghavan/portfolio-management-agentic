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
    "apps/mcp-server",
):
    package_path = str(REPO_ROOT / relative_path)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from portfolio_mcp.tools import (  # noqa: E402
    approve_paper_order_simulation,
    create_backtest_request,
    create_pre_market_briefing,
    create_paper_order_proposal,
    create_paper_trade_proposal,
    cite_strategy_evidence,
    draft_paper_strategy,
    explain_candidate_evidence,
    explain_factor_stack,
    get_approval_queue,
    get_audit_events,
    get_backtest_request,
    get_backtest_result,
    get_data_provider_health,
    get_market_data_snapshot,
    get_pattern_playbook,
    get_paper_portfolio_accounting,
    get_portfolio_summary,
    get_research_digest,
    get_risk_review,
    get_signal_summary,
    get_strategy_draft,
    get_watchlist_snapshot,
    get_universe_members,
    list_data_providers,
    list_backtest_requests,
    list_paper_fills,
    list_paper_orders,
    list_paper_positions,
    list_strategy_drafts,
    list_universes,
    run_screener,
    run_momentum_screener,
    search_pattern_library,
    simulate_approved_paper_fill,
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
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    model_name = os.getenv("LLM_MODEL", "gemini-flash-latest")

    if provider == "gemini":
        configure_model_environment()
        return Gemini(
            model=model_name,
            retry_options=types.HttpRetryOptions(attempts=3),
        )

    try:
        from google.adk.models.lite_llm import LiteLlm
    except ImportError as exc:  # pragma: no cover - only hit for non-Gemini providers.
        raise RuntimeError(
            "Non-Gemini providers require ADK LiteLlm support and its optional dependencies."
        ) from exc

    if provider == "ollama":
        return LiteLlm(model=f"ollama_chat/{model_name}")
    if provider == "claude":
        return LiteLlm(model=f"anthropic/{model_name}")
    if provider == "openai_compatible":
        return LiteLlm(model=f"openai/{model_name}")

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


root_agent = Agent(
    name="portfolio_management_agent",
    model=build_model(),
    instruction="""You are Portfolio Management Agentic, a portfolio and paper-trading copilot.

Core rules:
- Use tools for portfolio, watchlist, signal, research, screener, strategy, and risk facts.
- For pre-market briefing requests, use the pre-market briefing tool or collect portfolio, watchlist, signal, research, and risk context before answering.
- Treat fixture data as offline-safe evidence, and clearly distinguish it from configured live data adapters.
- Use provider catalog and health tools before claiming configured data is available.
- Use screener, pattern-library, and factor-stack tools when explaining candidate setups.
- Use strategy draft history, backtest request/result tools, and paper-ledger tools for simulation review, pending approvals, and audit context.
- Keep deterministic tool outputs, citations, risk checks, and policy ahead of model intuition.
- Paper trading and simulation only.
- Never place live trades.
- Never enable live strategies.
- Never request, reveal, or use broker trading tokens.
- Draft strategies and paper orders may be created, but simulated fills require human approval first.
- Explain uncertainty, counterevidence, and risk in plain language.
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
        get_market_data_snapshot,
        get_universe_members,
        list_universes,
        run_screener,
        explain_candidate_evidence,
        search_pattern_library,
        get_pattern_playbook,
        cite_strategy_evidence,
        explain_factor_stack,
        create_backtest_request,
        list_backtest_requests,
        get_backtest_request,
        get_backtest_result,
        list_paper_orders,
        list_paper_positions,
        list_paper_fills,
        get_paper_portfolio_accounting,
        create_paper_order_proposal,
        approve_paper_order_simulation,
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
