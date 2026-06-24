from __future__ import annotations

import os

from .tools import (
    approve_paper_order_simulation,
    assert_exposed_tools_are_safe,
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

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only before MCP deps are installed.
    FastMCP = None  # type: ignore[assignment]


def _mcp_port() -> int:
    return int(os.getenv("MCP_PORT", "8081"))


def build_server():
    """Build the portfolio MCP server.

    Forbidden compatibility traps are intentionally not registered as MCP tools.
    They remain available in `tools.py` for deterministic policy tests.
    """
    assert_exposed_tools_are_safe()
    if FastMCP is None:
        raise RuntimeError("The mcp package is required to run the MCP server.")

    server = FastMCP(
        "portfolio-management-agentic",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=_mcp_port(),
        streamable_http_path=os.getenv("MCP_STREAMABLE_HTTP_PATH", "/mcp"),
        sse_path=os.getenv("MCP_SSE_PATH", "/sse"),
        stateless_http=os.getenv("MCP_STATELESS_HTTP", "true").lower() == "true",
    )
    server.tool()(get_portfolio_summary)
    server.tool()(get_watchlist_snapshot)
    server.tool()(get_signal_summary)
    server.tool()(get_research_digest)
    server.tool()(create_pre_market_briefing)
    server.tool()(run_momentum_screener)
    server.tool()(list_data_providers)
    server.tool()(get_data_provider_health)
    server.tool()(validate_data_provider_imports)
    server.tool()(list_provider_profiles)
    server.tool()(list_provider_source_templates)
    server.tool()(list_provider_source_onboarding)
    server.tool()(list_provider_import_jobs)
    server.tool()(get_provider_refresh_readiness)
    server.tool()(refresh_provider_import_profile)
    server.tool()(run_provider_refresh_schedule)
    server.tool()(get_market_data_snapshot)
    server.tool()(list_market_data_snapshots)
    server.tool()(get_universe_members)
    server.tool()(list_universes)
    server.tool()(run_screener)
    server.tool()(list_screener_runs)
    server.tool()(explain_candidate_evidence)
    server.tool()(search_pattern_library)
    server.tool()(get_pattern_playbook)
    server.tool()(cite_strategy_evidence)
    server.tool()(explain_factor_stack)
    server.tool()(get_recommendation_explanation)
    server.tool()(generate_paper_trading_report)
    server.tool()(create_backtest_request)
    server.tool()(list_backtest_requests)
    server.tool()(get_backtest_request)
    server.tool()(get_backtest_result)
    server.tool()(list_paper_orders)
    server.tool()(list_paper_positions)
    server.tool()(list_paper_fills)
    server.tool()(get_paper_portfolio_accounting)
    server.tool()(create_paper_order_proposal)
    server.tool()(approve_paper_order_simulation)
    server.tool()(simulate_approved_paper_fill)
    server.tool()(get_approval_queue)
    server.tool()(get_audit_events)
    server.tool()(get_risk_review)
    server.tool()(draft_paper_strategy)
    server.tool()(list_strategy_drafts)
    server.tool()(get_strategy_draft)
    server.tool()(create_paper_trade_proposal)
    return server


server = build_server() if FastMCP is not None else None


def main() -> None:
    if server is None:
        raise SystemExit("Install MCP dependencies before running the server.")
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise SystemExit(f"Unsupported MCP_TRANSPORT: {transport}")
    server.run(transport=transport)


if __name__ == "__main__":
    main()
