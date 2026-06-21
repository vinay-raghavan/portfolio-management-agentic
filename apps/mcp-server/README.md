# Portfolio MCP Server

Policy-enforced MCP tools for portfolio analysis and paper-trading workflows.

The server exposes only safe read-only and draft-only tools. Forbidden live-trading and broker-token helpers remain unregistered compatibility traps for tests.

## Local Runtime

```bash
uv sync
MCP_TRANSPORT=streamable-http MCP_HOST=0.0.0.0 MCP_PORT=8081 uv run python -m portfolio_mcp.server
```

Supported transports:

- `stdio`
- `sse`
- `streamable-http`

Docker Compose or Podman Compose uses `streamable-http` on port `8081`.
