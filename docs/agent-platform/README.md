# Agent Platform Guidance

This directory will hold platform-specific handoff guidance for ADK, Codex, Claude Code, and generic MCP clients.

The portable contract is:

- Use the MCP server for tools.
- Enforce action tiers in policy code, not only prompts.
- Keep model-provider configuration separate from tool policy.
- Run the same safety tests and evals before release.
- Never enable live trading or broker trading-token access.

