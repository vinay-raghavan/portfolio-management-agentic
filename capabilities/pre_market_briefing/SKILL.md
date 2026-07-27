---
name: pre_market_briefing
description: Read-only pre-market briefing over portfolio, watchlist, signals, research digest, and risk state.
---

# Pre-Market Briefing Capability

Use this capability for read-only pre-market review, watchlist triage, signal context, research digest, and risk-state summaries before the trading day.

## Allowed tools

- `create_pre_market_briefing`
- `get_portfolio_summary`
- `get_research_digest`
- `get_risk_review`
- `get_signal_summary`
- `get_watchlist_snapshot`

## Context contract

Use portfolio summary, watchlist snapshot, signal summary, research digest, and risk review. Treat all context as read-only evidence and do not create strategy drafts, paper orders, approvals, fills, or live trades from this capability.

## Response contract

Return `PreMarketBriefingResponse` with market/readiness highlights, watchlist items, risk notes, review-only actions, paper-only boundary, and uncertainty for stale or missing data.
