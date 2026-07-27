# Product Data And Pattern Foundation

## Goal

Build the next milestone as a functioning portfolio research and paper-trading foundation, not a demo-only slice. Offline-safe fixtures remain required for tests and public capstone evidence, but the product architecture must support configured market, fundamental, sentiment, volatility, and macro data adapters.

## Non-Goals

- No live order placement.
- No live strategy enablement.
- No broker trading-token access.
- No copied private source or local path dependencies.
- No retrieval layer that can authorize trading.
- No vector storage for price candles or account ledgers.

## Source-System Screener Lessons

The source-system screener flow gives useful product pointers that should be rewritten into this repository's contracts:

- Start with a named universe such as a broad index and preserve the universe source, timestamp, and fallback behavior.
- Fetch batched historical OHLCV data through a provider boundary, with caching and concurrency limits.
- Apply hard gates before ranking: data sufficiency, liquidity, volatility sanity, trend eligibility, duplicate or already-active strategy exclusion, and missing-data handling.
- Support separate screen families such as momentum, breakout, consolidation, pullback-to-support, value, growth, dividend, and quality.
- Use weighted component scores inside each screener, then expose filter-level reasons and failure reasons.
- Produce overlap ranking for candidates that pass multiple screen families.
- Infer strategy intent from filters, but keep the result as a draft strategy recommendation until risk checks, backtests, policy, and approval gates pass.
- Adapt screener strictness and candidate families to market regime, breadth, and volatility context.
- Write auditable run summaries instead of console-only output.

## Public Reference Model

The pattern library and factor model should be seeded from public, citable references:

| Area | Reference Use |
| --- | --- |
| Technical indicators | TA-Lib indicator catalog for RSI, MACD, ADX, Bollinger Bands, ATR, stochastic, candlestick recognition, and related indicator names. |
| Equity factors | Fama/French five-factor definitions for size, value, profitability, and investment; Fama/French momentum construction for prior-return momentum. |
| Multi-factor construction | S&P Quality, Value & Momentum Multi-Factor Index as a public example of selecting stocks by combined quality, value, and momentum score. |
| Factor taxonomy | MSCI factor research for value, low size, low volatility, high yield, quality, and momentum as common equity factor families. |
| Style diversification | AQR style-premia research for combining independent styles such as value, momentum, carry, and defensive instead of relying on one signal family. |
| Volatility regime | Cboe VIX methodology for expected 30-day U.S. equity volatility, and NSE India VIX methodology for NIFTY option-derived expected volatility. |
| Macro context | FRED API for economic series, release calendars, and historical observations. |
| Fundamentals | SEC EDGAR APIs for public company submissions and XBRL company facts where relevant to supported markets. |
| Sentiment | AAII Investor Sentiment Survey and SF Fed Daily News Sentiment Index as public sentiment methodology references. |

Reference URLs should live in `references/reference-map.md`, not inside prompts. Pattern cards must include source identifiers, retrieval timestamps where applicable, version, and license or usage notes when relevant.

## Factor Evidence Model

The product should avoid a single opaque "AI score." Use a typed evidence stack:

1. `DataQualityGate`: universe source, OHLCV coverage, missing bars, corporate-action handling, stale data, and provider health.
2. `TradabilityGate`: liquidity, spread proxy when available, volatility sanity, instrument eligibility, and paper-only action status.
3. `MarketRegime`: index trend, breadth, volatility level or change, sector leadership, and macro event context.
4. `TechnicalEvidence`: trend, momentum, breakout, pullback, consolidation, volume confirmation, volatility, and support or resistance.
5. `FundamentalEvidence`: value, quality, growth, profitability, leverage, earnings momentum, dividend sustainability, and data freshness.
6. `SentimentEvidence`: news sentiment, investor sentiment, social or event notes when configured, and contradiction flags.
7. `PortfolioFit`: existing exposure, concentration, correlation proxy, risk budget, drawdown, and duplicate strategy checks.
8. `PatternMatch`: matched public pattern cards, citations, prerequisites, counterevidence, and confidence.
9. `StrategyIntent`: strategy archetype, parameters, expected holding period, backtest requirement, and paper-trading eligibility.

Every candidate explanation should include positive evidence, counterevidence, missing data, score components, citations, and the next allowed action.

## Combining Factors

Use a layered approach:

- Hard gates remove invalid candidates before scoring.
- Screener-specific weights rank valid candidates within an explicit strategy family.
- Regime context changes strictness and allowed strategy families, but it should not silently rewrite policy.
- Fundamental and sentiment factors should confirm, downgrade, or defer technical candidates unless the strategy family explicitly gives them primary weight.
- VIX or India VIX context should affect risk sizing, stop width, position caps, and candidate count rather than mechanically creating buy or sell orders.
- Multi-hit candidates should be surfaced when they pass independent screen families, but the explanation must show which families agreed.
- Missing data should reduce confidence or mark a factor as unavailable; it should not be converted into neutral evidence without being disclosed.

