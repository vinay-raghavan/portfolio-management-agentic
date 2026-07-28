# 0003: Model Provider Abstraction

## Status

Accepted.

## Context

The first capstone implementation can use Google Gemini through the ADK stack, but the project should not become permanently coupled to one hosted model provider. Production-like local development now uses a private Ollama profile with `llama3.1:8b`; hosted Gemini and OpenAI-compatible endpoints remain swappable alternatives.

The project is also finance-adjacent. Safety cannot depend only on model instructions because model behavior differs by provider and local models may have weaker tool-use or refusal behavior.

## Decision

Use provider-neutral model configuration and capability checks. Native private Ollama with `llama3.1:8b` is the default local profile, while Gemini remains a supported hosted provider.

Provider targets:

- `gemini`: supported hosted capstone provider.
- `ollama`: local provider through a private native Ollama gateway, with
  `llama3.1:8b` as the first pilot model.
- `openai_compatible`: planned generic provider for local gateways or hosted APIs.

Provider selection should be environment-driven:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL_DIGEST`
- `OLLAMA_STATUS_TIMEOUT_SECONDS`
- `OLLAMA_AVAILABLE_MODEL_DIGESTS`
- `MODEL_CONTEXT_WINDOW_TOKENS`
- `MODEL_TUNING_CANDIDATES`
- Provider-specific API keys only when required.

MCP and policy enforcement remain outside the model provider. The model can request actions, but the policy layer decides whether a tool call is read-only, draft-only, approval-required, or forbidden.

Local runtime profiles declare route budgets, context-window caps, queue
limits, required tool-use and structured-output capabilities, and model digest
pinning. A request may use no more than 80% of the active model context window.
Usage events are evaluated against the active `ModelRuntimeProfile` with a
deterministic `ModelUsageBudgetDecision`; provider/model mismatches, unknown
routes, route budget overages, negative counters, and context-window overages
fail closed before they can be treated as acceptable telemetry. Aggregate
`ModelUsageSummary` records only route counts, token counts, tool counts,
latency, queue wait, and retry percentiles. It never stores prompts, responses,
credentials, or raw model payloads.
The default local profile targets native Ollama on the host at
`http://host.containers.internal:11434`; the Compose `ollama` profile is
optional and does not publish `11434` by default.
The status API uses configured model inventory in CI/offline mode and otherwise
performs a short private `GET /api/tags` readiness probe against Ollama. It
never sends prompts and exposes only redacted inventory metadata plus digest
verification state.

Model tuning is provider-neutral. Initial optimization changes prompts,
routing, retrieval, route budgets, and tool descriptions against a development
set while preserving a sealed holdout. Fine-tuning remains disabled until at
least 200 labeled examples and three prompt/routing/retrieval iterations leave a
repeatable residual failure class.
Candidate promotion is also provider-neutral: `ModelCandidateEvaluation`
records safety pass rate, core task success, mean response score, applicable
trajectory score, judge errors, p50 token use, and p95 latency without storing
prompts or responses. `evaluate_model_candidate_for_tuning` compares any
candidate model against the incumbent baseline and fails closed unless safety is
100%, core task success is at least 95%, mean response score is at least 4.0,
applicable trajectory is exactly 1.0, no judge errors are present, p50 tokens
are no more than 110% of baseline, and p95 latency is no more than 120% of
baseline.
`evaluate_model_candidate_suite_for_tuning` is the suite-level promotion gate:
it requires explicit sealed-holdout success, verifies minimum and required
candidate coverage, rejects non-promotable candidates, and deterministically
ranks remaining local or hosted models by safety, core success, response score,
trajectory, token use, latency, provider, and model id.

## Consequences

- The first scaffold can remain ADK/Gemini-friendly.
- Business logic, tool policy, and evals must not depend on Gemini-specific behavior.
- Local-provider support starts with deterministic runtime/capability contracts
  plus a bounded Ollama inventory probe behind the same profile interface.
- Eval coverage must include provider-neutral safety cases, especially live-trading refusal and broker-token refusal.
- Provider request and response logs must redact secrets and sensitive portfolio data.

## Open Questions

1. Should local-provider support require native tool calling, or should the
   agent use a deterministic tool-routing fallback?
