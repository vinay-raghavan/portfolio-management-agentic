# Capability Manifests and Repository Skills

Capability manifests are the route-scoped source of truth for the next harness
slice. Each capability lives under `capabilities/<name>/` with:

- `manifest.json`: runtime-facing contract for allowed tools, context sources,
  response schema, token budget, and eval cases.
- `SKILL.md`: agent-facing workflow instructions that must match the manifest.

The parity test in `tests/contract/test_capability_manifests.py` ensures every
manifest has matching skill documentation, references only exposed and
policy-classified tools, and preserves the paper-only safety boundary.
`DeterministicRouter.tool_bundle_for(...)` consumes these manifests to build
the current `RouteToolBundle` contract used by route-scoped model calls.

## Current capabilities

| Capability | Max tier | Purpose |
| --- | --- | --- |
| `research` | read-only | Curated research and pattern-card synthesis with citations. |
| `technical_analysis` | read-only | Deterministic screener, market snapshot, and factor-stack explanations. |
| `fyers_data` | read-only | FYERS-style normalized provider/account snapshot context without credentials or mutations. |
| `pre_market_briefing` | read-only | Portfolio, watchlist, signals, research digest, and risk-state pre-market review. |
| `provider_readiness` | read-only | Configured data-provider health, validation, previews, reconciliation, and refresh readiness. |
| `risk_review` | read-only | Portfolio, paper-ledger, watchlist, and safety-switch review. |
| `paper_proposal_execution` | draft-only | Paper-only strategy/backtest/order proposal drafting; no approval or fill authority. |
| `reporting` | read-only | Paper ledger, approvals, fills, accounting, and redacted audit reporting. |
| `safety` | forbidden/toolless | Refusal path for live trading, credentials, approval bypass, and unsafe requests. |

## Safety invariants

- Read-only capabilities may use only read-only tools.
- `paper_proposal_execution` may draft proposals but must not include
  `approve_paper_order_simulation` or `simulate_approved_paper_fill`.
- `safety` is intentionally toolless.
- Forbidden live-trading and broker-token tools remain policy-classified but
  absent from every allowed tool bundle.
- The FYERS capability is currently a read-only provider-data contract. OAuth,
  credential storage, approval, revocation, live order placement, and policy
  administration remain outside model-visible tools.

## Router integration path

These manifests are the audited contract the router consumes for
least-privilege model-visible tool bundles:

1. Deterministically route forbidden, FYERS refresh, approval, and paper
   execution intents before model classification.
2. Select exactly one `CapabilityManifest`.
3. Build a `RouteToolBundle` with only the manifest's allowed tools for that
   route.
4. Build a context pack from the manifest's context sources.
5. Validate the response against the manifest's response schema and eval cases.
