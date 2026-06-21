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
- Demo portfolio, screener, strategy draft, and paper proposal contracts work.
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
- The ADK agent exposes safe portfolio tools only.
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
