from __future__ import annotations

import asyncio

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
