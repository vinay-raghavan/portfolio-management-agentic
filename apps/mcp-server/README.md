# Portfolio MCP Server

Policy-enforced MCP tools for portfolio analysis and paper-trading workflows.

The server exposes only policy-classified tools. Current provider, screener, recommendation, reporting, strategy, backtest, and paper-ledger tools can cache read-only market snapshots and screener runs, explain paper-only recommendations from evidence and history, generate read-only paper-trading reports with redacted audit exports, persist paper strategy drafts, list strategy history, draft backtest requests, list backtest history, return simulated results, create pending paper order proposals, approve paper simulations, create approval-gated simulated fills, list paper positions and fills, show accounting summaries, show approval requests, and return redacted audit events. Forbidden live-trading and broker-token helpers remain unregistered compatibility traps for tests.

Set `PAPER_LEDGER_DB_PATH` to enable SQLite-backed strategy, backtest, and paper-ledger persistence. Docker or Podman Compose uses `/data/paper-ledger.db` on a named volume.
Set `MARKET_DATA_DB_PATH` to enable SQLite-backed market snapshot and screener-run persistence. Docker or Podman Compose uses `/data/market-data.db` on the same named volume.

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
