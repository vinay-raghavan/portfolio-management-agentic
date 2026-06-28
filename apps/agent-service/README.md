# agent-service

ADK-based portfolio and paper-trading copilot for the capstone.

## Project Structure

```
agent-service/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Safe Tool Surface

The agent exposes only policy-classified tools:

- Pre-market briefing: portfolio summary, watchlist snapshot, signal summary, research digest, risk review, and composed briefing.
- Screener and strategy drafting: synthetic momentum screener, fixture-backed deterministic screener, persisted paper strategy drafts, strategy history retrieval, and pending paper proposal.
- Provider checks: read-only provider catalog, provider health, configured import validation, guided source onboarding, configured import dry-run previews, import reconciliation, sanitized source templates, sanitized provider profiles and import-job history, provider refresh readiness, scheduled configured-provider refresh cycles, configured market/context imports, fixture market snapshots, and fixture universe members.
- Market-data storage: fixture/provider snapshots, provider context records, and screener runs are cached in the same JSON shape returned by tools when `MARKET_DATA_DB_PATH` is configured.
- Pattern, factor, and recommendation evidence: universe listing, pattern search, pattern playbook retrieval, strategy evidence citations, factor-stack explanations, and read-only recommendation explanations that join provider refresh readiness, import-reconciliation gates, history, risk, and ledger context.
- Backtest, ledger, and report review: persisted simulated backtest requests, backtest history retrieval, deterministic results, paper order proposals, approval-gated simulated fills, paper positions, paper accounting, approval queue, redacted audit events, and read-only paper-trading reports.
- Web console workflows: `/console/overview` summarizes safe state, while `/console/workflows` and its paper-only POST endpoints expose focused screeners, strategy/backtest review, paper order proposals, human approval, simulated fills, reports, and provider settings with guided configured-source onboarding, configured-source setup, required env-key visibility, active adapter modes, setup-gap feedback, schema/template guidance, configured-file validation, dry-run import previews, import reconciliation, import-gate visibility on decision pages, provider profiles, full refresh orchestration, per-provider backoff state, and import-job feedback.

Forbidden live-order and broker-token functions are not exposed to the agent.

When `PAPER_LEDGER_DB_PATH` is configured, strategy, backtest, and paper-ledger
tools use SQLite-backed state. The repository Compose file mounts
`/data/paper-ledger.db` on a named volume for local container runs.
When `MARKET_DATA_DB_PATH` is configured, market snapshot, provider context,
and screener-run tools use SQLite-backed state. The repository Compose file mounts
`/data/market-data.db` on the same named volume for local container runs.
When `PROVIDER_CONFIG_DB_PATH` is configured, provider profile and import-job
tools use SQLite-backed metadata state. The repository Compose file mounts
`/data/provider-config.db` on the same named volume for local container runs.
Configured refreshes can import normalized market, universe, fundamentals,
sentiment, volatility, and macro records into the market-data database while
keeping job records free of resolved paths and raw provider payloads. Scheduled
refresh orchestration reports ready, stale, retry-due, and backoff state for the
configured providers. Dry-run import previews report normalized counts, target
stores, sample identifiers, warnings, and would-write status before those
refresh writes run. Import reconciliation compares preview counts, latest
refresh-job counts, and stored row counts so operators can confirm configured
stores are in sync before running configured screeners. Screeners and
recommendations consume reconciliation state as a confidence component and
paper-readiness gate; source-changed, store-mismatch, or needs-attention states
remove paper-order next actions until refresh/reconciliation is reviewed.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |

From the repository root, use the credential-aware wrapper before model-backed
evals:

```bash
uv run python scripts/run_agent_evals.py preflight --json
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The wrapper still uses the official ADK path: `agents-cli eval generate`
followed by `agents-cli eval grade`.

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

Deployment requires explicit human approval and a separate release gate. The
current capstone runtime is Docker or Podman Compose from the repository root.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
