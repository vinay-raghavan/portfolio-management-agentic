# Verification

## Deterministic Safety Checks

Run from the repo root:

```bash
uv run pytest tests
```

Current coverage:

- Unknown tools are forbidden by default.
- Live trading and broker-token access are blocked.
- Sensitive keys are redacted from blocked-tool details.
- Exposed MCP tools contain no forbidden tool names.
- MCP streamable HTTP runtime exposes only the safe tool catalog.
- Docker or Podman Compose config validates when either runtime is available.
- Demo portfolio, screener, strategy draft, and paper proposal contracts work.
- Pre-market briefing contracts compose portfolio, watchlist, signal, research, and risk sections from synthetic data.
- Product data and pattern contracts list fixture/configured universes, run hard-gated deterministic screeners, seed file-backed PatternStore/ResearchStore contracts from versioned pattern cards, reject arbitrary URL research queries in fixture, Postgres, MCP, and protected HTTP modes, execute tenant-scoped PostgresResearchStore full-text retrieval through an injectable connection, retrieve pattern cards, cite strategy evidence, and explain factor stacks without vector retrieval. Protected HTTP research contracts list only registered allowlisted sources, search curated fixture/Postgres stores, queue refresh intents only by registered source id plus normalized query or symbol, and enforce `RESEARCH_REFRESH_KILL_SWITCH` / `PORTFOLIO_RESEARCH_REFRESH_KILL_SWITCH` before source lookup or query normalization.
- Provider readiness evidence contracts disclose stale, backoff, pending, or retry-due provider state in configured screener and recommendation explanations without creating paper orders or leaking local provider paths.
- Provider import-reconciliation gate contracts disclose source-changed, store-mismatch, pending-refresh, and needs-attention states in configured screeners and recommendations, downgrade confidence, and remove paper-order next actions without leaking local provider paths.
- Market-data and provider-context persistence contracts store and reload fixture/configured-provider market snapshots, screener runs, universes, fundamentals, sentiment, volatility, and macro context through tenant-scoped Postgres in production-like mode, retain explicit SQLite offline coverage, and avoid exposing database paths or credentials.
- Provider profile metadata contracts store configured-provider profile and import-refresh job summaries without exposing resolved local paths, file names, credentials, or raw provider payloads.
- Protected FYERS integration API contracts verify typed `FyersConnection` and
  `ProviderRefreshJob` public contracts, `ActorContext`-required OAuth
  start/status/callback/disconnect and refresh routes, OAuth state plus PKCE
  challenge generation without returning a verifier, short-lived one-time
  verifier cache behavior, callback fail-closed on unknown state or missing
  verifier, explicit token-exchange-disabled status until the credential vault
  is wired, operator `FYERS_CONNECTOR_KILL_SWITCH` rejection before connector
  access or refresh-result persistence, read-only normalized fixture refreshes
  with signed positions, and absence of provider tokens, credential material,
  broker mutation methods, model-visible OAuth tools, or paper-ledger payload
  mixing.
- FYERS Postgres storage contracts verify the Alembic-managed
  `fyers_oauth_sessions` table, tenant row-level security, sanitized
  `fyers_connections` upserts, single-use actor/connection-scoped OAuth state,
  and absence of access tokens, refresh tokens, client secrets, trading tokens,
  or PKCE verifiers from persisted params and returned contracts.
- FYERS refresh persistence contracts verify tenant-scoped
  `provider_refresh_jobs`, `provider_snapshot_envelopes`, and
  `broker_account_snapshots` writes for read-only refreshes, including signed
  positions, funds, provenance, explicit provider errors, and no Yahoo fallback
  or paper-ledger mixing.
- Postgres/Alembic foundation contracts verify production-like storage selects
  Postgres explicitly through `PORTFOLIO_STORAGE_BACKEND`, redacts database and
  Redis credentials in runtime status payloads, requires migrations, preserves
  SQLite as an offline compatibility backend, and rejects SQLite when
  production-like readiness is required. Alembic revision-chain contracts also
  verify a single migration head, no orphaned `down_revision` references, and
  reversible upgrade/downgrade functions for every migration file.
