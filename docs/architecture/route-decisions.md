# Route Decisions

`DeterministicRouter` is the first stage of the harness router. It handles
high-risk precedence before any model-based or schema-constrained
classification is allowed.

## Deterministic precedence

The router currently returns a `RouteDecision` for:

1. Forbidden live-trading, live-strategy, credential, or approval-bypass intent.
2. FYERS refresh/OAuth/account-refresh intent.
3. Human paper-approval intent.
4. Draft-only paper proposal intent.
5. Ambiguous read-only intent that may proceed to schema-constrained
   classification.

## Safety boundaries

- Forbidden routes select the toolless `safety` capability.
- FYERS refresh routes to `/v1/integrations/fyers/refresh`; OAuth and reconnect
  operations stay outside model-visible tools.
- Paper approval routes to `/v1/paper/batches/{id}/approve`; approval identity
  must come from server-created `ActorContext` derived from the authenticated
  human API, never from `approved_by` in model output or request JSON.
- Paper proposal routes may expose only the draft-only
  `paper_proposal_execution` capability tools.
- `approve_paper_order_simulation` and `simulate_approved_paper_fill` remain
  outside model-selected approval routes and are not registered in the
  model-visible MCP transport catalog.

## Route tool bundles

`RouteToolBundle` is the least-privilege model-visible tool contract derived
from a `RouteDecision`. Capability routes receive exactly the selected
manifest's allowed tools, filtered to tools that are exposed and within the
manifest's maximum action tier. Forbidden, FYERS refresh/OAuth, and human
approval routes return an empty model-visible bundle and point callers to the
protected human API when applicable.

Schema-constrained classification may resolve only read-only capabilities.
Invalid, unknown, low-confidence, or non-read-only classified capabilities must
fall back to clarification rather than widening the tool bundle.

## Integration path

The runtime should call `DeterministicRouter` before constructing a model
request, then build a `RouteToolBundle` before context packing or model calls.
If the decision is `needs_classification`, a schema-constrained classifier may
choose among read-only capabilities and must fall back to clarification for
invalid or low-confidence output.
