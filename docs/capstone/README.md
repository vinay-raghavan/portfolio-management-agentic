# Capstone Notes

Kaggle submission docs will live here.

Initial topics:

- Writeup outline.
- Video script.
- Feature-to-requirement mapping.
- Evidence checklist.
- Demo scenario list.

## Product North Star

The capstone should demonstrate a web application for portfolio and paper-trading workflows, not just a chat endpoint. The first demo can remain backend/API-first, but the story should show a clear path to:

- Agent-guided dashboard and pre-market briefing.
- Portfolio, watchlist, screener, research, signal, strategy, backtest, risk, report, and settings coverage.
- Paper-trading proposals with human approval.
- Policy-enforced refusal of live trading and broker-token access.

## Source Workflow Repurposing

Source-system scripts are treated as reference context. They should be inventoried and classified before implementation:

- Safe ideas become typed domain functions or synthetic fixtures.
- Safe workflows become MCP tools with explicit policy tiers.
- Strategy explanations become RAG pattern cards with citations.
- Live, credentialed, account-specific, or direct-execution behavior is excluded.

The capstone evidence should show that useful workflow knowledge was preserved while the implementation became portable, testable, and paper-only.

## First Demo Scenario

Prompt:

```text
What should I review before market open?
```

Expected agent flow:

- Use the pre-market briefing tool or gather portfolio, watchlist, signal, research, and risk context.
- Explain that the data is synthetic demo data.
- Summarize exposure, watchlist candidates, signal regime, research notes, counterevidence, and risk switches.
- Suggest review actions only.
- Do not place orders, enable live strategies, retrieve broker tokens, or simulate execution.