- Model usage telemetry contracts verify metric-only `ModelUsageEvent`
  persistence, tenant-scoped Postgres `model_usage_events` migration with row
  level security, idempotent request recording, FastAPI routing to Postgres
  when production-like storage is configured, in-memory fallback for
  local/offline mode, and rejection/non-retention of raw prompts, raw responses,
  provider credentials, broker tokens, or secret-looking payloads.
- Session-memory contracts verify compact summary-only persistence, tenant and
  actor-scoped Postgres upserts/reads/deletes, 2-hour idle and 24-hour absolute TTLs,
  immediate deletion, object-reference-only carryover, and rejection of raw
  account payloads, provider secrets, private notes, and long-term preferences.
- Provider refresh orchestration contracts record bounded scheduled refresh cycles, retry/backoff state, and stale-data readiness without exposing local provider paths; `PROVIDER_REFRESH_SCHEDULER_KILL_SWITCH` / `PORTFOLIO_PROVIDER_REFRESH_SCHEDULER_KILL_SWITCH` blocks scheduled cycles before validation, metadata-job persistence, storage-status checks, or imports run.
- Configured-source template contracts expose adapter-valid synthetic JSON shapes for market, universe, fundamentals, sentiment, volatility, and macro sources, and verify each template validates through the same configured-provider adapters without leaking source paths or credential-like values.
- Guided configured-source onboarding contracts link templates, validation, setup gaps, refresh readiness, and safe next actions without exposing source paths or credential-like values.
- Configured-provider import preview contracts dry-run normalized target-store counts, sample identifiers, warnings, and would-write status without initializing provider profile or market-data stores, writing cache rows, or leaking source paths or credential-like values.
- Configured-provider import reconciliation contracts compare preview counts, latest refresh-job counts, and structured store row counts, including pending-refresh, in-sync, source-changed, store-mismatch, and needs-attention states, without leaking source paths, database paths, raw payloads, or credential-like values.
- Recommendation explanation contracts join factor evidence, strategy history, backtest metrics, risk gates, ledger context, citations, and paper-only next actions without creating orders.
- Paper-trading report contracts return read-only review summaries with readiness preflight sections, JSON-ready redacted audit exports, and no file writes.
- Paper-execution grant contracts verify policy ceilings are disabled until fully
  configured, grants are human-bound and no broader than both request and
  policy, self-approval is rejected by default, revoked or expired grants,
  duplicate idempotency keys, stale quotes, kill-switch activation, and
  quantity/notional violations reject without mutation, and accepted fills are
  paper-only with no FYERS/live/credential fields.
- Postgres paper-execution store contracts verify Alembic adds explicit
  `permitted_symbols`, protected policy/batch/grant/ledger writes are
  tenant-scoped and committed, read paths return tenant-scoped domain
  contracts without committing, active grant revocation updates and returns the
  revoked grant atomically, grant approval identity is not requester-spoofed,
  idempotent ledger rows use `ON CONFLICT ... DO NOTHING`, and FYERS or
  credential-looking payloads fail closed before storage or read return.
- Protected paper-execution API contracts verify `/v1/paper/*` requires
  authenticated `ActorContext` with explicit tenant metadata, admin policy
  creation, analyst batch proposal, approver-bound grant issuance and
  revocation, body-spoofed `approved_by` rejection, fresh
  execution-under-grant acceptance, revoked-grant rejection, Postgres-store
  routing when `PORTFOLIO_STORAGE_BACKEND=postgres`, durable work-item
  enqueue/claim/complete routing for Postgres execution, database URL redaction
  from responses, duplicate idempotency rejection from the Postgres ledger
  rather than process-local memory, conflict-race rejection when a unique ledger
  insert is skipped, accepted-insert grant consumed-capacity updates without
  consuming capacity on duplicate conflicts, server-side
  `PAPER_EXECUTION_KILL_SWITCH` enforcement in direct API and queued Postgres
  worker execution even when request payloads set `kill_switch_active=false`,
  locked-grant capacity guards that
  reject reserved-capacity races without ledger mutation, and paper-only
  response payloads without FYERS or credential fields.
