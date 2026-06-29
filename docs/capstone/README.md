# Capstone Notes

Kaggle submission docs will live here.

Initial topics:

- Writeup outline.
- Video script.
- Feature-to-requirement mapping.
- Evidence checklist.
- Demo scenario list.

## Product North Star

The capstone should demonstrate a functioning portfolio research and paper-trading tool, not a demo-only product and not just a chat endpoint. Public capstone evidence may use offline-safe fixtures, but the architecture should support configured data adapters and persistent paper-trading state.

The product path should include:

- Agent-guided dashboard and pre-market briefing.
- Portfolio, watchlist, screener, research, signal, strategy, backtest, risk, report, and settings coverage.
- Paper-trading proposals with human approval.
- Real market, fundamental, sentiment, volatility, and macro data adapters where explicitly configured.
- Deterministic screeners and factor evidence before agent-written explanations.
- Policy-enforced refusal of live trading and broker-token access.

## Source Workflow Repurposing

Source-system scripts are treated as reference context. They should be inventoried and classified before implementation:

- Safe ideas become typed domain functions or offline-safe fixtures.
- Safe workflows become MCP tools with explicit policy tiers.
- Strategy explanations become RAG pattern cards with citations.
- Live, credentialed, account-specific, or direct-execution behavior is excluded.

The capstone evidence should show that useful workflow knowledge was preserved while the implementation became portable, testable, and paper-only.

## Product Scenario

Prompt:

```text
What should I review before market open?
```

Expected agent flow:

- Use the pre-market briefing tool or gather portfolio, watchlist, signal, research, and risk context.
- Identify whether the run uses configured data or offline-safe fixtures.
- Summarize exposure, watchlist candidates, signal regime, research notes, counterevidence, and risk switches.
- Suggest review actions only.
- Do not place orders, enable live strategies, retrieve broker tokens, or simulate execution.

## Product-Grade Evidence

The final submission should show that the same workflows can run with fixtures for reproducibility and with configured read-only providers for real use. Evidence should include:

- Screener run summary with hard gates, component scores, and multi-hit ranking.
- Factor-stack explanation with technical, fundamental, sentiment, volatility, macro, and portfolio-fit sections.
- Pattern-card citations from public references.
- Paper-trading proposal that remains draft or pending until approved.
- Simulated backtest result feeding a paper order proposal, approval-gated simulated fill, and paper accounting update.
- Audit log or trace showing policy boundaries and refusal of live-trading requests.
- Model-backed eval baseline showing positive workflow quality and negative safety refusal behavior when credentials are configured, backed by the redacted baseline summary and grade artifacts.
- Web console screenshots showing focused screener, strategy/backtest, paper approval, report, and provider-settings pages from safe workflows.
