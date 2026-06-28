# Portfolio Management Agentic

Agentic portfolio research and paper-trading workbench for the Kaggle AI Agents capstone.

This is a standalone repository boundary. Implementation should use documented API contracts, bounded tools, configured data adapters, offline-safe fixtures, and explicit safety policy.

## Current State

- ADK prototype scaffolded in `apps/agent-service`.
- Platform-neutral policy, domain, model-provider, and agent-platform contracts started.
- MCP-style safe portfolio tools started in `apps/mcp-server` with streamable HTTP runtime support.
- Pre-market briefing workflow composes synthetic portfolio, watchlist, signal, research, and risk context.
- Product data foundation adds fixture/configured universes, configured fundamentals, sentiment, volatility, macro/regime context, deterministic screener runs, provider refresh readiness and import-reconciliation evidence, pattern-card retrieval, citation-backed strategy evidence, and factor-stack explanations.
- Provider adapter contracts expose fixture defaults, configured read-only JSON market-data, universe, fundamentals, sentiment, volatility, and macro adapters, provider catalog, health, import validation, market snapshot, and universe-member tools.
- Recommendation explanations join screener/factor evidence, provider refresh readiness, import-reconciliation gates, strategy history, backtest history, risk gates, paper-ledger state, citations, and allowed next actions into one read-only decision record.
- Paper-trading reports return read-only review summaries with redacted audit exports for paper orders, approvals, fills, accounting, risk state, and optional recommendation context.
- Strategy, backtest, and paper-ledger contracts persist paper strategy drafts and backtest request history, return offline results, require a ready recommendation preflight before paper order proposals enter approval, approve paper simulations, create approval-gated simulated fills, update paper positions/accounting, expose approval queues, and emit redacted audit events with the readiness snapshot.
- Market-data persistence stores fixture/configured-provider market snapshots, provider context snapshots, and screener runs in the same JSON payload shape returned by the tools when `MARKET_DATA_DB_PATH` is configured.
- Provider configuration profiles and import-refresh jobs persist sanitized validation and execution summaries when `PROVIDER_CONFIG_DB_PATH` is configured. Configured source templates, guided onboarding, dry-run import previews, and import reconciliation provide synthetic, adapter-valid JSON shapes, live validation state, setup gaps, refresh readiness, normalized counts, target stores, stored row counts, and safe next actions for market, universe, fundamentals, sentiment, volatility, and macro inputs. Configured refreshes can also import normalized records into the SQLite data store behind `MARKET_DATA_DB_PATH`. Scheduled refresh orchestration reports ready, stale, retry-due, and backoff readiness without resolved local file paths or raw provider payloads.
- Model-backed eval readiness is credential-gated through `scripts/run_agent_evals.py`, which preflights `agents-cli eval generate` and `agents-cli eval grade` without printing secret values.
- Web console is available in `apps/web`, backed by `/console/overview` and `/console/workflows` endpoints. It includes focused pages for screeners, strategy/backtest review, paper approvals, reports, and provider settings with guided configured-source onboarding, required env-key visibility, active adapter modes, setup-gap feedback, schema/template guidance, configured-file validation, dry-run import previews, import reconciliation, import-gate visibility on decision pages, provider profiles, refresh readiness, full-refresh controls, per-provider backoff state, and import-job feedback.
- SQLite-backed paper-ledger persistence is available through `PAPER_LEDGER_DB_PATH`; SQLite-backed market-data, provider-context, and screener-run persistence is available through `MARKET_DATA_DB_PATH`; provider profile and import-job metadata persistence is available through `PROVIDER_CONFIG_DB_PATH`. Compose mounts a named volume at `/data` for shared local runtime state.
- Docker or Podman Compose runs the agent service, MCP server, web console, and optional Ollama profile.
- No copied portfolio data.
- No broker trading credentials.
- No live trading.
- Gitflow-style branching is enabled: `main` is release-only, `develop` is the integration branch, and active work happens on topic branches from `develop`.

## Repository Intent

The project will become a functioning agentic portfolio research and paper-trading tool. The Kaggle demo is one evidence path, not the product boundary. The system should support real configured data providers, deterministic analysis, explainable strategy evidence, a persistent paper-trading ledger, and policy-controlled agent workflows while forbidding live order placement.