- Paper-execution worker contracts verify `DeterministicPaperExecutionWorker`
  owns the evaluate-and-record boundary, records only accepted decisions, keeps
  rejected decisions mutation-free, and returns the recorder-authoritative
  decision for conflict handling.
- Paper-execution queue-processor contracts verify the standalone
  `PaperExecutionQueueProcessor` returns `no_work` without mutation, claims
  queued work items, reconstructs authoritative paper execution context from
  tenant-scoped storage, records accepted decisions before completing work
  items, and fails closed without ledger mutation when policy state or work-item
  payloads are missing or malformed.
- Paper-execution worker-runner contracts verify the standalone Postgres-only
  worker loop processes queued items until idle, stops at a configured item
  budget, counts fail-closed items without recording ledger mutations, refuses
  non-Postgres startup, parses configured tenant IDs, polls tenant-scoped
  processors in round-robin order, persists distributed scheduling cursor and
  failure backoff in Redis without credential leakage, emits redacted
  worker-health/backoff snapshots without queue mutation, and is deployed by
  Compose without exposing a public port or MCP/model-visible authority.
- Capstone evidence manifest contracts build a repo-safe submission evidence summary without local paths, broker/provider secrets, real account data, or raw provider payloads.
- Model-backed eval checks build the official `agents-cli eval generate` and `agents-cli eval grade` commands, skip without credentials, write a redacted baseline summary, produce deterministic failure triage, expose a manual credentialed baseline workflow, and never print secret values.
- Eval dataset contracts verify the selected metrics include the LLM response-quality rubric plus deterministic forbidden-action and workflow-tool-trajectory code metrics, and execute representative trajectory-policy examples directly from `eval_config.yaml`.
- Agent definition contracts verify the ADK instruction contains eval-aligned workflow routes and refusal guidance, that local/unit imports use an in-process adapter by default, that production-like `AGENT_TOOL_TRANSPORT=mcp` builds a private streamable-HTTP `McpToolset` filtered to `EXPOSED_TOOL_NAMES`, that public MCP URLs are rejected, and that runtime callbacks short-circuit forbidden/human-API routes, filter paper-proposal tools to the capability manifest, and block out-of-route stale tool calls before model-backed evals run.
- MCP tool-description and runtime contracts verify every exposed model-facing tool names its policy tier, high-risk provider-readiness, recommendation-to-paper-order, and report tools include trajectory hints before model-backed evals run, and human-approval, legacy fill-mutation, and forbidden compatibility traps are absent from both MCP transport registration and the package-level `portfolio_mcp` public API.
- Web console contracts verify the Vite/React app, safe product surfaces, Compose wiring, `/console/overview`, focused `/console/workflows` pages, paper-order readiness preflight visibility, provider source setup visibility, guided onboarding, required env-key display, active adapter modes, setup-gap feedback, schema/template guidance, provider import validation feedback, provider profile/import-job settings, import-gate visibility on decision pages, full provider refresh controls, per-provider backoff state, `ActorContext`-derived approval identity, body-spoof rejection for `approved_by`, and the paper-only action lifecycle.
- OIDC identity contracts validate generic provider settings, issuer, audience,
  signed JWTs, expiry, immutable subject, tenant claim, roles, nonce, and
  constant-time authorization state comparison. When `OIDC_AUTH_ENABLED=true`,
  protected API dependencies require a signed Bearer token; trusted actor
  headers remain only the local/offline fallback.
- Actor identity storage contracts upsert verified `issuer + subject` pairs in
  `actor_identities`, store only hashed/optional profile fields, and ensure
  Postgres-backed session memory receives the stable actor UUID required by its
  foreign key rather than a raw OIDC subject.
- Paper execution API contracts ensure Postgres-backed policy, batch, grant,
  and execution work-item actor FK fields also use resolved `actor_identities`
  UUIDs while local/offline process-memory mode keeps readable subject strings.
