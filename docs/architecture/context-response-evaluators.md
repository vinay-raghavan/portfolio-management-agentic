# Context and Response Evaluators

The harness evaluator contracts add deterministic checks around model calls.
They are model-independent and should run the same way for Gemini, Ollama,
Gemma, Llama, Claude, or any OpenAI-compatible runtime.

## ContextPack

`ContextPack` is the typed bundle of context selected for one routed request. It
records:

- tenant, user, route, and request id;
- source ids, source types, provenance, freshness, and checksums;
- token counts and the route/model input budget.

Context items are untrusted until `ContextEvaluator` accepts them.

## ContextEvaluator

`ContextEvaluator` deterministically blocks context with:

- tenant mismatch;
- stale or expired sources;
- low relevance;
- duplicate checksums;
- prompt-injection language;
- secret-looking content;
- input-token budget overflow.

Findings are redaction-safe and do not echo secret values.

## ResponseEvaluator

`ResponseEvaluator` validates structured model output against:

- required response fields;
- citation existence in the supplied `ContextPack`;
- agreement between declared supported claims and tool outputs;
- required policy statements;
- required uncertainty or data-limit statements.

One structured repair attempt is allowed by contract. If the repaired response
still fails, the caller should return a typed safe error instead of relying on
LLM judging as a runtime safety control.

## Integration path

The next router slice should:

1. Build a route-scoped `ContextPack`.
2. Run `ContextEvaluator` before calling the model.
3. Call the model with only evaluated context and route-scoped tools.
4. Run `ResponseEvaluator` on the structured response.
5. Permit one repair attempt, then fail closed.