## Data And Storage Direction

- Use typed provider contracts for `MarketDataProvider`, `UniverseProvider`, `FundamentalsProvider`, `SentimentProvider`, `VolatilityProvider`, and `MacroProvider`.
- Use Postgres for production-like users, portfolios, watchlists, strategies, paper orders, simulated fills, approvals, audit logs, market snapshots, screener runs, and provider universe/factor context. Keep SQLite as an explicit offline fallback.
- Use structured local storage for market snapshots, provider context snapshots, screener runs, provider profile metadata, provider import-refresh jobs, and backtest datasets. The current implementation uses tenant-scoped Postgres for durable market snapshots, screener runs, universes, fundamentals, sentiment, volatility, and macro context in production-like mode, SQLite for offline market/provider-context caches, and configured read-only JSON market-snapshot, universe, fundamentals, sentiment, volatility, and macro adapters for local provider exports; DuckDB or Parquet can replace or supplement this when batch analytics volume justifies it.
- Use `PatternStore` and `ResearchStore` interfaces for reference cards and
  curated research documents. Start file-backed, use Postgres full-text search
  for runtime retrieval, and add vector/hybrid retrieval only after a labeled
  benchmark proves material improvement.
- Keep research source administration outside model-visible tools. Runtime
  Postgres retrieval must join tenant-scoped enabled `research_sources` to
  available `research_documents`, use full-text ranking, and reject arbitrary
  URL queries through the MCP research search surface.
- Keep price candles, paper trades, and approvals in structured stores, not vector memory.

## Implementation Status

Current status: the fixture-backed implementation covers product-data contracts, provider adapter contracts, deterministic screener output, tenant-scoped Postgres market snapshot, screener-run, and provider-context persistence with SQLite offline fallback, configured read-only JSON market-data, universe, fundamentals, sentiment, volatility, and macro adapters, configured source schema/template guidance, guided configured-source onboarding, configured import validation with provider-settings UI feedback, configured import dry-run previews with normalized counts and target stores, configured import reconciliation with latest-job and stored-row counts, sanitized provider profiles and import-refresh job history, scheduled refresh readiness with retry/backoff and stale-data detection, provider readiness and import-reconciliation evidence in configured screener and recommendation explanations, web-console full refresh controls with per-provider backoff state, web-console configured-source setup management with required env keys, active adapter modes, setup-gap feedback, schema/template guidance, guided onboarding, dry-run preview panels, import reconciliation panels, screener/recommendation import-gate visibility, paper-order readiness preflight visibility in approval cards and reports, configured market and provider-context refresh execution into Postgres or SQLite fallback, configured multi-factor screener candidates, file-backed PatternStore/ResearchStore contracts seeded from versioned pattern cards, a curated read-only research MCP search tool, Postgres full-text research search planning/execution contracts and search-field maintenance migration, read-only MCP tools, simulated backtest contracts, paper-ledger contracts, SQLite-backed paper-ledger persistence, recommendation-readiness preflight enforcement before paper order proposals, readiness snapshots in order/audit payloads, approval-gated simulated fills, paper accounting, credential-gated eval baseline summary capture, deterministic eval failure triage, manual credentialed eval workflow support, eval submission-readiness gates, eval-aligned agent workflow routing guidance, model-facing MCP tool-description trajectory hints, deterministic workflow-tool-trajectory eval policy, repo-safe capstone evidence manifest generation, and deterministic tests.

The implementation sequence for this foundation was:

