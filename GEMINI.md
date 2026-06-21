# Gemini And ADK Guide

Read `.agents-cli-spec.md` before implementation work.

ADK is the first capstone runtime, but the framework is not Google-only. Keep model provider choices and agent platform choices behind configuration and adapters.

Hard rules:

- Gemini is the first demo provider, not the only future provider.
- Keep Ollama, Claude, and OpenAI-compatible support possible through the model-provider contract.
- Use MCP and policy code for safety enforcement.
- Keep all trading workflows paper-only or simulation-only.
- Never enable live trading or broker trading-token access.

ADK prototype:

- `apps/agent-service`

