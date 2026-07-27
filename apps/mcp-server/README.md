# Portfolio MCP Server

Policy-enforced MCP tools for portfolio analysis and paper-trading workflows.

The server exposes only policy-classified model-safe tools. Current provider, screener, recommendation, reporting, strategy, backtest, and paper-ledger tools can cache read-only market snapshots, provider context records, and screener runs, track sanitized provider profiles and import-refresh jobs, import configured market/universe/factor records into structured storage, explain paper-only recommendations from evidence, provider refresh readiness, import-reconciliation gates, and history, generate read-only paper-trading reports with redacted audit exports, persist paper strategy drafts, list strategy history, draft backtest requests, list backtest history, return simulated results, create paper order proposals only after readiness preflight passes, create approval-gated simulated fills after verified human approval, list paper positions and fills, show accounting summaries, show approval requests, and return redacted audit events. Human approval APIs stay outside MCP/model-visible bundles; forbidden live-trading and broker-token helpers remain unregistered compatibility traps for tests.

Set `PAPER_LEDGER_DB_PATH` to enable SQLite-backed strategy, backtest, and paper-ledger persistence. Docker or Podman Compose uses `/data/paper-ledger.db` on a named volume.
Set `MARKET_DATA_DB_PATH` to enable SQLite-backed market snapshot, provider context, and screener-run persistence. Docker or Podman Compose uses `/data/market-data.db` on the same named volume.
Set `PROVIDER_CONFIG_DB_PATH` to enable SQLite-backed provider profile and import-job metadata persistence. Docker or Podman Compose uses `/data/provider-config.db` on the same named volume.
Set `PORTFOLIO_MARKET_DATA_PROVIDER=json_file` and `PORTFOLIO_MARKET_DATA_JSON_PATH` to read configured local market snapshots through the read-only JSON adapter. Keep those JSON exports under ignored local data paths.
Set `PORTFOLIO_UNIVERSE_PROVIDER=json_file` and `PORTFOLIO_UNIVERSE_JSON_PATH` to read configured local universes through the read-only JSON adapter.
Set `PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file` and `PORTFOLIO_FUNDAMENTALS_JSON_PATH` to read configured local fundamentals through the read-only JSON adapter.
Set `PORTFOLIO_SENTIMENT_PROVIDER=json_file` and `PORTFOLIO_SENTIMENT_JSON_PATH` to read configured local sentiment through the read-only JSON adapter.
Set `PORTFOLIO_VOLATILITY_PROVIDER=json_file` and `PORTFOLIO_VOLATILITY_JSON_PATH` to read configured local volatility through the read-only JSON adapter.
Set `PORTFOLIO_MACRO_PROVIDER=json_file` and `PORTFOLIO_MACRO_JSON_PATH` to read configured local macro/regime context through the read-only JSON adapter.
The FYERS read-only connector currently exposes offline fixture tools for
connection health, quotes, and normalized account snapshots:
`get_fyers_connection_health`, `get_fyers_quote`, and
`get_fyers_account_snapshot`. These tools preserve exchange-qualified symbols,
fresh/stale/unavailable status, signed quantities, funds, and provenance while
keeping provider account data separate from the simulated paper ledger. OAuth
start/callback/status/disconnect, provider app administration, and any broker
mutation surface stay outside MCP/model-visible bundles. Unknown FYERS symbols
return unavailable/error context; they are not converted to empty holdings,
zero funds, or another provider's data.
Use `validate_data_provider_imports` to validate configured local JSON files before running provider-backed workflows. It reports validation status and sample identifiers without exposing local paths or credential values.
Use `list_provider_source_templates` to retrieve synthetic, adapter-valid JSON
templates and accepted wrapper names for each configured source kind without
returning provider data or local paths. Use `list_provider_source_onboarding`
to review each configured source's template, validation state, setup gaps,
refresh readiness, and safe next actions in one read-only payload. Use
`list_provider_import_previews` to dry-run configured imports before refresh;
it reports normalized counts, sample identifiers, target stores, warnings, and
would-write status without initializing stores or writing cache rows. Use
`list_provider_import_reconciliation` to compare preview counts, latest refresh
job counts, and stored row counts before configured screeners depend on cached
data. Screeners and recommendations also use reconciliation as a confidence and
paper-readiness gate; source-changed, store-mismatch, or needs-attention states
remove paper-order next actions until refresh/reconciliation is reviewed. Use
`list_provider_profiles`, `get_provider_refresh_readiness`,
`refresh_provider_import_profile`, `run_provider_refresh_schedule`, and
`list_provider_import_jobs` to review provider readiness and sanitized refresh
execution. Configured refreshes can import normalized market, universe,
fundamentals, sentiment, volatility, and macro records into structured local
storage. Scheduled refresh orchestration reports ready, stale, retry-due, and
backoff state. Refresh jobs do not store resolved paths or raw provider payloads.
`create_paper_order_proposal` builds the same readiness evidence into a
`paper-order-readiness-preflight/v1` snapshot before draft creation. Blocked
preflights return no paper order; ready preflights are stored on the order and
redacted audit event for human approval review.

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
