---
name: risk_review
description: Read-only risk review over portfolio, watchlist, paper positions, accounting, and safety switches.
---

# Risk Review Capability

Use this capability to summarize exposure, concentration, paper-ledger state, and safety switches. It may recommend review or pause actions, but it must not alter risk settings.

## Allowed tools

- `get_paper_portfolio_accounting`
- `get_portfolio_summary`
- `get_risk_review`
- `get_watchlist_snapshot`
- `list_paper_orders`
- `list_paper_positions`

## Context contract

Use portfolio summary, paper ledger, risk state, and watchlist context. Cite missing data and stale state instead of inventing exposure.

## Response contract

Return `RiskReviewResponse` with risk factors, severity, uncertainty, recommended paper-only review actions, and any safety switch status.
