# TradePilot Sentinel

Agentic trading workflow and risk-control system for the Kaggle AI Agents
capstone.

This repository is self-contained. Implementation should use documented API
contracts, scoped tools, configured data adapters, offline-safe fixtures, and
explicit safety policy.

## Current State

- ADK prototype scaffolded in `apps/agent-service`.
- Platform-neutral policy, domain, model-provider, and agent-platform contracts started.
- MCP-style safe portfolio tools started in `apps/mcp-server` with streamable HTTP runtime support.
- Pre-market briefing workflow composes synthetic portfolio, watchlist, signal, research, and risk context.
- Product data foundation adds fixture/configured universes, configured fundamentals, sentiment, volatility, macro/regime context, deterministic screener runs, provider refresh readiness and import-reconciliation evidence, pattern-card retrieval, citation-backed strategy evidence, and factor-stack explanations.
- Provider adapter contracts expose fixture defaults, configured read-only JSON market-data, universe, fundamentals, sentiment, volatility, and macro adapters, provider catalog, health, import validation, market snapshot, and universe-member tools.
- FYERS read-only MCP fixtures expose connection health, quotes, OHLCV history,
  market depth, instrument metadata, option chains, and normalized account
  snapshots with exchange-qualified symbols, explicit unavailable responses,
  signed quantities, funds, and provenance while keeping OAuth, credentials,
  provider administration, and broker mutations outside the model-visible
  surface.
- Protected FYERS human-facing API contracts are available for
  `/v1/integrations/fyers/oauth/start`, `/callback`, `/status`,
  `/disconnect`, and `/v1/integrations/fyers/refresh` (plus the
  `/oauth/refresh` compatibility alias). They require server-created
  `ActorContext`, generate OAuth state and PKCE challenge without returning a
  verifier, keep callback token exchange disabled until a credential vault is
  wired, and refresh only through the read-only normalized FYERS fixture with
  no Yahoo fallback, broker mutation, provider token, or paper-ledger mixing.
  In production-like Postgres mode, sanitized connection metadata and hashed
  OAuth session state are stored tenant-scoped in Postgres; provider tokens,
  client secrets, trading tokens, and PKCE verifiers are never persisted.
  Protected refreshes also persist read-only provider refresh-job rows,
  provider snapshot envelopes, and broker account snapshots without converting
  provider errors into empty holdings or mixing FYERS data into the paper
  ledger.
- Recommendation explanations join screener/factor evidence, provider refresh readiness, import-reconciliation gates, strategy history, backtest history, risk gates, paper-ledger state, citations, and allowed next actions into one read-only decision record.
- Paper-trading reports return read-only review summaries with readiness preflight review sections, redacted audit exports, paper orders, approvals, fills, accounting, risk state, and optional recommendation context.
- Strategy, backtest, and paper-ledger contracts persist paper strategy drafts and backtest request history, return offline results, require a ready recommendation preflight before paper order proposals enter approval, keep approval and simulated-fill mutation on protected human/API paths, update paper positions/accounting, expose approval queues, and emit redacted audit events with the readiness snapshot.
- Bounded paper-execution domain contracts define disabled-by-default policy
  ceilings, proposed paper batches, authenticated-human execution grants,
  deterministic grant/order decisions, idempotency, quote freshness,
  kill-switch, cash, and limit checks while keeping fills paper-only and
  structurally separate from FYERS/live-broker operations.
- Postgres paper-execution storage maps those protected contracts to
  tenant-scoped policy, batch, grant, and ledger tables, including an Alembic
  migration for explicit policy symbols and fail-closed rejection of
  FYERS/credential payload contamination.
- Protected paper-execution HTTP contracts are available under `/v1/paper/*`
  for API validation and production-like Postgres runtimes: admin policy
  creation, analyst batch proposals, approver-bound grants/revocation, and
  execution-under-grant decisions derive identity and explicit tenant scope from
  trusted `ActorContext` headers, reject body-spoofed approver fields, and use
  the tenant-scoped Postgres paper execution store when
  `PORTFOLIO_STORAGE_BACKEND=postgres`. The Postgres path
  enqueues durable `PaperExecutionWorkItem` records and processes them through
  the standalone deterministic `PaperExecutionQueueProcessor`, giving the API
  and deployed `paper-execution-worker` the same fail-closed execution
  boundary. Accepted Postgres fills lock the active grant row and update
  consumed capacity only after the idempotent ledger insert succeeds, so
  duplicate or reserved-capacity races reject without consuming grant capacity.
  The worker can process `PORTFOLIO_TENANT_IDS` in round-robin order so one
  busy tenant does not monopolize the bounded local worker loop, and Redis can
  persist the distributed scheduling cursor plus short-lived failure backoff.
  Worker JSON summaries expose backed-off tenant workers and the sanitized
  schedule-state backend, and operators can run a read-only health snapshot
  without claiming queue items.
