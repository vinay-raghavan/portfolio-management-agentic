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
- The ADK agent exposes safe portfolio, briefing, screener, strategy, and risk tools only.
- The FastAPI app starts without Google ADC.
- Invalid request handling works.
- Feedback endpoint works with local logging fallback.

Gemini streaming tests are skipped unless `GOOGLE_API_KEY` or `GOOGLE_CLOUD_PROJECT` is configured.

## Agent Evals

Run from `apps/agent-service` after model credentials are configured:

```bash
agents-cli eval generate
agents-cli eval grade
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

The optional local LLM profile is disabled by default:

```bash
podman compose --profile ollama up --build
```

## GitHub Actions

CI runs on pull requests into `develop` or `main`, pushes to `develop`, `main`,
`feature/**`, and `fix/**`, and manual dispatch. It runs:

- Root contract, security, integration, and hygiene tests.
- Agent-service unit and integration tests.
- Docker Compose config validation.
- Agent and MCP image builds.
- Agent readiness check at `/docs`.
- MCP streamable HTTP safe-tool catalog check.

CD runs on `v*` tags or manual dispatch. It builds the agent-service and
MCP-server images and publishes them to GHCR only when tag-triggered or when
manual dispatch explicitly enables image publishing. It does not deploy to an
environment or require model, broker, or data-provider credentials.
