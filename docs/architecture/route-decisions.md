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
  must come from the authenticated human API.
- Paper proposal routes may expose only the draft-only
  `paper_proposal_execution` capability tools.
- `approve_paper_order_simulation` and `simulate_approved_paper_fill` remain
  outside model-selected approval routes.

## Integration path

The next runtime slice should call `DeterministicRouter` before constructing a
model request. If the decision is `needs_classification`, a schema-constrained
classifier may choose among read-only capabilities and must fall back to
clarification for invalid or low-confidence output.