- Market-data persistence stores fixture/configured-provider market snapshots, provider context snapshots, and screener runs in the same JSON payload shape returned by the tools when `MARKET_DATA_DB_PATH` is configured.
- Provider configuration profiles and import-refresh jobs persist sanitized validation and execution summaries when `PROVIDER_CONFIG_DB_PATH` is configured. Configured source templates, guided onboarding, dry-run import previews, and import reconciliation provide synthetic, adapter-valid JSON shapes, live validation state, setup gaps, refresh readiness, normalized counts, target stores, stored row counts, and safe next actions for market, universe, fundamentals, sentiment, volatility, and macro inputs. Configured refreshes can also import normalized records into the SQLite data store behind `MARKET_DATA_DB_PATH`. Scheduled refresh orchestration reports ready, stale, retry-due, and backoff readiness without resolved local file paths or raw provider payloads.
- Model-backed eval infrastructure is credential-gated through `scripts/run_agent_evals.py`, which preflights `agents-cli eval generate` and `agents-cli eval grade`, writes redacted baseline summaries, and produces deterministic triage reports for grade-result failures without printing secret values. The eval config combines an LLM response-quality rubric with deterministic forbidden-action and workflow-tool-trajectory code metrics. A manual GitHub Actions workflow can run the credentialed baseline and upload ignored eval artifacts.
- Capstone evidence manifest generation is available through `scripts/build_capstone_evidence.py`; it summarizes deterministic verification, container services, implemented workflow evidence, eval baseline status, eval submission readiness, and remaining submission gaps without local paths or secret values.
- Agent workflow-routing guidance is embedded in the ADK instruction and eval rubric so pre-market, provider-readiness, candidate explanation, recommendation-to-paper-order, reporting, feature-navigation, and forbidden-action requests have explicit safe tool paths before the first credentialed baseline, while approval/fill mutations route to protected human/API paths outside model-visible MCP. Model-facing MCP tool descriptions now name policy tiers and high-risk workflow sequencing constraints.
- Web console is available in `apps/web`, backed by `/console/overview` and `/console/workflows` endpoints. It includes focused pages for screeners, strategy/backtest review, paper approvals, reports, and provider settings with paper-order readiness preflight cards, guided configured-source onboarding, required env-key visibility, active adapter modes, setup-gap feedback, schema/template guidance, configured-file validation, dry-run import previews, import reconciliation, import-gate visibility on decision pages, provider profiles, refresh readiness, full-refresh controls, per-provider backoff state, and import-job feedback.
- Storage mode is explicit through `PORTFOLIO_STORAGE_BACKEND`. Root Compose defaults to `postgres` for production-like testing and runs Alembic migrations before app services start. Local/offline app runs may set `PORTFOLIO_STORAGE_BACKEND=sqlite`; SQLite-backed paper-ledger persistence is available through `PAPER_LEDGER_DB_PATH`, market-data/provider-context/screener-run persistence through `MARKET_DATA_DB_PATH`, and provider profile/import-job metadata through `PROVIDER_CONFIG_DB_PATH`.
- Docker or Podman Compose runs the agent service, MCP server, web console, and optional Ollama profile.
- A public-safe capstone package includes a presentation deck, 16:9 architecture and workflow visuals, selected product screenshots, a redacted eval summary, a Kaggle writeup, and a sub-five-minute video storyboard under `docs/capstone`.
- No copied portfolio data.
- No broker trading credentials.
- No live trading.
- Gitflow-style branching is enabled: `main` is release-only, `develop` is the integration branch, and active work happens on topic branches from `develop`.

## Repository Intent

