# 0003: Model Provider Abstraction

## Status

Accepted.

## Context

The first capstone implementation can use Google Gemini through the ADK stack, but the project should not become permanently coupled to one hosted model provider. Future development may use a local model through Ollama or another OpenAI-compatible endpoint.

The project is also finance-adjacent. Safety cannot depend only on model instructions because model behavior differs by provider and local models may have weaker tool-use or refusal behavior.

## Decision

Use Gemini as the first working provider, while designing the agent service around model-provider configuration and capability checks.

Provider targets:

- `gemini`: primary capstone provider.
- `ollama`: planned local provider.
- `openai_compatible`: planned generic provider for local gateways or hosted APIs.

Provider selection should be environment-driven:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`
- Provider-specific API keys only when required.

MCP and policy enforcement remain outside the model provider. The model can request actions, but the policy layer decides whether a tool call is read-only, draft-only, approval-required, or forbidden.

## Consequences

- The first scaffold can remain ADK/Gemini-friendly.
- Business logic, tool policy, and evals must not depend on Gemini-specific behavior.
- Local-provider support can start as a documented adapter contract and test stub before full Ollama runtime support.
- Eval coverage must include provider-neutral safety cases, especially live-trading refusal and broker-token refusal.
- Provider request and response logs must redact secrets and sensitive portfolio data.

## Open Questions

1. Should Ollama run as a Docker or Podman Compose profile inside this repo or be treated as an external local dependency?
2. Which local model should be the first Ollama target once the Gemini path is stable?
3. Should local-provider support require native tool calling, or should the agent use a deterministic tool-routing fallback?