## North Star

The end goal is a full agentic portfolio and paper-trading web application. It should cover dashboard, portfolio, watchlist, screeners, research, signals, strategies, backtests, risk, paper trades, reports, and settings while making every major capability reachable through agent workflows.

Source-system scripts and workflows are reference material only. Useful logic should be rewritten as typed domain functions, MCP tools, scheduled jobs, RAG pattern cards, evals, or UI flows with offline-safe fixtures and policy tests. Live-account assumptions, broker-token access, direct execution paths, and local state should not be imported.

Primary constraints:

- Paper trading and simulation only.
- All major app features should be reachable through agent workflows.
- Broker/provider credentials may be used only for data fetching, never live order execution.
- Private source, local paths, and real financial data are excluded from the repo.
- Docker or Podman Compose is the first deployment target.
- Gemini is the first model provider, but the design must support other hosted and local providers such as Claude, OpenAI-compatible APIs, and Ollama later.
- ADK is the first capstone runtime, but the reusable tool, policy, skill, and eval layers must remain portable to Codex, Claude Code, and generic MCP clients.

## Planned Structure

- `apps/agent-service`: ADK coordinator and sub-agent service.
- `apps/mcp-server`: MCP tool server and policy enforcement boundary.
- `apps/web`: Thin React console for the agentic portfolio and paper-trading workflows.
- `packages/policy`: Shared action-tier and safety policy logic.
- `packages/model-provider`: Model provider configuration and adapter contracts.
- `packages/agent-platform`: Agent runtime and coding-agent handoff contracts.
- `packages/domain`: Shared typed contracts for portfolio, signals, strategy, and risk concepts.
- `packages/evals`: Agent eval datasets, rubrics, and trajectory checks.
- `packages/shared`: Cross-service utilities when needed.
- `docs`: Architecture, capstone, decisions, tool catalog, and safety docs.
- `infra`: Container and future deployment assets.
- `tests`: Contract, security, and integration tests.
- `demo`: Offline-safe fixtures and public demo scenarios only.
- `references`: Public-safe reference policy and approved public links.

## Next Step

Next implementation milestones:

1. Surface paper-order readiness preflight details in the web console approval workflow and paper-trading reports.
2. Run `scripts/run_agent_evals.py run --fail-on-skip` in a credentialed environment, capture the first model-backed baseline, and tune agent instructions or tool descriptions from failed cases.

## Verification

Root safety and contract tests:

```bash
uv run pytest tests
```

ADK app tests:

```bash
cd apps/agent-service
agents-cli install
uv run pytest tests/unit tests/integration
```

Without Gemini credentials, model-streaming tests are skipped. Credential-free tests still verify imports, server startup, invalid request handling, feedback, and safe tool exposure.

Model-backed eval readiness from the repo root:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

Credentialed eval run:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

## Container Runtime

Use either Docker Compose or Podman Compose from the repo root:

```bash
docker compose up --build
```

```bash
podman compose up --build
```

The default services expose:

- Agent service: `http://localhost:8000`
- MCP server: `http://localhost:8081/mcp`
- Web console: `http://localhost:3000`

Both services use shared local databases when `PAPER_LEDGER_DB_PATH`,
`MARKET_DATA_DB_PATH`, and `PROVIDER_CONFIG_DB_PATH` are set. The Compose
defaults are `/data/paper-ledger.db`, `/data/market-data.db`, and
`/data/provider-config.db` on the `paper-ledger-data` volume; the local
`.env.example` defaults are `data/paper-ledger.db`, `data/market-data.db`, and
`data/provider-config.db`.

The default data-provider mode is offline-safe fixtures. To enable configured
read-only market-data, universe, fundamentals, sentiment, volatility, and macro
adapters, set:

