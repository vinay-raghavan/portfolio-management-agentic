# Verification

## Deterministic Safety Checks

Run from the repo root:

```bash
uv run pytest tests
```

Current coverage:

- Unknown tools are forbidden by default.
- Live trading and broker-token access are blocked.
- Sensitive keys are redacted from blocked-tool details.
- Exposed MCP tools contain no forbidden tool names.
- MCP streamable HTTP runtime exposes only the safe tool catalog.
- Docker or Podman Compose config validates when either runtime is available.
- Demo portfolio, screener, strategy draft, and paper proposal contracts work.
- Pre-market briefing contracts compose portfolio, watchlist, signal, research, and risk sections from synthetic data.
- Product data and pattern contracts list fixture/configured universes, run hard-gated deterministic screeners, retrieve pattern cards, cite strategy evidence, and explain factor stacks.
- Provider readiness evidence contracts disclose stale, backoff, pending, or retry-due provider state in configured screener and recommendation explanations without creating paper orders or leaking local provider paths.
- Provider import-reconciliation gate contracts disclose source-changed, store-mismatch, pending-refresh, and needs-attention states in configured screeners and recommendations, downgrade confidence, and remove paper-order next actions without leaking local provider paths.
- Market-data persistence contracts store and reload fixture/configured-provider market snapshots, provider context records, and screener runs in their tool payload shape without exposing database paths or credentials.
- Provider profile metadata contracts store configured-provider profile and import-refresh job summaries without exposing resolved local paths, file names, credentials, or raw provider payloads.
- Provider refresh orchestration contracts record bounded scheduled refresh cycles, retry/backoff state, and stale-data readiness without exposing local provider paths.
- Configured-source template contracts expose adapter-valid synthetic JSON shapes for market, universe, fundamentals, sentiment, volatility, and macro sources, and verify each template validates through the same configured-provider adapters without leaking source paths or credential-like values.
- Guided configured-source onboarding contracts link templates, validation, setup gaps, refresh readiness, and safe next actions without exposing source paths or credential-like values.
- Configured-provider import preview contracts dry-run normalized target-store counts, sample identifiers, warnings, and would-write status without initializing provider profile or market-data stores, writing cache rows, or leaking source paths or credential-like values.
- Configured-provider import reconciliation contracts compare preview counts, latest refresh-job counts, and structured store row counts, including pending-refresh, in-sync, source-changed, store-mismatch, and needs-attention states, without leaking source paths, database paths, raw payloads, or credential-like values.
- Recommendation explanation contracts join factor evidence, strategy history, backtest metrics, risk gates, ledger context, citations, and paper-only next actions without creating orders.
- Paper-trading report contracts return read-only review summaries with JSON-ready redacted audit exports and no file writes.
- Model-backed eval preflight checks build the official `agents-cli eval generate` and `agents-cli eval grade` commands, skip without credentials, and never print secret values.
- Web console contracts verify the Vite/React app, safe product surfaces, Compose wiring, `/console/overview`, focused `/console/workflows` pages, provider source setup visibility, guided onboarding, required env-key display, active adapter modes, setup-gap feedback, schema/template guidance, provider import validation feedback, provider profile/import-job settings, import-gate visibility on decision pages, full provider refresh controls, per-provider backoff state, and the paper-only action lifecycle.
- Provider adapter contracts expose fixture defaults, provider health, import validation, fixture market snapshots, configured read-only JSON market snapshots, configured read-only JSON universes, configured read-only JSON fundamentals, configured read-only JSON sentiment, configured read-only JSON volatility, configured read-only JSON macro context, and universe membership without credentials or network requirements.
- Strategy, backtest, and paper-ledger contracts persist paper strategy drafts and backtest request history, return offline results, require readiness preflight before paper order proposals, block incomplete proposal evidence before draft creation, require approval before simulated fills, update paper positions/accounting, emit redacted audit events, and persist paper-ledger state when SQLite is configured.
- Gemini, Claude, OpenAI-compatible, and Ollama provider profiles are declared.
- ADK, Codex, Claude Code, Gemini CLI, and generic MCP client profiles use the MCP policy boundary.

## ADK Scaffold Checks

Run from `apps/agent-service`:

```bash
agents-cli install
uv run pytest tests/unit tests/integration
```

Credential-free checks verify:

