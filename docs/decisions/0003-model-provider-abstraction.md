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
- `ollama`: local provider through a private native Ollama gateway, with
  `llama3.1:8b` as the first pilot model.
- `openai_compatible`: planned generic provider for local gateways or hosted APIs.

Provider selection should be environment-driven:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL_DIGEST`
- `MODEL_CONTEXT_WINDOW_TOKENS`
- `MODEL_TUNING_CANDIDATES`
- Provider-specific API keys only when required.

MCP and policy enforcement remain outside the model provider. The model can request actions, but the policy layer decides whether a tool call is read-only, draft-only, approval-required, or forbidden.

Local runtime profiles declare route budgets, context-window caps, queue
limits, required tool-use and structured-output capabilities, and model digest
pinning. A request may use no more than 80% of the active model context window.
The default local profile targets native Ollama on the host at
`http://host.containers.internal:11434`; the Compose `ollama` profile is
optional and does not publish `11434` by default.

Model tuning is provider-neutral. Initial optimization changes prompts,
routing, retrieval, route budgets, and tool descriptions against a development
set while preserving a sealed holdout. Fine-tuning remains disabled until at
least 200 labeled examples and three prompt/routing/retrieval iterations leave a
repeatable residual failure class.

## Consequences

- The first scaffold can remain ADK/Gemini-friendly.
- Business logic, tool policy, and evals must not depend on Gemini-specific behavior.
- Local-provider support starts with deterministic runtime/capability contracts
  and can later add live Ollama probing behind the same profile interface.
- Eval coverage must include provider-neutral safety cases, especially live-trading refusal and broker-token refusal.
- Provider request and response logs must redact secrets and sensitive portfolio data.

## Open Questions

1. Which provider-neutral eval metric should select the next 7B/8B candidate
   after the `llama3.1:8b` pilot?
2. Should local-provider readiness probe `ollama /api/tags` at startup or only
   in a deployment preflight command?
3. Should local-provider support require native tool calling, or should the agent use a deterministic tool-routing fallback?
