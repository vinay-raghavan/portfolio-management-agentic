# 0006 CI/CD Boundary

## Status

Accepted.

## Context

The project needs repeatable checks and a release path after the Docker and eval foundation. The workflow structure is adapted from a local reference project, but this repository must keep its own branch model, paths, safety policy, and paper-trading constraints.

## Decision

Add two GitHub Actions workflows:

- `CI`: runs deterministic root tests, agent-service tests, Docker Compose validation, image builds, agent readiness, and MCP safe-tool smoke checks.
- `CD`: publishes agent-service and MCP-server images to GHCR only on version tags or explicit manual dispatch.

CI uses read-only repository permissions. CD grants package write permission only for container publishing through `GITHUB_TOKEN`. No model provider keys, broker credentials, live-trading credentials, or deployment secrets are required.

## Consequences

- Pull requests into `develop` get deterministic test and container evidence before merge.
- Release images can be produced without enabling live trading or cloud deployment.
- Deployment to a runtime environment remains a later decision after a target, rollback plan, and approval gate exist.
- Main remains release-only; normal implementation continues through topic branches into `develop`.

## Verification

- `uv run pytest tests`
- `cd apps/agent-service && uv run pytest tests/unit tests/integration`
- `docker compose config --quiet`
- CI workflow smoke checks agent readiness and MCP safe tool exposure.
