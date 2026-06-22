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

## Safety Boundary

- Backtest output is simulated and not predictive.
- Paper order proposals do not create fills.
- Human approval is required before any future simulated execution.
- Approval cannot authorize live trading.
- Broker trading-token access and live order placement remain forbidden.
- Fixture stores use offline-safe data and do not require provider credentials.

## Next Product Step

The next implementation slice should replace the in-memory stores with structured persistence, then add approval-gated simulated fills and paper portfolio accounting. The MCP contract should remain stable while the backing store changes.
