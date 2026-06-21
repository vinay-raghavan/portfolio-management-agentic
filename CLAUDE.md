# Claude Code Guide

Read `.agents-cli-spec.md` before implementation work.

This repo is platform-neutral. Claude Code should use the same MCP tools, policy tests, evals, and safety gates as ADK or Codex.

Hard rules:

- No real trades.
- No broker trading-token access.
- No copied real portfolio data.
- No committed secrets.
- Financial actions must be read-only, draft-only, or pending human approval.
- Forbidden tool calls must be blocked by policy code even if the model asks for them.

Primary files:

- `.agents-cli-spec.md`
- `docs/decisions/0004-agent-platform-neutrality.md`
- `packages/policy`
- `apps/mcp-server`
- `tests/security`

