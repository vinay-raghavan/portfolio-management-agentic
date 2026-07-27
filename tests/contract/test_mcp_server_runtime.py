from __future__ import annotations

import asyncio

import portfolio_mcp
from portfolio_mcp import server as mcp_server
from portfolio_mcp.tools import EXPOSED_TOOL_NAMES


def test_mcp_server_builds_streamable_http_runtime(monkeypatch) -> None:
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "8081")
    monkeypatch.setenv("MCP_STREAMABLE_HTTP_PATH", "/mcp")
    monkeypatch.setenv("MCP_STATELESS_HTTP", "true")

    server = mcp_server.build_server()

    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 8081
    assert server.settings.streamable_http_path == "/mcp"
    assert server.settings.stateless_http is True


def test_mcp_server_registers_only_safe_tools() -> None:
    server = mcp_server.build_server()
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert EXPOSED_TOOL_NAMES == tool_names
    assert "place_live_order" not in tool_names
    assert "get_broker_trading_token" not in tool_names
    assert "approve_paper_order_simulation" not in tool_names
    assert "simulate_approved_paper_fill" not in tool_names


def test_mcp_package_public_exports_exclude_human_approval_fill_and_forbidden_traps() -> None:
    public_exports = set(portfolio_mcp.__all__)

    assert EXPOSED_TOOL_NAMES <= public_exports
    assert "approve_paper_order_simulation" not in public_exports
    assert "simulate_approved_paper_fill" not in public_exports
    assert "place_live_order" not in public_exports
    assert "get_broker_trading_token" not in public_exports
    assert not hasattr(portfolio_mcp, "approve_paper_order_simulation")
    assert not hasattr(portfolio_mcp, "simulate_approved_paper_fill")
    assert not hasattr(portfolio_mcp, "place_live_order")
    assert not hasattr(portfolio_mcp, "get_broker_trading_token")
