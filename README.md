# Portfolio Management Agentic

Agentic portfolio and paper-trading workbench for the Kaggle AI Agents capstone.

This is a standalone repository boundary. Implementation should use documented API contracts, bounded tools, demo data, and explicit safety policy.

## Current State

- ADK prototype scaffolded in `apps/agent-service`.
- Platform-neutral policy, domain, model-provider, and agent-platform contracts started.
- MCP-style safe portfolio tools started in `apps/mcp-server` with streamable HTTP runtime support.
- Docker or Podman Compose runs the agent service, MCP server, and optional Ollama profile.
- No copied portfolio data.
- No broker trading credentials.
- No live trading.
- Gitflow-style branching is enabled: `main` is release-only, `develop` is the integration branch, and active work happens on topic branches from `develop`.

## Repository Intent

The project will add an ADK-based agent layer, MCP policy server, eval suite, and capstone demo around a portfolio-management and paper-trading workflow.

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
- `apps/web`: Optional capstone UI or thin agent console.
- `packages/policy`: Shared action-tier and safety policy logic.
- `packages/model-provider`: Model provider configuration and adapter contracts.
- `packages/agent-platform`: Agent runtime and coding-agent handoff contracts.
- `packages/domain`: Shared typed contracts for portfolio, signals, strategy, and risk concepts.
- `packages/evals`: Agent eval datasets, rubrics, and trajectory checks.
- `packages/shared`: Cross-service utilities when needed.
- `docs`: Architecture, capstone, decisions, tool catalog, and safety docs.
- `infra`: Container and future deployment assets.
- `tests`: Contract, security, and integration tests.
- `demo`: Synthetic data and demo scenarios only.
- `references`: Public-safe reference policy and approved public links.

## Next Step

Next implementation milestones:

1. Expand MCP tools from demo contracts to the first full briefing workflow.
2. Add read-only RAG pattern memory for strategy playbooks and cited explanations.
3. Add demo scenarios or a demo data service for richer capstone walkthroughs.
4. Run and tune model-backed agent evals when provider credentials are configured.
5. Build the first capstone web or console demo flow.

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

The optional Ollama service is profile-gated:

```bash
podman compose --profile ollama up --build
```

## CI/CD

GitHub Actions are split into CI and CD:

- CI runs deterministic tests, Docker Compose validation, container builds, and MCP safe-tool smoke checks for PRs and topic-branch pushes.
- CD publishes agent-service and MCP-server images to GHCR only for `v*` tags or explicit manual dispatch.

No workflow requires broker credentials, model provider keys, or live-trading access.

## Branching Model

- `main`: locked release line. Release commits merge here from `develop`.
- `develop`: default integration branch.
- `feature/*`: new work branched from `develop`, merged back into `develop`.
- `fix/*`: defect fixes branched from `develop`, merged back into `develop`.
- `release/*`: optional stabilization branches when preparing a release merge into `main`.
