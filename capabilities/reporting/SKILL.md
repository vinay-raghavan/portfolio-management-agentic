---
name: reporting
description: Read-only reporting over paper ledger, recommendations, approvals, fills, and redacted audit events.
---

# Reporting Capability

Use this capability for read-only paper-trading summaries, accounting review, approval status, fills, and redacted audit evidence.

## Allowed tools

- `generate_paper_trading_report`
- `get_approval_queue`
- `get_audit_events`
- `get_paper_portfolio_accounting`
- `list_paper_fills`
- `list_paper_orders`
- `list_paper_positions`

## Context contract

Use paper ledger, approval queue, redacted audit events, and paper accounting. Do not write report files or export raw audit payloads from this capability.

## Response contract

Return `ReportingResponse` with summary sections, redacted audit references, paper-only status, and explicit uncertainty for missing ledger data.