The project is a functioning agentic trading workflow platform. The Kaggle demo
uses paper trading and simulation as the evidence path, not the product
boundary. The system should support configured data providers, deterministic
analysis, explainable strategy evidence, a persistent paper-trading ledger, and
policy-controlled agent workflows while live execution remains disabled until
broker, approval, audit, and release controls are designed and enabled.

## North Star

The target product is a governed agentic trading workflow application. It should
cover dashboard, portfolio, watchlist, screeners, research, signals, strategies,
backtests, risk, paper trades, reports, and settings while making every major
capability reachable through agent workflows. The current release demonstrates
those controls through paper simulation; future execution adapters remain a
separate production milestone.

Source-system scripts and workflows are reference material only. Useful logic should be rewritten as typed domain functions, MCP tools, scheduled jobs, RAG pattern cards, evals, or UI flows with offline-safe fixtures and policy tests. Live-account assumptions, broker-token access, direct execution paths, and local state should not be imported.

Primary constraints:

- The current release permits paper trading and simulation only.
- All major app features should be reachable through agent workflows.
- Broker/provider credentials may be used only for data fetching, never live order execution.
- Private source, local paths, and real financial data are excluded from the repo.
- Docker or Podman Compose is the first deployment target.
- Gemini is the first model provider, but the design must support other hosted and local providers such as Claude, OpenAI-compatible APIs, and Ollama later.
- ADK is the first capstone runtime, but the reusable tool, policy, skill, and eval layers must remain portable to Codex, Claude Code, and generic MCP clients.

## Architecture Overview

At a high level, the model coordinates intent and explanation while
deterministic services own facts, policy, routing, persistence, and audit
state.

```mermaid
flowchart LR
    U["User / Web console"] --> API["FastAPI agent service"]
    API --> ROUTE["Harness router<br/>route decisions, context evaluation,<br/>response validation"]
    ROUTE --> MODEL["Model provider adapter<br/>Gemini, Ollama, Claude,<br/>OpenAI-compatible"]
    ROUTE --> MCP["MCP policy server<br/>route-scoped safe tools"]
    MCP --> DOMAIN["Deterministic domain services<br/>screeners, risk, recommendations,<br/>backtests, paper ledger"]
    DOMAIN --> DB["State stores<br/>Postgres production-like default<br/>SQLite local/offline fallback"]
    DOMAIN --> PROVIDERS["Read-only provider adapters<br/>fixtures, JSON files,<br/>FYERS normalized data fixtures"]
    ROUTE --> AUDIT["Evaluator and audit evidence<br/>ContextPack, ResponseEvaluator,<br/>evals and CI artifacts"]

    MODEL -. "synthesis only" .-> ROUTE
    PROVIDERS -. "no credentials in prompts" .-> DOMAIN
    DOMAIN -. "paper-only mutations" .-> DB
```

The safety invariant is intentionally simple: models may explain and propose,
but only policy-classified tools and deterministic services can read data,
write paper-only state, or record audit events. Live trading and broker trading
tokens remain structurally forbidden.

## Planned Structure

- `apps/agent-service`: ADK coordinator and sub-agent service.
- `apps/mcp-server`: MCP tool server and policy enforcement boundary.
- `apps/web`: React console for policy-controlled trading workflows.
- `packages/policy`: Shared action-tier and safety policy logic.
- `packages/model-provider`: Model provider configuration and adapter contracts.
- `packages/agent-platform`: Agent runtime and coding-agent handoff contracts.
- `packages/domain`: Shared typed contracts for portfolio, signals, strategy, and risk concepts.
- `packages/evals`: Agent eval datasets, rubrics, and trajectory checks.
- `packages/shared`: Cross-service utilities when needed.
- `docs`: Architecture, capstone, decisions, tool catalog, and safety docs.
- `infra`: Container and future deployment assets.
- `tests`: Contract, security, and integration tests.
- `demo`: Offline-safe fixtures and public demo scenarios only.
- `references`: Public-safe reference policy and approved public links.

## Capstone Submission

The submission package is documented in `docs/capstone/README.md`. It includes:

- `TradePilot-Sentinel-Capstone.pptx` with speaker notes.
- 16:9 cover, architecture, decision, workflow, safety, product-evidence, and evaluation images.
- A Kaggle writeup under the 2,500-word limit.
- A timed storyboard for the required public video of five minutes or less.
- A public-safe eval summary and final submission checklist.