- Credential-vault readiness contracts fail closed by default, require explicit
  `macos_keychain` local or `kms` hosted configuration before token exchange is
  allowed, expose only redacted admin status, keep FYERS OAuth callbacks in
  `token_exchange_not_configured` state when token exchange is disabled, and
  exchange browser auth codes into the configured vault only when an explicit
  FYERS token-exchange flag and ready vault are present. They round-trip only
  opaque FYERS credential references through Postgres while redacting the ref
  value from HTTP payloads. Vault write-plan
  and writer contracts keep token payloads out of serializable summaries, fail
  closed on disabled or mismatched backends, reject live-broker trading-token
  material, send macOS Keychain secrets through stdin rather than command-line
  arguments, and keep hosted KMS plaintext/ciphertext handles out of results.
- Provider adapter contracts expose fixture defaults, provider health, import validation, fixture market snapshots, configured read-only JSON market snapshots, configured read-only JSON universes, configured read-only JSON fundamentals, configured read-only JSON sentiment, configured read-only JSON volatility, configured read-only JSON macro context, and universe membership without credentials or network requirements. FYERS connector contracts additionally verify the isolated `fyers-apiv3==3.1.14` SDK adapter normalizes only read allowlisted data surfaces, preserves signed quantities and provenance, hashes provider order/trade identifiers, rejects provider/API failures as unavailable, disables Yahoo fallback, and exposes no broker mutation method.
- Strategy, backtest, and paper-ledger contracts persist paper strategy drafts, backtest request history, paper orders, positions, fills, approvals, and audit events through tenant-scoped Postgres in production-like mode, retain explicit SQLite offline coverage, return offline results, require readiness preflight before paper order proposals, block incomplete proposal evidence before draft creation, require approval before simulated fills, update paper positions/accounting, and emit redacted audit events.
- Gemini, Claude, OpenAI-compatible, and Ollama provider profiles are declared; Ollama runtime profiles include route budgets for every model-visible capability manifest, 80% context-window caps, model digest pinning and verification, private inventory probing without prompts, capability readiness, redacted usage-event schema, deterministic usage-budget decisions, aggregate token/latency/tool summaries, a prompt/routing/retrieval-first tuning gate, and provider-neutral candidate promotion checks for safety, core success, response quality, trajectory, judge errors, token use, and latency.
- ADK, Codex, Claude Code, Gemini CLI, and generic MCP client profiles use the MCP policy boundary.
- Harness evaluator contracts define `ContextPack`, `ContextEvaluator`, and
  `ResponseEvaluator` checks for tenant isolation, freshness, relevance,
  duplication, prompt injection, client-secret/provider-token leakage, positive
  token sizes, budget, schema validity, citation existence, tool-output
  agreement, policy statements, uncertainty, and one structured repair attempt.
- Session-memory API contracts require `ActorContext`, persist compact
  tenant/actor-scoped summaries through Postgres when configured, keep only
  process-local fallback state in local mode, enforce 2-hour idle and 24-hour
  absolute TTLs, support immediate deletion, and reject raw account data,
  prompts, tokens, secrets, private notes, and long-term preferences.
- Harness route-decision contracts deterministically route forbidden live
  trading, FYERS refresh, human approval, pre-market briefing, and draft-only
  paper proposal intents before model classification; ambiguous read-only
  requests either resolve to exactly one read-only manifest bundle or fail
  closed to clarification with no model-visible tools.

## ADK Scaffold Checks

Run from `apps/agent-service`:

```bash
agents-cli install
uv run pytest tests/unit tests/integration
```

Credential-free checks verify:

- Agent imports without Google ADC.
- The ADK agent exposes safe portfolio, briefing, provider, screener, pattern, factor-evidence, recommendation, report, strategy-history, backtest-history, paper-ledger, and risk tools only.
- The FastAPI app starts without Google ADC.
- Invalid request handling works.
- Feedback endpoint works with local logging fallback.

Gemini streaming tests are skipped unless `GOOGLE_API_KEY` or `GOOGLE_CLOUD_PROJECT` is configured.

## Agent Evals

From the repository root, run a credential-safe preflight first:

```bash
uv run python scripts/run_agent_evals.py preflight --json
```

