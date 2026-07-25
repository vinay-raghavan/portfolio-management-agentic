# TradePilot Sentinel Capstone Package

TradePilot Sentinel is a governed agentic trading workflow and risk-control
platform. The Kaggle submission demonstrates the system with safe fixture data,
read-only provider adapters, deterministic analysis, and approval-gated paper
simulation. Paper trading is the capstone evidence path, not the long-term
product boundary.

## One-Sentence Summary

TradePilot Sentinel turns portfolio, market, and risk evidence into
approval-gated paper-trading decisions for personal investors.

## Submission Assets

- [Capstone presentation](TradePilot-Sentinel-Capstone.pptx)
- [Kaggle writeup](writeup.md)
- [Video storyboard and narration](video-storyboard.md)
- [Submission checklist](submission-checklist.md)
- [Architecture source of truth](../architecture/README.md)
- [Media gallery assets](media/README.md)
- [Public-safe eval summary](evidence/eval-summary.json)

The cover image is
[01-cover.png](media/slides/01-cover.png). Architecture, workflow, safety,
product, and evaluation visuals are exported as individual 16:9 PNG files in
`media/slides`.

## Product Story

A user can ask the agent to review market conditions, screen candidates,
explain a factor stack, retrieve pattern citations, draft a strategy, request a
simulated backtest, create a paper order proposal, review approval state,
simulate an approved fill, and generate a redacted report. The agent does not
replace deterministic scoring or policy. It coordinates those services and
summarizes their outputs into a workflow the user can review.

The implemented evidence path is:

```text
intent -> evidence -> recommendation -> strategy -> backtest -> proposal
       -> human approval -> simulated fill -> accounting -> audit report
```

## Course Concepts Demonstrated

| Concept | Repository evidence | Submission evidence |
| --- | --- | --- |
| Google ADK agent | `apps/agent-service/app/agent.py` | Architecture and workflow slides; live prompt demo |
| MCP server | `apps/mcp-server/portfolio_mcp/server.py` | Architecture and safety slides |
| Security controls | `packages/policy` and contract tests | Safety slide; approval and refusal demo |
| Deployability | `compose.yaml`, Dockerfiles, GitHub Actions | Evaluation and deployment slide |
| Agents CLI evals and skills | eval datasets, wrapper, skills, and runbook | Public eval summary and video evidence |

## Evidence Status

- Product workflow screenshots: ready.
- Architecture and workflow diagrams: ready.
- Presentation deck and cover image: ready.
- Credentialed Gemini baseline: completed.
- Deterministic eval triage: passed with zero failures and zero critical
  failures.
- Latest `develop` CI at the start of this package: passed.
- Final narrated video and YouTube upload: pending.
- Kaggle writeup publication and Media Gallery upload: pending.
- Public GitHub visibility and release merge to `main`: pending human action.

## Safety Boundary

- Live order placement is unavailable.
- Live strategy enablement is unavailable.
- Broker trading-token access is forbidden.
- Provider secrets and credential values are never returned.
- Paper fills require persisted human approval.
- Forbidden compatibility traps are not registered as MCP tools.
- Evidence contains no real account data, private source, or local paths.

Future execution support is a separate production milestone. It requires
explicit broker isolation, stronger approvals, audit and observability review,
rollback, and release controls before any adapter can be enabled.

## Build Evidence Manifest

From the repository root:

```bash
uv run python scripts/build_capstone_evidence.py --json
```

The generated manifest reports product scope, workflow coverage, eval
readiness, container services, tracked media readiness, and remaining gaps
without recording credential values or local absolute paths.

## Verification

```bash
uv run pytest tests
cd apps/agent-service && uv run pytest tests/unit tests/integration
cd apps/web && npm run typecheck && npm run build
podman compose config --quiet
uv run python scripts/run_agent_evals.py triage --json
```

Model-backed eval generation remains credential-gated. Deterministic tests and
triage remain runnable without cloud credentials once the redacted grade
artifacts are available.
