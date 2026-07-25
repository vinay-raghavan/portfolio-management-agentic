---
name: paper_proposal_execution
description: Proposal-only paper execution planning that can draft requests but cannot approve or simulate fills.
---

# Paper Proposal Execution Capability

Use this capability to prepare paper-only strategy drafts, backtest requests, and paper order proposals. It cannot approve a proposal, create a fill, place a live order, or bypass human review.

## Allowed tools

- `create_backtest_request`
- `create_paper_order_proposal`
- `create_paper_trade_proposal`
- `draft_paper_strategy`
- `get_approval_queue`
- `get_audit_events`
- `get_backtest_request`
- `get_backtest_result`
- `get_recommendation_explanation`
- `get_risk_review`
- `list_backtest_requests`
- `list_paper_orders`
- `list_strategy_drafts`

## Context contract

Use recommendation explanation, backtest history, strategy drafts, risk review, approval queue, and audit trail. Approval identity must come from the human-facing API, never from model output.

## Response contract

Return `PaperProposalExecutionResponse` with preflight status, proposal details, risk blockers, approval requirement, grant status if available, and no fill/approval mutation.