1. Update specs and reference docs for real-tool scope, public references, factor combination, and source-system screener lessons.
2. Add typed domain contracts for universes, OHLCV snapshots, factor evidence, screener definitions, screener runs, pattern cards, paper orders, fills, and audit events.
3. Add deterministic fixture-backed provider adapters so tests pass without cloud, broker, or model credentials.
4. Add a deterministic screener service with momentum, breakout, consolidation, and pullback presets using hard gates plus weighted scores.
5. Add a file-backed pattern library seeded with public-source pattern cards and citation metadata.
6. Add read-only MCP tools for universe listing, screener execution, candidate evidence explanation, pattern search, and factor-stack explanation.
7. Add draft-only paper-strategy proposal flow that requires risk review and human approval before simulated execution.
8. Add eval cases for factor-grounded explanations, missing data, high-volatility regime downgrades, and refusal of live trading.
9. Add a configured JSON market-data adapter that reads local-only snapshot payloads through the same provider boundary and cache shape as fixtures.
10. Add a configured JSON universe adapter and metric-backed configured screener path that ranks configured symbols without network or broker access.
11. Add a configured JSON fundamentals adapter and factor-backed configured screener scoring that uses quality, value, growth, earnings revision, and leverage metrics when available.
12. Add configured JSON sentiment and volatility adapters that replace missing-data disclosures with sentiment and volatility evidence when configured.
13. Add a configured JSON macro/regime adapter that contributes macro evidence to configured screener scoring and sources the market-regime explanation from provider data when configured.
14. Add provider-settings import validation and UI feedback that reports valid, missing, unsupported, or malformed configured JSON files without leaking local paths or credential-like values.
15. Add sanitized provider configuration profiles and import-refresh job history so configured local sources can be validated and tracked without committing provider data, paths, or payloads.
16. Add configured market-data refresh execution that imports normalized snapshots into the structured market-data store while keeping job records sanitized.
17. Add configured universe, fundamentals, sentiment, volatility, and macro refresh execution that imports normalized provider context records into structured stores while keeping job records sanitized.
18. Add scheduled provider refresh orchestration that runs bounded configured-provider refresh cycles and reports ready, stale, retry-due, and backoff readiness.
19. Wire provider refresh readiness into configured screener candidates, factor-stack explanations, and recommendation explanations so stale or backoff-limited data is disclosed before paper decisions.
20. Add web-console provider-settings controls for running a full provider refresh cycle and inspecting per-provider backoff and next-attempt state.
21. Add web-console configured-source setup management that shows required env keys, active adapter modes, and safe setup gaps without resolved local paths.
22. Add configured-source schema/template guidance with synthetic adapter-valid JSON payloads for each source kind, expose it through MCP and the web console, and validate the generated examples through the configured-provider adapters.
23. Add guided configured-source onboarding that links each template to live validation status, setup gaps, refresh readiness, and the safe refresh path in one operator workflow.
24. Add configured-provider import dry-run previews that parse configured sources, report normalized counts, sample identifiers, target stores, warnings, and would-write status, and avoid initializing profile, market, or provider-context stores before refresh.
25. Add configured-provider import reconciliation that compares dry-run preview counts, the latest sanitized refresh job, and structured cache rows, then reports pending-refresh, in-sync, source-changed, store-mismatch, needs-attention, or not-configured states.
26. Wire configured-provider import reconciliation into screener scoring, candidate gates, factor-stack explanations, recommendation risk gates, confidence downgrades, next allowed actions, and web-console import-gate visibility.
27. Require paper-order proposal readiness preflight from recommendation evidence, provider refresh readiness, import reconciliation, strategy/backtest history, risk gates, and paper-only approval policy; persist the preflight on orders and redacted audit payloads.
28. Surface stored readiness preflight status, provider reconciliation, provider refresh, submitted-strategy gate, blocking reasons, and paper-only approval policy in web-console approval cards, order rows, action feedback, and paper-trading reports.
29. Add credential-gated eval baseline summary capture that records preflight status, command return codes, trace and grade artifact file names, and next actions without storing credential values.
30. Add deterministic eval failure triage and a manual credentialed eval workflow so grade artifacts can be classified into policy, provider-readiness, paper-trading, grounding, tool-trajectory, or response-quality follow-ups.
31. Harden ADK agent workflow-routing instructions and the eval rubric so safe tool sequences are explicit for pre-market briefing, provider readiness, candidate explanation, recommendation-to-paper-order, approval-gated simulated fill, reports, feature navigation, and forbidden-action refusal.
32. Harden MCP tool descriptions so ADK-visible tool affordances name their policy tier and high-risk workflow sequencing constraints for provider readiness, candidate discovery, recommendation-to-paper-order, approval-gated simulated fills, and paper-trading reports.
33. Add a deterministic `workflow_tool_trajectory_policy` eval metric so generated traces are checked for required safe tool calls, forbidden tool absence, and ordering constraints across the main workflow cases.
34. Add a repo-safe capstone evidence manifest generator that summarizes deterministic proof, container runtime, workflow coverage, eval baseline status, and remaining submission gaps without local paths or secret values.
35. Add explicit eval submission-readiness gates to the baseline summary, deterministic triage report, and capstone evidence manifest so credentialed evals clearly resolve to blocked, ready-for-triage, needs-hardening, artifact-gap, or ready-for-submission states.

## Acceptance Criteria