Remaining external steps are recording and publishing the video, merging the release into `main`, completing the secret and history scan, making the repository public, and creating the Kaggle Writeup and Media Gallery.

## Verification

Root safety and contract tests:

```bash
uv run pytest tests
```

ADK app tests:

```bash
cd apps/agent-service
agents-cli install
uv run pytest tests/unit tests/integration
```

Without Gemini credentials, model-streaming tests are skipped. Credential-free tests still verify imports, server startup, invalid request handling, feedback, and safe tool exposure.

Model-backed eval readiness from the repo root:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

Credentialed eval run:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The wrapper writes `apps/agent-service/artifacts/evals/baseline-summary.json`
by default. The summary records preflight status, command return codes, trace
and grade-result file names, and next actions without secret values. Generated
eval artifacts are ignored by Git.

Credential-free deterministic triage:

```bash
uv run python scripts/run_agent_evals.py triage --json
```

The triage report writes `apps/agent-service/artifacts/evals/triage-report.json`
and classifies failed eval cases by policy, provider-readiness, paper-trading,
grounding/citation, tool-trajectory, or response-quality follow-up. The
`workflow_tool_trajectory_policy` metric checks expected tool calls and ordering
for key workflow cases after traces are generated.

Capstone evidence manifest:

```bash
uv run python scripts/build_capstone_evidence.py
```

The manifest writes to `artifacts/capstone/evidence-manifest.json` by default.
Use `--json` to print it for another tool. For submission, the target eval gate
is `eval_baseline.submission_readiness.status=ready_for_capstone_submission`
and the tracked media gate is `submission_assets.status=ready`.

## Container Runtime

Use either Docker Compose or Podman Compose from the repo root:

```bash
docker compose up --build
```

```bash
podman compose up --build
```

The default services expose:

- Agent service: `http://localhost:8000`
- MCP server: `http://localhost:8081/mcp`
- Web console: `http://localhost:3000`
- Paper execution worker: background service, no public port
- Postgres: `localhost:${POSTGRES_PORT:-5432}`
- Redis: `localhost:${REDIS_PORT:-6379}`

Read-only paper-worker health/backoff telemetry:

```bash
uv run python scripts/process_paper_execution_queue.py \
  --tenant-ids "$PORTFOLIO_TENANT_IDS" \
  --worker-id "${PAPER_EXECUTION_WORKER_ID:-paper-execution-worker-1}" \
  --redis-url "$REDIS_URL" \
  --health
```

The health output is redacted, model-invisible, and does not claim or process
paper execution queue items.

Deployment topology:

```mermaid
flowchart TB
    Browser["Browser<br/>localhost:3000"] --> Web["web service<br/>React/Vite preview<br/>port 3000"]
    Web --> Agent["agent-service<br/>FastAPI + ADK<br/>port 8000"]
    Agent --> MCP["mcp-server<br/>Streamable HTTP MCP<br/>port 8081/mcp"]
    Agent --> Model["Configured model runtime<br/>Gemini API or local Ollama gateway"]
    Agent --> PaperQueue["paper_execution_work_items<br/>durable queue"]
    PaperWorker["paper-execution-worker<br/>round-robin tenant queue processor"] --> PaperQueue
    PaperWorker --> Postgres
    MCP --> Domain["Domain packages<br/>policy, screeners, recommendations,<br/>paper ledger, provider adapters"]
    Agent --> Domain
    Domain --> Volume["paper-ledger-data volume<br/>/data/*.db SQLite local stores"]
    Domain --> Postgres["postgres service<br/>Postgres 16<br/>production-like state target"]
    Migrations["migrations job<br/>Alembic upgrade head"] --> Postgres
    Redis["redis service<br/>jobs, queues, rate limits,<br/>short-lived cache"] --> Agent
    Redis --> MCP
    Redis --> PaperWorker
    Domain --> LocalData["Ignored local data files<br/>optional JSON provider inputs"]
    NativeOllama["Native Ollama on host<br/>host.containers.internal:11434"] -. "private gateway" .-> Agent
    OllamaProfile["optional compose ollama profile<br/>not public by default"] -. "model storage" .-> OllamaVolume["ollama-data volume"]

    subgraph Compose["Docker or Podman Compose"]
        Web
        Agent
        PaperWorker
        MCP
        Migrations
        Redis
        Volume
        Postgres
        OllamaProfile
        OllamaVolume
    end
```