Run from `apps/agent-service` after model credentials are configured:

```bash
agents-cli eval generate
agents-cli eval grade
```

The repository wrapper runs the same generate-and-grade sequence with explicit
artifact directories:

```bash
uv run python scripts/run_agent_evals.py run --fail-on-skip
```

The wrapper writes `apps/agent-service/artifacts/evals/baseline-summary.json`
unless `--summary-output` is provided. The summary uses schema
`portfolio-agent-eval-baseline/v1` and records preflight status, command return
codes, trace file names, grade-result file names, the exact `candidate_commit`,
and an `agents-cli eval compare` template without credential values. Missing or
unknown commit binding keeps the artifact out of release-ready status.

Credential-free triage can be run before or after a credentialed baseline:

```bash
uv run python scripts/run_agent_evals.py triage --json
```

It writes `apps/agent-service/artifacts/evals/triage-report.json` with schema
`portfolio-agent-eval-triage/v1`, classifies failed cases by category and
severity, records trace tool calls by case, and suggests the next regression
type without another model call. Passing triage is capstone-ready only when the
triage report and baseline summary are bound to the same exact
`candidate_commit`.

The default dataset includes positive workflow cases and negative safety cases.
The `forbidden_action_policy` code metric fails traces that call forbidden tools
or fail to clearly refuse live-trading and credential-disclosure requests. The
`workflow_tool_trajectory_policy` code metric checks required tool calls,
safe alternatives, and ordering constraints for the main pre-market,
provider-readiness, candidate-explanation, paper-order, approval-gated-fill,
history, recommendation, report, and forbidden-action cases.

## Capstone Evidence

Generate the repo-safe evidence manifest from the repository root:

```bash
uv run python scripts/build_capstone_evidence.py
```

The manifest writes to `artifacts/capstone/evidence-manifest.json` by default
and summarizes deterministic verification commands, container services,
implemented workflows, eval baseline status, and remaining submission gaps. The
output is ignored by Git and must contain only relative artifact paths and
credential key names. The capstone builder reports `commit_unbound` or
`commit_mismatch` when eval evidence is missing exact candidate-commit binding.
CD requires a successful GitHub eval artifact named
`portfolio-agentic-eval-artifacts-${GITHUB_SHA}` for that exact commit before
container images can build or publish.

## Container Checks

Use either Docker Compose or Podman Compose from the repo root:

```bash
docker compose config --quiet
docker compose up --build
```

```bash
podman compose config --quiet
podman compose up --build
```

Default endpoints:

- Agent service: `http://localhost:8000`
- MCP server: `http://localhost:8081/mcp`
- Web console: `http://localhost:3000`

Compose config also validates the shared `paper-ledger-data` volume and
`PAPER_LEDGER_DB_PATH=/data/paper-ledger.db`,
`MARKET_DATA_DB_PATH=/data/market-data.db`, and
`PROVIDER_CONFIG_DB_PATH=/data/provider-config.db` defaults for durable local
compatibility state. Strategy drafts, backtest requests, paper orders,
positions, fills, approvals, paper-ledger audit events, market snapshots,
screener runs, provider context, provider configuration profiles, and provider
import-refresh jobs use tenant-scoped Postgres when production-like storage is
selected. Compose also passes
`PORTFOLIO_MARKET_DATA_PROVIDER`,
`PORTFOLIO_MARKET_DATA_JSON_PATH`, `PORTFOLIO_UNIVERSE_PROVIDER`,
`PORTFOLIO_UNIVERSE_JSON_PATH`, `PORTFOLIO_FUNDAMENTALS_PROVIDER`,
`PORTFOLIO_FUNDAMENTALS_JSON_PATH`, `PORTFOLIO_SENTIMENT_PROVIDER`,
`PORTFOLIO_SENTIMENT_JSON_PATH`, `PORTFOLIO_VOLATILITY_PROVIDER`, and
`PORTFOLIO_VOLATILITY_JSON_PATH`, `PORTFOLIO_MACRO_PROVIDER`, and
`PORTFOLIO_MACRO_JSON_PATH` to the agent and MCP services so local JSON
snapshot, universe, fundamentals, sentiment, volatility, and macro adapters
can be enabled without committing provider data. Import validation, dry-run
import previews, and import reconciliation check those configured JSON files
without returning local file paths. Preview output includes normalized counts,
target stores, sample identifiers, warnings, and would-write status before
refresh writes run. Reconciliation output compares preview counts, latest
refresh-job counts, and stored row counts before configured screeners or
recommendations rely on cached provider data. Source-changed, store-mismatch,
or needs-attention states downgrade configured evidence and block paper-order
next actions until refresh/reconciliation is reviewed. Provider profile refresh jobs persist sanitized
validation and execution summaries, source env key names, import counts,
retry/backoff state, and stale-data readiness. Configured refreshes can import
normalized market snapshots, provider universes, and factor context into
tenant-scoped Postgres `market_data_snapshots`, `provider_universe_members`,
and `provider_factor_snapshots` in production-like mode, or into the SQLite
fallback when `MARKET_DATA_DB_PATH` is configured.

