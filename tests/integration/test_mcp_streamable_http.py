from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from portfolio_mcp.tools import EXPOSED_TOOL_NAMES


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def mcp_streamable_http_server() -> Iterator[str]:
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            "apps/mcp-server",
            "packages/domain",
            "packages/policy",
            env.get("PYTHONPATH", ""),
        ]
    )
    env["MCP_TRANSPORT"] = "streamable-http"
    env["MCP_HOST"] = "127.0.0.1"
    env["MCP_PORT"] = str(port)

    process = subprocess.Popen(
        [sys.executable, "-m", "portfolio_mcp.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


async def _list_tool_names(url: str) -> set[str]:
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return {tool.name for tool in result.tools}


def test_mcp_streamable_http_exposes_only_safe_tools(
    mcp_streamable_http_server: str,
) -> None:
    deadline = time.monotonic() + 10
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            tool_names = asyncio.run(_list_tool_names(mcp_streamable_http_server))
            break
        except Exception as exc:  # pragma: no cover - retry loop is timing-dependent.
            last_error = exc
            time.sleep(0.25)
    else:
        raise AssertionError("MCP streamable HTTP server did not become ready.") from last_error

    assert tool_names == EXPOSED_TOOL_NAMES
    assert "place_live_order" not in tool_names
    assert "get_broker_trading_token" not in tool_names
    assert "approve_paper_order_simulation" not in tool_names
    assert "simulate_approved_paper_fill" not in tool_names