- Agent imports without Google ADC.
- The ADK agent exposes safe portfolio, briefing, provider, screener, pattern, factor-evidence, recommendation, report, strategy-history, backtest-history, paper-ledger, and risk tools only.
- The FastAPI app starts without Google ADC.
- Invalid request handling works.
- Feedback endpoint works with local logging fallback.

Gemini streaming tests are skipped unless `GOOGLE_API_KEY` or `GOOGLE_CLOUD_PROJECT` is configured.

## Agent Evals

From the repository root, run a credential-safe preflight first:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

Run from `apps/agent-service` after model credentials are configured:

```bash
agents-cli eval generate
agents-cli eval grade
```

The repository wrapper runs the same generate-and-grade sequence with explicit
artifact directories:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The default dataset includes positive workflow cases and negative safety cases.
The `forbidden_action_policy` code metric fails traces that call forbidden tools
or fail to clearly refuse live-trading and credential-disclosure requests.

## Container Checks

Use either Docker Compose or Podman Compose from the repo root:

```bash
docker compose config --quiet
docker compose up --build
```

```bash
podman compose config --quiet
podman compose up --build
```

Default endpoints:

- Agent service: `http://localhost:8000`
- MCP server: `http://localhost:8081/mcp`
- Web console: `http://localhost:3000`

Compose config also validates the shared `paper-ledger-data` volume and
`PAPER_LEDGER_DB_PATH=/data/paper-ledger.db`,
`MARKET_DATA_DB_PATH=/data/market-data.db`, and
`PROVIDER_CONFIG_DB_PATH=/data/provider-config.db` defaults for durable local
ledger, market-data, and provider-profile metadata state. It also passes
`PORTFOLIO_MARKET_DATA_PROVIDER`,
`PORTFOLIO_MARKET_DATA_JSON_PATH`, `PORTFOLIO_UNIVERSE_PROVIDER`,
`PORTFOLIO_UNIVERSE_JSON_PATH`, `PORTFOLIO_FUNDAMENTALS_PROVIDER`,
`PORTFOLIO_FUNDAMENTALS_JSON_PATH`, `PORTFOLIO_SENTIMENT_PROVIDER`,
`PORTFOLIO_SENTIMENT_JSON_PATH`, `PORTFOLIO_VOLATILITY_PROVIDER`, and
`PORTFOLIO_VOLATILITY_JSON_PATH`, `PORTFOLIO_MACRO_PROVIDER`, and
`PORTFOLIO_MACRO_JSON_PATH` to the agent and MCP services so local JSON
snapshot, universe, fundamentals, sentiment, volatility, and macro adapters
can be enabled without committing provider data. Import validation, dry-run
import previews, and import reconciliation check those configured JSON files
without returning local file paths. Preview output includes normalized counts,
target stores, sample identifiers, warnings, and would-write status before
refresh writes run. Reconciliation output compares preview counts, latest
refresh-job counts, and stored row counts before configured screeners or
recommendations rely on cached provider data. Source-changed, store-mismatch,
or needs-attention states downgrade configured evidence and block paper-order
next actions until refresh/reconciliation is reviewed. Provider profile refresh jobs persist sanitized
validation and execution summaries, source env key names, import counts,
retry/backoff state, and stale-data readiness. Configured refreshes can import
normalized snapshots into
`market_data_snapshots`, `provider_universe_members`, and
`provider_factor_snapshots` when `MARKET_DATA_DB_PATH` is configured.

The optional local LLM profile is disabled by default:

```bash
podman compose --profile ollama up --build
```

## GitHub Actions

CI runs on pull requests into `develop` or `main`, pushes to `develop`, `main`,
`feature/**`, and `fix/**`, and manual dispatch. It runs:

- Root contract, security, integration, and hygiene tests.
- Credential-gated model eval preflight.
- Agent-service unit and integration tests.
- Web console install, moderate dependency audit, typecheck, and build.
- Docker Compose config validation.
- Agent, MCP, and web image builds.
- Agent readiness check at `/docs`.
- Web console readiness check at `http://127.0.0.1:3000`.
- MCP streamable HTTP safe-tool catalog check.

CD runs on `v*` tags or manual dispatch. It builds the agent-service and
MCP-server and web-console images and publishes them to GHCR only when
tag-triggered or when manual dispatch explicitly enables image publishing. It
does not deploy to an environment or require model, broker, or data-provider
credentials.
