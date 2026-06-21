# Portfolio Management Agentic

Agentic portfolio and paper-trading workbench for the Kaggle AI Agents capstone.


## Current State

- Spec-first phase.
- No scaffolded ADK code yet.
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
- Existing projects and whitepapers are external references, not vendored source.
- Docker Compose is the first deployment target.
- Gemini is the first model provider, but the design must support local or OpenAI-compatible providers such as Ollama later.

## Planned Structure

- `apps/agent-service`: ADK coordinator and sub-agent service.
- `apps/mcp-server`: MCP tool server and policy enforcement boundary.
- `apps/web`: Optional capstone UI or thin agent console.
- `packages/policy`: Shared action-tier and safety policy logic.
- `packages/model-provider`: Model provider configuration and adapter contracts.
- `packages/domain`: Shared typed contracts for portfolio, signals, strategy, and risk concepts.
- `packages/evals`: Agent eval datasets, rubrics, and trajectory checks.
- `packages/shared`: Cross-service utilities when needed.
- `docs`: Architecture, capstone, decisions, tool catalog, and safety docs.
- `infra`: Docker and future deployment assets.
- `tests`: Contract, security, and integration tests.
- `demo`: Synthetic data and demo scenarios only.
- `references`: Pointers to external reference material, not copied source.

## Next Step

After this repo boundary is approved:

1. Study matching ADK samples.
2. Run `agents-cli info`.
3. Load the scaffold skill.
5. Start with MCP policy tests and negative safety evals.

## Branching Model

- `main`: locked release line. Release commits merge here from `develop`.
- `develop`: default integration branch.
- `feature/*`: new work branched from `develop`, merged back into `develop`.
- `fix/*`: defect fixes branched from `develop`, merged back into `develop`.
- `release/*`: optional stabilization branches when preparing a release merge into `main`.

Current active branch: `feature/agentic-scaffold`.
