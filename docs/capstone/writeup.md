# TradePilot Sentinel

**Track:** Agents for Business

## The Problem

Trading decisions rarely fail because one indicator is missing. They fail
because evidence is scattered, reasoning is hard to inspect, and automation can
move faster than the controls around it.

A candidate may look attractive technically while fundamentals, volatility,
macro conditions, portfolio concentration, or stale provider data argue
against it. Conventional dashboards expose those facts on separate pages and
leave the user to assemble the decision. A generic chat assistant can describe
the situation, but it should not invent market facts, bypass readiness checks,
or turn a conversational response into an uncontrolled financial action.

TradePilot Sentinel covers the decision workflow around the recommendation. It
combines agent coordination, deterministic analysis, explicit permissions,
human approval, and audit history in one system.

## The Solution

TradePilot Sentinel is an agentic trading workflow and risk-control platform.
For the Kaggle capstone, the system is demonstrated with offline-safe fixture
data, configured read-only provider adapters, and approval-gated paper
simulation.

A user can ask the agent to review market conditions, screen candidates,
explain a recommendation, draft a strategy, run a simulated backtest, create a
paper order proposal, review approvals, simulate an approved fill, and produce
a redacted report. Each step is visible, reviewable, and tied back to the
evidence that produced it.

The capstone deliberately stops at paper simulation. That is the evidence path
for this submission, not the permanent product boundary. Future execution
adapters would require broker isolation, stronger approvals, production
observability, audit review, rollback, and release controls. Those future
capabilities are not represented as implemented today.

## How The Agentic System Works

The React console and API clients send workflow requests to a FastAPI service
hosting a Google ADK agent. The agent interprets intent, chooses an explicit
workflow route, calls scoped tools, and synthesizes the result in plain
language.

The language model does not own trading facts or permissions. A streamable HTTP
MCP server exposes the safe tool catalog, while deterministic domain services
own provider validation, screener rules, factor scoring, recommendations,
backtests, paper-ledger transitions, readiness checks, reports, and audit
events. Forbidden capabilities such as live order placement and broker-token
access are not registered with the MCP server.

The model layer is configurable. Gemini is the default capstone provider, and
the adapter design also includes Claude, OpenAI-compatible, and Ollama paths.
The MCP and policy boundaries remain the same regardless of provider, so
changing the model cannot expand permissions.

## Decision Intelligence

TradePilot Sentinel combines six evidence families:

- Technical evidence such as trend, momentum, setup, and volatility.
- Fundamental evidence such as quality, value, growth, leverage, and earnings
  revisions.
- Sentiment evidence from news, investor measures, and contradiction signals.
- Volatility evidence including VIX context, regime, and a risk multiplier.
- Macro evidence including breadth, rates, event risk, and liquidity.
- Portfolio-fit evidence including concentration, exposure, provider
  readiness, and current risk state.

Typed provider contracts normalize inputs from fixtures or configured
read-only JSON sources. Hard gates run before weighted scoring. Import
reconciliation issues, stale data, missing strategy evidence, failed risk
checks, or unready backtest state can remove the paper-order next action.

Recommendations include supporting evidence, counterevidence, uncertainty,
citations, readiness state, and allowed next actions. Read-only pattern cards
add strategy context and references, while structured facts remain
authoritative. Retrieval helps the agent explain the decision; it does not
make the decision.

## The Governed Workflow

The primary scenario begins with a natural-language request to review a
candidate. The agent routes the request through the screener, factor,
provider-readiness, risk, and pattern tools. It explains the result and can
draft a strategy. A simulated backtest provides additional evidence before the
system creates a paper order proposal.

The proposal is saved as pending approval. A human must explicitly approve the
simulation. Only then can the MCP tool create a simulated paper fill. The paper
ledger updates positions and accounting and emits audit events with sensitive
details removed. A report brings the readiness snapshot, approval, fill,
accounting, risk state, and audit rows into one reviewable result.

The action tiers are simple:

- `read_only` tools gather portfolio, provider, screener, factor, and report
  evidence.
- `draft_only` tools create strategies, backtest requests, and paper proposals.
- `approval_required` tools require persisted human approval before simulation.
- `forbidden` actions are absent from the exposed tool catalog.

## Course Concepts Demonstrated

**Google ADK agent:** The coordinator uses explicit workflow-routing guidance
for pre-market review, provider readiness, candidate analysis,
recommendation-to-proposal, approval-gated fills, reporting, navigation, and
forbidden requests.

**MCP server:** Forty-nine safe tools are published through a streamable HTTP
server. Contract and container tests assert that the runtime catalog exactly
matches the approved set and excludes forbidden tools.

**Security:** Least-privilege tool registration, deterministic policy,
credential redaction, provider-path redaction, human approval, and audit events
create defense in depth beyond the model prompt.

**Deployability:** Docker Compose and Podman Compose start the web console,
agent service, MCP server, shared SQLite state, and optional Ollama profile.
GitHub Actions run contract tests, agent tests, the web build, container smoke
tests, and safe-tool verification. Release automation publishes images only on
release tags or explicit dispatch.

**Agents CLI skills and evals:** Reusable development skills define tests-first
implementation, security review, documentation synchronization, release gates,
and evaluation practices. The official ADK evaluation path uses
`agents-cli eval generate` followed by `agents-cli eval grade`.

## Evaluation

The Gemini baseline completed 15 credentialed inference cases covering both
successful workflows and forbidden-action requests. The evaluation combines an
LLM response-quality rubric with deterministic policy and tool-trajectory
metrics.

The recorded mean scores are:

- Response quality: **4.9167 out of 5**.
- Forbidden-action policy: **1.0000**.
- Workflow tool trajectory: **0.8000**.

Deterministic triage reported zero failures and zero critical failures. The
trajectory score points to a concrete follow-up: tighten routing so the agent
selects the preferred tool sequence more consistently. Three response-quality
judge outputs produced parse errors; they are retained as a known baseline
limitation.

Credential-free tests still verify imports, contracts, policy, persistence,
API behavior, web compilation, Compose configuration, and MCP tool exposure.

## Business Value

TradePilot Sentinel turns a chain of manual handoffs into a governed,
repeatable workflow. Analysts receive one evidence-backed explanation instead
of assembling disconnected screens. Risk reviewers can see why an action is,
or is not, eligible. Operators can inspect provider readiness and
reconciliation before trusting a recommendation. Every consequential
simulation leaves an approval and audit record.

The same architecture can support research desks, portfolio teams, and
individual systematic traders because the model provider, data adapters, and
agent client are replaceable while the policy and domain contracts remain
stable.

## What Comes Next

The next product milestones are richer provider integrations, scheduled data
quality monitoring, stronger portfolio optimization, expanded strategy and
backtest engines, calibrated eval datasets, and production observability.

Any future live execution milestone remains separate and high risk. It must
introduce broker-specific isolation, multi-party approval where appropriate,
strict position and loss limits, idempotency, reconciliation, kill switches,
incident response, and release approval before an execution adapter can be
registered.

TradePilot Sentinel's operating principle is simple: the model can recommend,
the system decides what is permitted, and a human controls the consequential
step.
