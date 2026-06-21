from __future__ import annotations

from .tools import (
    assert_exposed_tools_are_safe,
    create_paper_trade_proposal,
    draft_paper_strategy,
    get_portfolio_summary,
    get_risk_review,
    run_momentum_screener,
)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - exercised only before MCP deps are installed.
    FastMCP = None  # type: ignore[assignment]


def build_server():
    """Build the portfolio MCP server.

    Forbidden compatibility traps are intentionally not registered as MCP tools.
    They remain available in `tools.py` for deterministic policy tests.
    """
    assert_exposed_tools_are_safe()
    if FastMCP is None:
        raise RuntimeError("The mcp package is required to run the MCP server.")

    server = FastMCP("portfolio-management-agentic")
    server.tool()(get_portfolio_summary)
    server.tool()(run_momentum_screener)
    server.tool()(get_risk_review)
    server.tool()(draft_paper_strategy)
    server.tool()(create_paper_trade_proposal)
    return server


server = build_server() if FastMCP is not None else None


if __name__ == "__main__":
    if server is None:
        raise SystemExit("Install MCP dependencies before running the server.")
    server.run()