- Deterministic tests pass without model, broker, or market-data credentials.
- The screener can run against offline-safe fixtures or configured local JSON market/universe/fundamentals/sentiment/volatility/macro inputs and return ranked candidates with filter-level reasons.
- Candidate explanations include technical, fundamental, sentiment, volatility, macro, market-regime, portfolio-fit, provider readiness, and pattern evidence sections when data exists.
- Provider settings expose read-only import validation for configured JSON sources without returning local paths, file names, or provider secrets.
- Provider settings expose profile readiness and refresh-job history without returning local paths, file names, raw provider payloads, or provider secrets.
- Provider settings expose required env keys, active adapter modes, and setup gaps for configured sources without returning resolved local paths, file names, raw provider payloads, or provider secrets.
- Provider settings expose synthetic JSON templates, accepted wrapper names, and required fields for configured sources without returning resolved local paths, file names, raw provider payloads, or provider secrets.
- Provider settings expose guided configured-source onboarding that links templates, validation, setup gaps, refresh readiness, and policy-classified safe next actions without returning resolved local paths, file names, raw provider payloads, or provider secrets.
- Provider settings expose configured-provider import dry-run previews with normalized counts, sample identifiers, target stores, warnings, and would-write status without initializing storage, writing cache rows, or returning resolved local paths, file names, raw provider payloads, or provider secrets.
- Provider settings expose configured-provider import reconciliation with preview counts, latest refresh-job counts, stored row counts, deltas, and safe next actions without returning resolved local paths, database paths, file names, raw provider payloads, or provider secrets.
- Configured screeners and recommendation explanations include provider import-reconciliation status; source-changed, store-mismatch, or needs-attention states downgrade configured-data confidence and block paper-order next actions until refresh/reconciliation is reviewed.
- Configured provider refreshes import normalized market snapshots into tenant-scoped Postgres `market_data_snapshots` in production-like mode or the SQLite fallback offline, and universe membership into `provider_universe_members` plus fundamentals/sentiment/volatility/macro snapshots into `provider_factor_snapshots` on the same production-like/offline storage boundary, while recording sanitized progress, import counts, retry attempts, retry/backoff state, stale-data readiness, and audit metadata.
- Public citations are present for pattern and factor definitions.
- Missing data is visible in outputs and lowers confidence where appropriate.
- RAG tools are read-only and cannot create, authorize, or execute paper or live trades.
- Curated research search rejects arbitrary URLs, stays tenant/source scoped for
  runtime Postgres retrieval, defaults to fixture-backed lexical hits, and can
  be switched to `PORTFOLIO_RESEARCH_STORE_BACKEND=postgres` only when a tenant
  id and database URL are configured. Misconfigured Postgres mode fails
  explicitly instead of falling back to fixtures; vector/hybrid retrieval still
  requires a labeled benchmark.
- Paper order proposals require a ready recommendation preflight before entering approval; blocked preflights return no draft order and disclose missing evidence without live-trading or credential affordances.
- Paper approval and report surfaces show the stored readiness preflight evidence operators need before human approval.
- Model-backed eval runs write redacted baseline summaries and deterministic triage reports, leave generated traces/results under ignored artifacts, and can be launched through a manual credentialed workflow.
- Agent instructions and eval rubrics include explicit safe workflow routes for the main paper-trading and provider-readiness journeys.
- Model-facing MCP tool descriptions include policy-tier language and sequencing hints for high-risk agent trajectories.
- Eval grading includes deterministic forbidden-action and workflow-tool-trajectory code metrics in addition to the response-quality judge.
- Capstone evidence can be generated as an ignored repo-safe manifest that lists deterministic proof, workflow coverage, eval status, and remaining gaps without local paths or secret values.
- Eval baseline, triage, and capstone evidence expose a submission-readiness status so the final package cannot silently treat skipped, failed, missing-artifact, or failing evals as complete.
- No tracked file contains local absolute paths, private source imports, broker tokens, real account data, or live-trading affordances.

## Remaining Implementation Plan

Next, run the credential-gated model eval baseline, review the baseline summary, triage report, traces, and grade artifacts, and use failures to tune remaining agent instructions, tool descriptions, and trajectory checks for paper-trading, provider-readiness, grounding, tool-trajectory, and forbidden-action workflows.

## BDD Scenarios

### Multi-factor screener

Given offline-safe OHLCV, fundamentals, sentiment, volatility, and macro fixtures exist
When the user asks for today's strongest paper-trading candidates
Then the system applies data-quality and tradability gates
And ranks candidates using explicit screener weights
And returns evidence, counterevidence, missing data, citations, and paper-only next actions.

### Regime-aware downgrade

Given a candidate has strong technical momentum
And the volatility or macro regime is elevated
When the agent explains the setup
Then the explanation keeps the technical evidence
But downgrades risk sizing or confidence
And does not create an order.

### Pattern retrieval boundary

Given a pattern card says a breakout setup can be actionable
When the user asks the agent to trade it live
Then the agent refuses live trading
And the MCP policy blocks forbidden tools
And the retrieved pattern remains advisory context only.

## Implementation Handoff

Read `.agents-cli-spec.md`, this document, `references/reference-map.md`, `docs/decisions/0005-rag-pattern-memory-boundary.md`, and `docs/architecture/tool-catalog.md`.

Next test to write: an eval-derived regression for the first model-backed trajectory that fails the credentialed baseline triage report.

Do not copy source-system code. Recreate the behavior as typed domain contracts and deterministic services with tests.