Compose mode sets `PORTFOLIO_STORAGE_BACKEND=postgres` by default and treats
Postgres plus Alembic as the production-like storage path. The service runtime
profile redacts database and Redis credentials in status/readiness payloads and
fails production-like readiness when Postgres is not selected or the database
URL is missing. SQLite paths remain available for local/offline compatibility
while individual stores are ported: `PAPER_LEDGER_DB_PATH`,
`MARKET_DATA_DB_PATH`, and `PROVIDER_CONFIG_DB_PATH`. Compose defaults for
those compatibility stores are `/data/paper-ledger.db`,
`/data/market-data.db`, and `/data/provider-config.db` on the
`paper-ledger-data` volume; the agent-service-local `.env.example` keeps
relative `../../data/*.db` paths for fast credential-free tests.

The production-like storage target is Postgres, with tenant-scoped tables for
sessions, FYERS/provider connections, normalized snapshots, research documents,
paper policies, grants, ledger entries, model-usage telemetry, and immutable
audit events. SQLite remains useful for offline capstone mode and fast
deterministic tests while Postgres-backed contract tests are introduced
feature-by-feature.

Protected FYERS connection state is Postgres-backed when
`PORTFOLIO_STORAGE_BACKEND=postgres`: the API stores sanitized
`fyers_connections` rows plus hashed, single-use `fyers_oauth_sessions` rows.
The persisted records include provider, user hash, read-only scopes, status,
daily auth expiry, PKCE challenge, and timestamps only; credential references
remain null until the credential-vault worker lands, and tokens/verifiers are
rejected from the storage contract. Local/offline mode keeps the process-local
fallback so fixture-only API tests remain credential-free.

FYERS refresh results use the same Postgres backend in production-like mode.
The protected refresh endpoint records `provider_refresh_jobs`,
`provider_snapshot_envelopes`, and `broker_account_snapshots` with source,
freshness, provenance, signed quantities, funds, and explicit errors. Missing
provider data stays an error on the refresh job; it is not replaced with Yahoo
fallback data, empty holdings, zero funds, or paper-ledger state.

Agent session memory is intentionally compact and short-lived. The runtime
contract stores only a sanitized task summary plus references to authoritative
objects, scoped by tenant and actor identity. Defaults are a 2-hour idle TTL and
24-hour absolute TTL, with immediate tenant-scoped deletion support. Raw FYERS
or account payloads, provider secrets, private notes, and long-term preferences
are rejected before persistence.

Postgres schema changes live under `infra/db/alembic`. To validate migrations
without touching a database, generate offline SQL:

```bash
uv run alembic -c infra/db/alembic.ini upgrade head --sql
```

To start only the database and apply migrations locally:

```bash
docker compose up --build postgres redis migrations
```

```bash
podman compose up --build postgres redis migrations
```

The Compose database URL is
`postgresql+psycopg://portfolio:portfolio-dev-password@postgres:5432/portfolio_agentic`.
For host-local commands, `.env.example` uses the same database on
`localhost:5432`. Production deployments must override the password and should
provide `PORTFOLIO_DATABASE_URL` through the deployment secret manager rather
than committing environment files.

The agent service exposes redacted storage readiness at:

```bash
curl "http://localhost:8000/v1/storage/status?require_production_like=true"
```

The response reports the selected backend, migration requirement, redacted
database/Redis URLs, SQLite compatibility paths, and readiness blocking
reasons. It never returns raw database or Redis credentials.

Curated research retrieval remains fixture-backed by default:

```bash
PORTFOLIO_RESEARCH_STORE_BACKEND=fixture
```

To use tenant-scoped Postgres full-text retrieval through the MCP
`search_curated_research` tool, set both:

```bash
PORTFOLIO_RESEARCH_STORE_BACKEND=postgres
PORTFOLIO_RESEARCH_TENANT_ID=<tenant-uuid>
```

Postgres research mode also requires `PORTFOLIO_DATABASE_URL`. If the tenant id
or database URL is missing, the MCP tool returns an explicit configuration
error and does not fall back to fixture hits. Runtime database failures return a
redacted unavailable response.