The local LLM profile uses native private Ollama by default. The first pilot
model is `llama3.1:8b`; the runtime contract remains model-independent:

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
curl "http://localhost:8000/v1/storage/status?require_production_like=true"
```

The model tuning status API is provider-neutral. It reports candidate model
names, development and sealed holdout set identifiers, prompt/routing/retrieval
tuning mode, disabled fine-tuning guardrails, and promotion thresholds without
returning provider secrets, raw prompts, raw responses, or eval examples.
`MODEL_ROUTE_KILL_SWITCH` / `PORTFOLIO_MODEL_ROUTE_KILL_SWITCH` keeps status
endpoints observable while marking the route blocked and makes protected
candidate and suite evaluation fail closed with HTTP 503 before promotion
logic runs.
The candidate-evaluation API applies those thresholds to metric-only baseline
and candidate evidence. It rejects candidates outside `MODEL_TUNING_CANDIDATES`
and rejects raw prompt, raw response, transcript, message, token, or secret
fields before evaluating promotion readiness.
The candidate-suite API applies the same provider-neutral checks to a bounded
set of local or hosted candidates, fails closed unless sealed holdout evidence
is explicitly marked as passed, enforces minimum and required candidate
coverage, and ranks only promotable models by safety, core success, response
score, trajectory, token use, and latency. This keeps `llama3.1:8b`,
`gemma4:12b`, and later 7B/8B pilots interchangeable behind the same metric
contract.
Model usage telemetry accepts only metric fields: route, provider/model ids,
prompt/output token counts, tool-call count, queue wait, latency, retry count,
and request id. Extra fields are rejected so raw prompts, raw responses, and
credential material do not enter the telemetry store. Production-like Postgres
mode persists those events in tenant-scoped `model_usage_events`; local/offline
mode keeps only a rolling process-memory buffer. Summaries expose aggregate
token, latency, queue, retry, route, and budget-violation data.

For the optional Compose-managed Ollama profile, run
`podman compose --profile ollama run --rm ollama-model-prepull` with
`OLLAMA_PREPULL_MODEL=llama3.1:8b` to hydrate the private `ollama-data` volume.
The Ollama service is intentionally unexposed; no `11434:11434` host port is
published.

## GitHub Actions

CI runs on pull requests into `develop` or `main`, pushes to `develop`, `main`,
`feature/**`, and `fix/**`, and manual dispatch. It runs:

- Root contract, security, integration, and hygiene tests.
- Credential-gated model eval preflight.
- Agent-service unit and integration tests.
- Web console install, moderate dependency audit, typecheck, and build.
- Docker Compose config validation.
- Agent, MCP, and web image builds.
- Agent readiness check at `/docs`.
- Web console readiness check at `http://127.0.0.1:3000`.
- MCP streamable HTTP safe-tool catalog check.

CD runs on `v*` tags or manual dispatch. It builds the agent-service and
MCP-server and web-console images and publishes them to GHCR only when
tag-triggered or when manual dispatch explicitly enables image publishing. It
does not deploy to an environment or require model, broker, or data-provider
credentials.
