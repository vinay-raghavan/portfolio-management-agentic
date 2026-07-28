# TradePilot Sentinel Video Storyboard

Target runtime: 4 minutes 40 seconds. Hard limit: 5 minutes.

Record at 1920x1080 or 2560x1440. Use desktop only. Keep browser zoom and font
size stable. Do not show `.env`, terminals containing credential values, cloud
billing pages, local absolute paths, or raw provider payloads.

## Shot List And Narration

### 0:00-0:20 — Product And Problem

**Visual:** `media/slides/01-cover.png`, followed briefly by
`media/slides/02-problem-value.png`.

**Narration:**

> TradePilot Sentinel is a governed agentic trading workflow platform. Trading
> decisions combine many signals, but most tools separate evidence, reasoning,
> and execution control. This system puts those controls into the workflow.

### 0:20-0:55 — Architecture

**Visual:** `media/slides/03-system-architecture.png`.

**Narration:**

> A FastAPI service hosts a Google ADK agent. The agent interprets intent and
> coordinates tools. Deterministic services own facts, scoring, policy,
> persistence, and audit state. The MCP server exposes only the approved tool
> catalog. Gemini is the default model, and the provider adapter also supports
> Claude, OpenAI-compatible endpoints, and Ollama without changing permissions.

### 0:55-1:25 — Agentic Request

**Visual:** Show the natural-language prompt and agent response or ADK trace for:

```text
What should I review before market open? Use portfolio, watchlist, signal,
research, and risk evidence. Do not create or execute an order.
```

**Narration:**

> This is not a direct dashboard query. The agent routes the request through a
> pre-market workflow, gathers portfolio, watchlist, signal, research, and risk
> context, then synthesizes review actions. It distinguishes fixture evidence
> from configured data and does not create an order.

### 1:25-2:00 — Screener And Recommendation

**Visual:** Open the Screener page, run the factor-gated candidate workflow,
then show `media/slides/04-decision-intelligence.png`.

**Narration:**

> The screener combines technical, fundamental, sentiment, volatility, macro,
> and portfolio-fit evidence. Provider freshness and import reconciliation are
> hard gates before scoring. The recommendation includes supporting evidence,
> counterevidence, citations, uncertainty, and only the next actions permitted
> by policy.

### 2:00-3:05 — Strategy To Approved Simulation

**Visual:** Show the Strategies and Backtests page. Draft a strategy, create a
simulated backtest, and create a paper order proposal. Move to Paper Approvals,
approve the simulation, and simulate the approved fill.

**Narration:**

> The agent can create draft-only strategy and backtest state. Before a paper
> proposal is accepted, deterministic readiness checks validate provider data,
> reconciliation, strategy evidence, backtest history, risk, and paper policy.
> The proposal remains pending until a human explicitly approves it. Only an
> approved proposal can become a simulated fill.

Pause briefly on the approval state before pressing the simulation control.

### 3:05-3:35 — Report And Audit

**Visual:** Open Reports and show the approval, simulated fill, readiness
preflight, accounting, and redacted audit rows. Use
`media/product/approval-gated-paper-report.png` as backup.

**Narration:**

> The result is reviewable. The paper ledger records the approval, simulated
> fill, positions, accounting, and redacted audit events. Live trading and
> broker-token access remain unavailable.

### 3:35-4:05 — Safety

**Visual:** `media/slides/06-safety-model.png`.

**Narration:**

> Safety is enforced outside the language model. Read-only and draft tools are
> scoped. Consequential simulation requires approval. Live orders, broker
> tokens, credential disclosure, and approval bypass are absent from the MCP
> catalog, so a weaker or compromised model cannot call them.

### 4:05-4:30 — Evals And Deployability

**Visual:** `media/slides/08-evaluation-deployability.png`.

**Narration:**

> Fifteen Gemini inference cases completed with all 45 metric results valid.
> Response quality averaged 5.0 out of 5, forbidden-action policy scored 1.0,
> and workflow trajectory scored 1.0. Deterministic triage found zero failures
> and zero critical failures. Docker or Podman Compose runs the web, ADK
> service, MCP server, Postgres, Redis, migrations, and the protected paper
> worker, while GitHub Actions verifies contracts, containers, and safe tool
> exposure.

### 4:30-4:40 — Close

**Visual:** `media/slides/09-capstone-conclusion.png`.

**Narration:**

> The model can recommend. The system decides what is permitted. A human
> controls the consequential step.

## Recording Evidence Checklist

- The title and product name read `TradePilot Sentinel`.
- The agentic prompt and multi-tool result are visible.
- At least one tool trajectory or agent trace is visible.
- The screener shows multi-factor evidence and readiness.
- The proposal, human approval, simulated fill, and audit report appear in order.
- The live-trading block is visible at least once.
- Docker or Podman deployability and eval results are stated.
- Total runtime is 5 minutes or less.
- The final upload is public or unlisted on YouTube and attached to the Kaggle
  Media Gallery.
