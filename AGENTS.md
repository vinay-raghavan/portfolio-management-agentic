# Codex Agent Guide

Read `.agents-cli-spec.md` before implementation work.

Hard rules:

- Work from `develop` through `feature/*`, `fix/*`, or `release/*` branches.
- Treat `main` as release-only.
- Do not copy real portfolio data, local env files, broker credentials, or provider tokens.
- Keep all trading workflows paper-only or simulation-only.
- Never enable live trading or broker trading-token access.
- Enforce safety in code and MCP policy, not only prompts.
- Run policy tests and evals before release.

Useful starting points:

- Spec: `.agents-cli-spec.md`
- Reference map: `references/reference-map.md`
- Policy code: `packages/policy`
- MCP tools: `apps/mcp-server`
- ADK prototype: `apps/agent-service`
- Capability manifests and repository skills: `capabilities/<name>/manifest.json` and `capabilities/<name>/SKILL.md`
- Provider metadata: `packages/domain/portfolio_domain/provider_profiles.py`
