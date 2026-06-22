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
- Product data and pattern contracts list fixture universes, run hard-gated deterministic screeners, retrieve pattern cards, cite strategy evidence, and explain factor stacks.
- Market-data persistence contracts store and reload fixture/configured-provider market snapshots and screener runs in their tool payload shape without exposing database paths or credentials.
- Recommendation explanation contracts join factor evidence, strategy history, backtest metrics, risk gates, ledger context, citations, and paper-only next actions without creating orders.
- Paper-trading report contracts return read-only review summaries with JSON-ready redacted audit exports and no file writes.
- Model-backed eval preflight checks build the official `agents-cli eval generate` and `agents-cli eval grade` commands, skip without credentials, and never print secret values.
- Web console contracts verify the Vite/React app, safe product surfaces, Compose wiring, `/console/overview`, focused `/console/workflows` pages, and the paper-only action lifecycle.
- Provider adapter contracts expose fixture defaults, provider health, fixture market snapshots, configured read-only JSON market snapshots, and universe membership without credentials or network requirements.
- Strategy, backtest, and paper-ledger contracts persist paper strategy drafts and backtest request history, return offline results, create pending paper order proposals, require approval before simulated fills, update paper positions/accounting, emit redacted audit events, and persist paper-ledger state when SQLite is configured.
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
`PAPER_LEDGER_DB_PATH=/data/paper-ledger.db` plus
`MARKET_DATA_DB_PATH=/data/market-data.db` defaults for durable local ledger and
market-data state. It also passes `PORTFOLIO_MARKET_DATA_PROVIDER` and
`PORTFOLIO_MARKET_DATA_JSON_PATH` to the agent and MCP services so a local
JSON snapshot adapter can be enabled without committing provider data.

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
