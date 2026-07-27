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

The agent exposes only policy-classified tools. Local/unit imports use the
in-process adapter unless `AGENT_TOOL_TRANSPORT=mcp` is set. Production-like
Compose sets `AGENT_TOOL_TRANSPORT=mcp` and
`AGENT_MCP_URL=http://mcp-server:8081/mcp`, so ADK builds an MCP client
toolset filtered to the repository `EXPOSED_TOOL_NAMES` safe catalog. Public
MCP URLs are rejected by the agent tool factory; OAuth, approval, revocation,
and fill mutation endpoints remain protected human/API surfaces outside
model-visible MCP.

- Pre-market briefing: portfolio summary, watchlist snapshot, signal summary, research digest, risk review, and composed briefing.
- Screener and strategy drafting: synthetic momentum screener, fixture-backed deterministic screener, persisted paper strategy drafts, strategy history retrieval, and pending paper proposal.
- Provider checks: read-only provider catalog, provider health, configured import validation, guided source onboarding, configured import dry-run previews, import reconciliation, sanitized source templates, sanitized provider profiles and import-job history, provider refresh readiness, scheduled configured-provider refresh cycles, configured market/context imports, fixture market snapshots, and fixture universe members.
- FYERS integration API: protected human-facing `/v1/integrations/fyers/oauth/start`, `/callback`, `/status`, `/disconnect`, and `/v1/integrations/fyers/refresh` endpoints use `ActorContext`, return no provider tokens or PKCE verifier, keep token exchange disabled until the credential-vault worker is added, and refresh only read-only normalized fixture snapshots. OAuth, disconnect, and refresh are not model-visible MCP tools. When `PORTFOLIO_STORAGE_BACKEND=postgres`, sanitized `fyers_connections` metadata, optional opaque vault references, hashed single-use `fyers_oauth_sessions` state, protected `provider_refresh_jobs`, `provider_snapshot_envelopes`, and `broker_account_snapshots` are stored in tenant-scoped Postgres tables; token values, client secrets, trading tokens, PKCE verifiers, Yahoo fallbacks, and paper-ledger payloads are never persisted or returned.
- Market-data storage: fixture/provider snapshots, provider context records, and screener runs are cached in the same JSON shape returned by tools when `MARKET_DATA_DB_PATH` is configured.
- Pattern, factor, and recommendation evidence: universe listing, pattern search, pattern playbook retrieval, strategy evidence citations, factor-stack explanations, and read-only recommendation explanations that join provider refresh readiness, import-reconciliation gates, history, risk, and ledger context.
- Backtest, ledger, and report review: persisted simulated backtest requests, backtest history retrieval, deterministic results, readiness-gated paper order proposals, approval-gated simulated fills, paper positions, paper accounting, approval queue, readiness preflight report sections, redacted audit events, and read-only paper-trading reports.
- Web console workflows: `/console/overview` summarizes safe state, while `/console/workflows` and its paper-only POST endpoints expose focused screeners, strategy/backtest review, paper order proposals, human approval, simulated fills, reports, and provider settings with guided configured-source onboarding, configured-source setup, required env-key visibility, active adapter modes, setup-gap feedback, schema/template guidance, configured-file validation, dry-run import previews, import reconciliation, import-gate visibility on decision pages, provider profiles, full refresh orchestration, per-provider backoff state, and import-job feedback. The approval endpoint uses server-created `ActorContext` identity and explicit tenant metadata from trusted request headers; request JSON may include an approval note only and cannot supply or spoof `approved_by`.

Forbidden live-order and broker-token functions are not exposed to the agent.

Protected endpoints derive identity through `ActorContext`. Local/offline mode
accepts trusted `X-Actor-*` headers for deterministic tests. Production-like
deployments can enable signed OIDC bearer-token validation with
`OIDC_AUTH_ENABLED=true`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_JSON`,
`OIDC_TENANT_CLAIM`, and `OIDC_ROLES_CLAIM`; the dependency verifies issuer,
audience, signature, expiry, immutable `sub`, tenant claim, roles, and optional
`X-OIDC-Nonce` before any protected route reads or writes state. In Postgres
mode, storage paths that require an actor foreign key upsert `issuer + sub`
into `actor_identities` and use the returned UUID, while audit payloads keep
the immutable subject as the human-readable actor reference. This includes
Postgres-backed paper policy creation, batch proposal, grant approval, and
queued execution work-item records.

Set `PORTFOLIO_STORAGE_BACKEND=postgres` with `PORTFOLIO_DATABASE_URL` for
production-like container runs; the repository Compose file runs Alembic
migrations before the agent service starts. Set
`PORTFOLIO_STORAGE_BACKEND=sqlite` for local/offline compatibility. When
Postgres is selected, protected `/v1/paper/*` policy, batch, grant, revoke,
duplicate-idempotency detection, and accepted execution-decision flows use the
tenant-scoped `PostgresPaperExecutionStore` and never return the configured
database URL. Protected FYERS OAuth/status/disconnect routes similarly use the
tenant-scoped `PostgresFyersIntegrationStore` for connection metadata and
hashed OAuth state while leaving credential-vault token exchange disabled.
Connections may carry an internal `credential_ref`, but HTTP responses expose
only whether one is configured.
Protected FYERS refresh routes use that same store to persist refresh-job rows,
normalized quote envelopes, and broker account snapshots with signed quantities
and explicit errors.
The protected admin-only `/v1/credentials/vault/status` endpoint reports
redacted credential-vault readiness for `disabled`, `macos_keychain`, and `kms`
backends. It returns configured booleans and blocking reasons only; provider
secrets, access tokens, refresh tokens, and client secrets are not accepted or
returned. FYERS OAuth callbacks include this readiness and keep token exchange
disabled until a token-exchange worker is enabled.
Credential-vault write plans remain backend neutral and redacted: token payloads
are carried only in non-serializing domain objects, live-broker trading-token
payloads are rejected, and future Keychain/KMS writers must avoid command-line
secret delivery.
Protected `/v1/sessions/{session_id}/summary` routes persist only compact
session summaries and sanitized object references through
`PostgresSessionMemoryStore` in Postgres mode; local/offline mode keeps the same
TTL and deletion semantics in process memory without durable preference or raw
account retention.
When SQLite/local mode is selected, those HTTP contracts keep
their process-local deterministic fallback for API tests and offline
development. When
`PAPER_LEDGER_DB_PATH` is configured, strategy, backtest, and paper-ledger
tools use SQLite-backed state while individual stores are ported to Postgres.
The repository Compose file mounts `/data/paper-ledger.db` on a named volume
for local container runs.
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
Paper order proposal requests also persist a `paper-order-readiness-preflight/v1`
snapshot on ready orders and audit events, and return no draft order when the
preflight is blocked.

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
uv run python scripts/run_agent_evals.py triage --json
```

The wrapper still uses the official ADK path: `agents-cli eval generate`
followed by `agents-cli eval grade`. It also writes
`artifacts/evals/baseline-summary.json` inside this app directory with
preflight status, command return codes, artifact file names, and next actions
without credential values. The triage command writes
`artifacts/evals/triage-report.json` and classifies grade-result failures by
policy, provider-readiness, paper-trading, grounding, tool-trajectory, or
response-quality follow-up.

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
