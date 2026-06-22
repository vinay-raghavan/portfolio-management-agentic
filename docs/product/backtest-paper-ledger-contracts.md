# Backtest And Paper Ledger Contracts

This slice establishes the safe contract between research, simulation, and the future paper-trading ledger.

## Current Capabilities

- Draft an offline backtest request for a symbol, setup, and date window.
- Return deterministic simulated backtest metrics and closed simulated trades.
- Create a paper order proposal that remains `pending_approval`.
- List paper order proposals without fills.
- List fixture-backed paper positions for exposure review.
- Show pending human approvals.
- Show redacted audit events for paper-ledger actions.
- Persist paper orders, paper positions, approval requests, audit events, and the reserved simulated-fill table in SQLite when `PAPER_LEDGER_DB_PATH` is configured.

## Safety Boundary

- Backtest output is simulated and not predictive.
- Paper order proposals do not create fills.
- Human approval is required before any future simulated execution.
- Approval cannot authorize live trading.
- Broker trading-token access and live order placement remain forbidden.
- Fixture stores use offline-safe data and do not require provider credentials.
- Persisted rows contain paper-only proposals, approvals, fixture positions, and redacted audit payloads; no broker credentials or live account identifiers are stored.

## Runtime Storage

The default Python import path remains fixture-backed and in memory when no
database path is configured. Local and container runtimes can enable durable
paper-ledger state with `PAPER_LEDGER_DB_PATH`.

Docker or Podman Compose sets `PAPER_LEDGER_DB_PATH=/data/paper-ledger.db` for
both the agent service and MCP server, backed by the `paper-ledger-data` volume.
For local development, `.env.example` uses `data/paper-ledger.db`, and database
files are ignored by Git.

## Next Product Step

The next implementation slice should add approval-gated simulated fills and
paper portfolio accounting. The MCP contract should remain stable while fill
creation stays behind policy and human approval.