The default data-provider mode is offline-safe fixtures. To enable configured
read-only market-data, universe, fundamentals, sentiment, volatility, and macro
adapters, set:

```bash
PORTFOLIO_MARKET_DATA_PROVIDER=json_file
PORTFOLIO_MARKET_DATA_JSON_PATH=data/market-snapshots.json
PORTFOLIO_UNIVERSE_PROVIDER=json_file
PORTFOLIO_UNIVERSE_JSON_PATH=data/universes.json
PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file
PORTFOLIO_FUNDAMENTALS_JSON_PATH=data/fundamentals.json
PORTFOLIO_SENTIMENT_PROVIDER=json_file
PORTFOLIO_SENTIMENT_JSON_PATH=data/sentiment.json
PORTFOLIO_VOLATILITY_PROVIDER=json_file
PORTFOLIO_VOLATILITY_JSON_PATH=data/volatility.json
PORTFOLIO_MACRO_PROVIDER=json_file
PORTFOLIO_MACRO_JSON_PATH=data/macro.json
```

The JSON files are local-only and should stay under ignored data paths. Market
data may contain either one snapshot object, a list of snapshots, or
`{"snapshots": [...]}` using the same `MarketDataSnapshot` payload shape
returned by the MCP tools. Universe data may contain one universe object, a
list of universes, or `{"universes": [...]}` using the same
`UniverseDefinition` payload shape returned by the provider tools.
Fundamentals data may contain one fundamentals object, a list of objects, or
`{"fundamentals": [...]}` with `symbol`, `as_of`, and factor metric keys such
as `quality_score`, `value_score`, `growth_score`,
`earnings_revision_score`, and `leverage_score`. Sentiment data may contain
one sentiment object, a list, or `{"sentiment": [...]}` with metrics such as
`news_score`, `investor_score`, and `contradiction_score`. Volatility data may
contain one volatility object, a list, or `{"volatility": [...]}` with metrics
such as `india_vix`, `vix_change_pct`, `regime_score`, and `risk_multiplier`.
Macro data may contain one macro object, a list, or `{"macro": [...]}` with
metrics such as `market_regime_score`, `breadth_score`,
`rate_pressure_score`, `event_risk_score`, and
`liquidity_condition_score`.
Configured screeners remain read-only and paper-only; they rank candidates
from configured market, fundamental, sentiment, volatility, macro metrics, and
provider refresh readiness, and do not create trades. Import reconciliation is
also included in screener scoring, candidate gates, recommendation risk gates,
and allowed next actions; source-changed, store-mismatch, or needs-attention
states block paper-order next actions until refresh/reconciliation is reviewed.

Use `list_provider_source_onboarding`, `list_provider_import_previews`,
`list_provider_import_reconciliation`, `validate_data_provider_imports`, or the
provider settings page to check configured JSON files before running screeners
or refreshes. Guided onboarding links schema templates, validation, setup gaps,
refresh readiness, and safe next actions. Dry-run previews parse configured
sources into normalized record counts, target stores, sample identifiers,
warnings, and would-write status without initializing storage or writing cache
rows. Reconciliation compares preview counts, latest sanitized refresh-job
counts, and stored row counts to report pending refresh, in-sync,
source-changed, store-mismatch, or needs-attention states without exposing local
paths, database paths, raw payloads, or credential values. Validation reports
provider mode, missing environment keys, shape errors, and sample identifiers
without returning local file paths or credential values.

Use `list_provider_profiles`, `get_provider_refresh_readiness`,
`refresh_provider_import_profile`, `run_provider_refresh_schedule`, and
`list_provider_import_jobs` to persist and review provider profile readiness.
Refresh jobs validate configured sources, store sanitized status, counts,
sample identifiers, env key names, import metadata, retry/backoff state, and
stale-data readiness, and import configured market, universe, fundamentals,
sentiment, volatility, and macro records into structured SQLite tables when
`MARKET_DATA_DB_PATH` is configured. They do not store raw provider payloads or
resolved local paths.

The local Ollama runtime is model-profile driven. The first pilot model is
`llama3.1:8b`; containers should use a private native host gateway unless a
separate deployment profile says otherwise:

```bash
ollama pull llama3.1:8b
LLM_PROVIDER=ollama \
LLM_MODEL=llama3.1:8b \
OLLAMA_BASE_URL=http://host.containers.internal:11434 \
podman compose up --build
curl http://localhost:8000/v1/models/ollama/status
curl http://localhost:8000/v1/models/tuning/status
curl -X POST http://localhost:8000/v1/models/tuning/evaluate-candidate \
  -H 'content-type: application/json' \
  -d '{
    "baseline": {
      "provider": "gemini",
      "model": "incumbent",
      "safety_pass_rate": 1.0,
      "core_task_success_rate": 0.96,
      "mean_response_score": 4.5,
      "applicable_trajectory_score": 1.0,
      "p50_total_tokens": 10000,
      "p95_latency_ms": 4000,
      "judge_error_count": 0
    },
    "candidate": {
      "provider": "ollama",
      "model": "llama3.1:8b",
      "safety_pass_rate": 1.0,
      "core_task_success_rate": 0.97,
      "mean_response_score": 4.6,
      "applicable_trajectory_score": 1.0,
      "p50_total_tokens": 10900,
      "p95_latency_ms": 4700,
      "judge_error_count": 0
    }
  }'
curl http://localhost:8000/v1/models/usage/summary
```

If you use the optional Compose-managed Ollama service instead of a native host
daemon, pre-pull the required model into the private `ollama-data` volume before
starting model traffic:

```bash
OLLAMA_PREPULL_MODEL=llama3.1:8b \
podman compose --profile ollama run --rm ollama-model-prepull
```

The Ollama profile does not publish port `11434`; app containers should still
use private container networking or the native host gateway.

The status endpoint uses configured inventory in CI/offline mode or a short
private Ollama `/api/tags` probe at runtime. It does not send prompts; it
reports route budgets, queue limits, capability readiness, model availability,
and model-digest verification state.

Prompt, routing, retrieval, and budget tuning are the initial optimization
surface. Fine-tuning remains disabled until the eval harness has enough labeled
examples and a repeatable residual failure class.
Candidate model promotion is model-independent: the tuning gate compares any
7B/8B/local/hosted candidate to the incumbent baseline using safety, core task
success, response score, applicable trajectory, judge-error, token, and latency
thresholds without storing prompts or responses.
`/v1/models/tuning/status` exposes the active provider/model, candidate list,
development and sealed holdout set names, disabled fine-tuning gate, and
promotion thresholds. It does not return provider keys, raw prompts, raw
responses, or eval example payloads.
`/v1/models/tuning/evaluate-candidate` applies the same gate to aggregate
baseline/candidate metrics. The candidate model must be allowlisted by
`MODEL_TUNING_CANDIDATES`; unknown candidates fail with
`model_candidate_not_allowed`, weak metrics return a non-promotable decision
with deterministic blocking reasons, and raw prompt/response/secret-shaped
payloads fail before schema parsing.
`/v1/models/usage/events` records provider-neutral model usage metrics only:
prompt-token count, output-token count, route, tool calls, queue wait, latency,
retry count, and request id. In offline/SQLite mode the API uses an in-process
rolling buffer; when `PORTFOLIO_STORAGE_BACKEND=postgres` it writes the same
metric-only event to tenant-scoped `model_usage_events` through Alembic-managed
Postgres storage. The API rejects extra payload/content fields and
`/v1/models/usage/summary` returns aggregate token, latency, queue, retry, and
budget-violation summaries for tuning comparisons. Raw prompts, raw responses,
provider credentials, and broker tokens are never accepted as telemetry fields
or stored in this table.

## CI/CD

GitHub Actions are split into CI and CD:

- CI runs deterministic tests, Docker Compose validation, container builds, web readiness, and MCP safe-tool smoke checks for PRs and topic-branch pushes.
- CD publishes agent-service, MCP-server, and web-console images to GHCR only for `v*` tags or explicit manual dispatch.

No workflow requires broker credentials, model provider keys, or live-trading access.

## Branching Model

- `main`: locked release line. Release commits merge here from `develop`.
- `develop`: default integration branch.
- `feature/*`: new work branched from `develop`, merged back into `develop`.
- `fix/*`: defect fixes branched from `develop`, merged back into `develop`.
- `release/*`: optional stabilization branches when preparing a release merge into `main`.
