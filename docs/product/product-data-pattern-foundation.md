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
- Use SQLite or Postgres for users, portfolios, watchlists, strategies, paper orders, simulated fills, approvals, and audit logs.
- Use DuckDB or Parquet for local market snapshots, screener runs, and backtest datasets.
- Use a `PatternStore` interface for reference cards. Start file-backed and add ChromaDB only when semantic retrieval over a larger corpus is actually needed.
- Keep price candles, paper trades, and approvals in structured stores, not vector memory.

## Implementation Status

Current status: the fixture-backed implementation covers product-data contracts, provider adapter contracts, deterministic screener output, file-backed pattern cards, read-only MCP tools, simulated backtest contracts, paper-ledger contracts, SQLite-backed paper-ledger persistence, and deterministic tests.

The implementation sequence for this foundation was:

1. Update specs and reference docs for real-tool scope, public references, factor combination, and source-system screener lessons.
2. Add typed domain contracts for universes, OHLCV snapshots, factor evidence, screener definitions, screener runs, pattern cards, paper orders, fills, and audit events.
3. Add deterministic fixture-backed provider adapters so tests pass without cloud, broker, or model credentials.
4. Add a deterministic screener service with momentum, breakout, consolidation, and pullback presets using hard gates plus weighted scores.
5. Add a file-backed pattern library seeded with public-source pattern cards and citation metadata.
6. Add read-only MCP tools for universe listing, screener execution, candidate evidence explanation, pattern search, and factor-stack explanation.
7. Add draft-only paper-strategy proposal flow that requires risk review and human approval before simulated execution.
8. Add eval cases for factor-grounded explanations, missing data, high-volatility regime downgrades, and refusal of live trading.

## Acceptance Criteria

- Deterministic tests pass without model, broker, or market-data credentials.
- The screener can run against offline-safe fixtures and return ranked candidates with filter-level reasons.
- Candidate explanations include technical, fundamental, sentiment, volatility, portfolio-fit, and pattern evidence sections when data exists.
- Public citations are present for pattern and factor definitions.
- Missing data is visible in outputs and lowers confidence where appropriate.
- RAG tools are read-only and cannot create, authorize, or execute paper or live trades.
- Paper proposals remain draft or pending until an explicit approval workflow is implemented and tested.
- No tracked file contains local absolute paths, private source imports, broker tokens, real account data, or live-trading affordances.

## BDD Scenarios

### Multi-factor screener

Given offline-safe OHLCV, fundamentals, sentiment, and volatility fixtures exist
When the user asks for today's strongest paper-trading candidates
Then the system applies data-quality and tradability gates
And ranks candidates using explicit screener weights
And returns evidence, counterevidence, missing data, citations, and paper-only next actions.

### Regime-aware downgrade

Given a candidate has strong technical momentum
And the volatility regime is elevated
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

First test to write: a contract test for a fixture-backed screener run that verifies hard gates, component scores, multi-hit tags, citations, and no live-trading tool exposure.

Do not copy source-system code. Recreate the behavior as typed domain contracts and deterministic services with tests.