```bash
PORTFOLIO_MARKET_DATA_PROVIDER=json_file
PORTFOLIO_MARKET_DATA_JSON_PATH=data/market-snapshots.json
PORTFOLIO_UNIVERSE_PROVIDER=json_file
PORTFOLIO_UNIVERSE_JSON_PATH=data/universes.json
PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file
PORTFOLIO_FUNDAMENTALS_JSON_PATH=data/fundamentals.json
PORTFOLIO_SENTIMENT_PROVIDER=json_file
PORTFOLIO_SENTIMENT_JSON_PATH=data/sentiment.json
PORTFOLIO_VOLATILITY_PROVIDER=json_file
PORTFOLIO_VOLATILITY_JSON_PATH=data/volatility.json
PORTFOLIO_MACRO_PROVIDER=json_file
PORTFOLIO_MACRO_JSON_PATH=data/macro.json
```

The JSON files are local-only and should stay under ignored data paths. Market
data may contain either one snapshot object, a list of snapshots, or
`{"snapshots": [...]}` using the same `MarketDataSnapshot` payload shape
returned by the MCP tools. Universe data may contain one universe object, a
list of universes, or `{"universes": [...]}` using the same
`UniverseDefinition` payload shape returned by the provider tools.
Fundamentals data may contain one fundamentals object, a list of objects, or
`{"fundamentals": [...]}` with `symbol`, `as_of`, and factor metric keys such
as `quality_score`, `value_score`, `growth_score`,
`earnings_revision_score`, and `leverage_score`. Sentiment data may contain
one sentiment object, a list, or `{"sentiment": [...]}` with metrics such as
`news_score`, `investor_score`, and `contradiction_score`. Volatility data may
contain one volatility object, a list, or `{"volatility": [...]}` with metrics
such as `india_vix`, `vix_change_pct`, `regime_score`, and `risk_multiplier`.
Macro data may contain one macro object, a list, or `{"macro": [...]}` with
metrics such as `market_regime_score`, `breadth_score`,
`rate_pressure_score`, `event_risk_score`, and
`liquidity_condition_score`.
Configured screeners remain read-only and paper-only; they rank candidates
from configured market, fundamental, sentiment, volatility, macro metrics, and
provider refresh readiness, and do not create trades. Import reconciliation is
also included in screener scoring, candidate gates, recommendation risk gates,
and allowed next actions; source-changed, store-mismatch, or needs-attention
states block paper-order next actions until refresh/reconciliation is reviewed.

Use `list_provider_source_onboarding`, `list_provider_import_previews`,
`list_provider_import_reconciliation`, `validate_data_provider_imports`, or the
provider settings page to check configured JSON files before running screeners
or refreshes. Guided onboarding links schema templates, validation, setup gaps,
refresh readiness, and safe next actions. Dry-run previews parse configured
sources into normalized record counts, target stores, sample identifiers,
warnings, and would-write status without initializing storage or writing cache
rows. Reconciliation compares preview counts, latest sanitized refresh-job
counts, and stored row counts to report pending refresh, in-sync,
source-changed, store-mismatch, or needs-attention states without exposing local
paths, database paths, raw payloads, or credential values. Validation reports
provider mode, missing environment keys, shape errors, and sample identifiers
without returning local file paths or credential values.

Use `list_provider_profiles`, `get_provider_refresh_readiness`,
`refresh_provider_import_profile`, `run_provider_refresh_schedule`, and
`list_provider_import_jobs` to persist and review provider profile readiness.
Refresh jobs validate configured sources, store sanitized status, counts,
sample identifiers, env key names, import metadata, retry/backoff state, and
stale-data readiness, and import configured market, universe, fundamentals,
sentiment, volatility, and macro records into structured SQLite tables when
`MARKET_DATA_DB_PATH` is configured. They do not store raw provider payloads or
resolved local paths.

The optional Ollama service is profile-gated:

```bash
podman compose --profile ollama up --build
```

## CI/CD

GitHub Actions are split into CI and CD:

- CI runs deterministic tests, Docker Compose validation, container builds, web readiness, and MCP safe-tool smoke checks for PRs and topic-branch pushes.
- CD publishes agent-service, MCP-server, and web-console images to GHCR only for `v*` tags or explicit manual dispatch.

No workflow requires broker credentials, model provider keys, or live-trading access.

## Branching Model

- `main`: locked release line. Release commits merge here from `develop`.
- `develop`: default integration branch.
- `feature/*`: new work branched from `develop`, merged back into `develop`.
- `fix/*`: defect fixes branched from `develop`, merged back into `develop`.
- `release/*`: optional stabilization branches when preparing a release merge into `main`.
