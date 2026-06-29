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

Docker or Podman Compose sets `PAPER_LEDGER_DB_PATH=/data/paper-ledger.db` for
both the agent service and MCP server, backed by the `paper-ledger-data` volume.
For local development, `.env.example` uses `data/paper-ledger.db`, and database
files are ignored by Git.

## Next Product Step

Run the credential-gated model eval loop, review the redacted baseline summary
and grade artifacts, and tune agent instructions or tool descriptions from
failed cases.
