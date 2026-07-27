# Backtest And Paper Ledger Contracts

This slice establishes the safe contract between research, simulation, and the future paper-trading ledger.

## Current Capabilities

- Draft an offline backtest request for a symbol, setup, and date window.
- Persist and retrieve paper strategy draft history.
- Persist and retrieve paper backtest request history.
- Return deterministic simulated backtest metrics and closed simulated trades.
- Explain paper-only recommendations by joining factor evidence, strategy history, backtest history, risk gates, ledger context, and citations.
- Generate read-only paper-trading review reports with readiness preflight sections and redacted audit export rows.
- Create a paper order proposal that first passes recommendation readiness preflight and then remains `pending_approval`.
- Block paper order proposals before draft creation when strategy history, backtest history, provider refresh readiness, import reconciliation, or recommendation gates are not ready.
- Approve a paper order for simulated execution through an approval-required tool.
- Simulate a paper fill only after approval.
- Define bounded batch paper-execution policy ceilings, paper batch requests,
  human-bound execution grants, and deterministic paper execution decisions as
  domain contracts for protected server-side workers.
- List paper order proposals, simulated fills, and accounting summaries.
- List fixture-backed paper positions for exposure review.
- Show pending human approvals.
- Show redacted audit events for paper-ledger actions.
- Export audit rows as JSON-ready, redacted report data without writing files.
- Surface stored readiness preflight status, provider reconciliation, provider refresh, submitted strategy, blocking reasons, paper-only policy, and human approval requirement in report data and the web console.
- Persist strategy drafts, backtest requests, paper orders, paper positions, approval requests, simulated fills, and audit events in SQLite when `PAPER_LEDGER_DB_PATH` is configured.

## Safety Boundary

- Backtest output is simulated and not predictive.
- Paper order proposals do not create fills by themselves.
- Paper order proposals require a ready `paper-order-readiness-preflight/v1` snapshot before they can enter the approval queue.
- Human approval is required before simulated execution.
- Batch paper execution is disabled until an admin-created
  `PaperExecutionPolicyCeiling` explicitly sets every required strategy,
  symbol, side, order-type, quantity, notional, loss, drawdown, slippage,
  freshness, and validity limit.
- A `PaperExecutionGrant` is issued only from a proposed `PaperBatchRequest`,
  is bound to the authenticated human approver actor, cannot outlive the
  policy ceiling, cannot exceed either the request or the ceiling, and rejects
  requester self-approval unless the ceiling explicitly permits it.
- The deterministic paper executor rejects expired or revoked grants, duplicate
  idempotency keys, stale quotes, inactive policies, kill-switch activation,
  tenant/scope mismatches, insufficient paper cash, and quantity/notional
  ceiling violations before returning any fill payload.
- `DeterministicPaperExecutionWorker` owns the paper-only evaluate-and-record
  boundary through `PaperExecutionWorkerRequest`. `PaperExecutionWorkItem`
  provides the durable queue contract for protected workers, and
  `PaperExecutionQueueProcessor` claims one tenant-scoped item, rebuilds the
  authoritative policy/grant/batch/order context, rejects malformed or
  credential-contaminated payloads, executes the deterministic worker, records
  accepted ledger decisions, and completes the work item. In Postgres mode, the
  protected API invokes this standalone processor synchronously today, and the
  `paper-execution-worker` deployment service invokes the same boundary as a
  background queue loop without giving the model or MCP layer execution
  authority.
- `PostgresPaperExecutionStore` persists and reads protected policy ceilings,
  batch requests, execution grants, durable execution work items, and
  idempotent ledger decision rows through tenant-scoped Postgres tables created
  by Alembic. It can revoke active grants atomically, enqueue/claim/complete
  paper execution work items with `FOR UPDATE SKIP LOCKED`, checks the durable
  ledger for duplicate idempotency keys before API execution, treats the unique
  ledger insert result as authoritative if a concurrent request races the
  pre-check, locks the active grant row before accepted ledger insertion,
  admits the insert only while reserved order/gross/net capacity remains, updates
  consumed capacity only after the ledger row is inserted, stores JSON-safe
  summaries only, and rejects FYERS, broker trading-token, and
  credential-looking payload contamination before writes or reads return domain
  contracts.
- The agent service exposes protected `/v1/paper/policies`,
  `/v1/paper/batches`, `/v1/paper/batches/{id}/approve|revoke`, and
  `/v1/paper/orders/{id}/execute` contracts. These endpoints derive requester
  and approver identity from server-created `ActorContext`, forbid
  `approved_by` request-body spoofing, use `PostgresPaperExecutionStore` when
  `PORTFOLIO_STORAGE_BACKEND=postgres`, route Postgres execution through the
  durable work-item queue boundary, and return paper-only decisions. They are
  API contracts for protected callers, not MCP/model-visible tools.
- Simulated fills update only the paper ledger and paper positions.
- Approval cannot authorize live trading.
- Broker trading-token access and live order placement remain forbidden.
- Fixture stores use offline-safe data and do not require provider credentials.
- Persisted rows contain paper-only strategy drafts, backtest requests, proposals, readiness preflight snapshots, approvals, fixture positions, and redacted audit payloads; no broker credentials or live account identifiers are stored.
- Report generation is read-only and returns structured data for the caller to render or store outside the tool boundary.

## Runtime Storage

The default Python import path remains fixture-backed and in memory when no
database path is configured. Local and container runtimes can enable durable
strategy, backtest, and paper-ledger state with `PAPER_LEDGER_DB_PATH`.

Production-like runtimes use the Postgres platform schema and the protected API
store adapter for bounded paper execution state. Alembic migration
`20260727_0003` adds explicit `permitted_symbols` to
`paper_execution_policy_ceilings` so policy ceilings can bound both symbols and
future universe scopes without overloading fields. Alembic migration
`20260727_0004` adds the tenant-scoped `paper_execution_work_items` queue table
with idempotency uniqueness, worker-claim indexes, and row-level security.
The protected HTTP endpoints keep local process state only as the
SQLite/offline deterministic fallback. In Postgres mode, duplicate
idempotency-key rejection reads from the tenant-scoped paper ledger instead of
process memory, and a skipped `ON CONFLICT DO NOTHING ... RETURNING id` insert
is returned to the API as a duplicate rejection rather than an accepted fill.
Postgres execution limit checks derive current exposure from the persisted
grant `consumed_capacity`, not request-body `current_gross_notional` or
`current_net_notional` fields. Accepted ledger inserts and grant-capacity
updates happen through one Postgres statement that locks the active grant row,
checks remaining reserved capacity, inserts the idempotent ledger row, and then
updates `paper_execution_grants.consumed_capacity`; duplicate conflicts or
capacity races return rejected decisions without consuming capacity. In
Postgres mode, `/v1/paper/orders/{id}/execute` now creates a
`PaperExecutionWorkItem` and processes it through `PaperExecutionQueueProcessor`
as `paper-execution-api`, completing the item as `completed` or `failed`.
Compose also deploys `paper-execution-worker`, a bounded Postgres-only queue
loop around the same processor for background processing. The next production
hardening step is fair scheduling across tenants.

Docker or Podman Compose sets `PAPER_LEDGER_DB_PATH=/data/paper-ledger.db` for
both the agent service and MCP server, backed by the `paper-ledger-data` volume.
For local development, `.env.example` uses `data/paper-ledger.db`, and database
files are ignored by Git.

## Next Product Step

Run the credential-gated model eval loop, review the redacted baseline summary,
deterministic triage report, and grade artifacts, and tune agent instructions or
tool descriptions from failed cases.
