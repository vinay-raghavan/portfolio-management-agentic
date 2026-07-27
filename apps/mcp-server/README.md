# Portfolio MCP Server

Policy-enforced MCP tools for portfolio analysis and paper-trading workflows.

The server exposes only policy-classified model-safe tools. Current provider, screener, recommendation, reporting, strategy, backtest, and paper-ledger tools can cache read-only market snapshots, provider context records, and screener runs, track sanitized provider profiles and import-refresh jobs, import configured market/universe/factor records into structured storage, explain paper-only recommendations from evidence, provider refresh readiness, import-reconciliation gates, and history, generate read-only paper-trading reports with redacted audit exports, persist paper strategy drafts, list strategy history, draft backtest requests, list backtest history, return simulated results, create paper order proposals only after readiness preflight passes, list paper positions and fills, show accounting summaries, show approval requests, and return redacted audit events. Human approval and simulated-fill mutation APIs stay outside MCP/model-visible bundles; forbidden live-trading, broker-token, human-approval, and legacy fill helpers remain internal compatibility traps for protected API paths and deterministic tests. The package-level `portfolio_mcp` public exports mirror safe MCP exposure; internal traps live only under `portfolio_mcp.tools`.

Set `PORTFOLIO_STORAGE_BACKEND=postgres` with `PORTFOLIO_DATABASE_URL` for production-like container runs; the repository Compose file runs Alembic migrations before MCP starts. Set `PORTFOLIO_STORAGE_BACKEND=sqlite` for local/offline compatibility.
Set `PAPER_LEDGER_DB_PATH` to enable SQLite-backed strategy, backtest, and paper-ledger persistence while individual stores are ported to Postgres. Docker or Podman Compose uses `/data/paper-ledger.db` on a named volume.
Market snapshots, screener runs, universes, and factor context use tenant-scoped Postgres when `PORTFOLIO_STORAGE_BACKEND=postgres`, `PORTFOLIO_DATABASE_URL`, and `PORTFOLIO_TENANT_ID` are set. Set `MARKET_DATA_DB_PATH` only for the explicit SQLite offline fallback. Docker or Podman Compose uses `/data/market-data.db` on the same named volume for that fallback.
Set `PROVIDER_CONFIG_DB_PATH` to enable SQLite-backed provider profile and import-job metadata persistence. Docker or Podman Compose uses `/data/provider-config.db` on the same named volume.
Set `PORTFOLIO_MARKET_DATA_PROVIDER=json_file` and `PORTFOLIO_MARKET_DATA_JSON_PATH` to read configured local market snapshots through the read-only JSON adapter. Keep those JSON exports under ignored local data paths.
Set `PORTFOLIO_UNIVERSE_PROVIDER=json_file` and `PORTFOLIO_UNIVERSE_JSON_PATH` to read configured local universes through the read-only JSON adapter.
Set `PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file` and `PORTFOLIO_FUNDAMENTALS_JSON_PATH` to read configured local fundamentals through the read-only JSON adapter.
Set `PORTFOLIO_SENTIMENT_PROVIDER=json_file` and `PORTFOLIO_SENTIMENT_JSON_PATH` to read configured local sentiment through the read-only JSON adapter.
Set `PORTFOLIO_VOLATILITY_PROVIDER=json_file` and `PORTFOLIO_VOLATILITY_JSON_PATH` to read configured local volatility through the read-only JSON adapter.
Set `PORTFOLIO_MACRO_PROVIDER=json_file` and `PORTFOLIO_MACRO_JSON_PATH` to read configured local macro/regime context through the read-only JSON adapter.
The FYERS read-only connector currently exposes offline fixture tools for
connection health, quotes, OHLCV history, market depth, instrument metadata,
option chains, and normalized account snapshots: `get_fyers_connection_health`,
`get_fyers_quote`, `get_fyers_ohlcv_history`, `get_fyers_depth`,
`get_fyers_instrument_metadata`, `get_fyers_option_chain`, and
`get_fyers_account_snapshot`. These tools preserve exchange-qualified symbols,
fresh/stale/unavailable status, signed quantities, funds, and provenance while
keeping provider account data separate from the simulated paper ledger. OAuth
start/callback/status/disconnect, provider app administration, and any broker
mutation surface stay outside MCP/model-visible bundles. Unknown FYERS symbols
return unavailable/error context; they are not converted to empty holdings,
zero funds, or another provider's data.
Use `search_curated_research` to retrieve read-only curated research hits from
the repository `ResearchStore` contract. The MCP payload is fixture-backed
lexical retrieval over versioned public-safe pattern documents by default
(`PORTFOLIO_RESEARCH_STORE_BACKEND=fixture`). Set
`PORTFOLIO_RESEARCH_STORE_BACKEND=postgres` with
`PORTFOLIO_RESEARCH_TENANT_ID` and `PORTFOLIO_DATABASE_URL` to use
tenant-scoped enabled research sources and available documents through
Postgres full-text search. Misconfigured Postgres mode returns an explicit
error instead of silently falling back to fixtures. Runtime database failures
return a redacted unavailable response. The model cannot submit arbitrary URLs,
administer source allowlists, or ingest user-supplied pages through MCP.
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
