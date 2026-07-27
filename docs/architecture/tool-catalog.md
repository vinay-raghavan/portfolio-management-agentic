# Tool Catalog

This catalog documents the first MCP-style tool slice. The MCP server must expose only tools that are explicitly classified by `packages/policy`.

Tool function docstrings are model-facing descriptions in ADK. Each exposed tool should name its policy tier, and high-risk workflow tools should also describe the safe sequence they support. This prevents future tool additions from weakening provider-readiness checks, recommendation preflights, protected human approval/fill boundaries, or live-trading refusals before evals can observe the behavior.

Route-scoped capability manifests live under `capabilities/<name>/` and are
documented in [Capability Manifests](capability-manifests.md). Those manifests
are the next harness contract for least-privilege tool bundles and matching
repository `SKILL.md` workflow instructions.

## Exposed Tools

| Tool | Tier | Purpose |
| --- | --- | --- |
| `get_portfolio_summary` | read-only | Return synthetic portfolio holdings, value, and notes. |
| `get_watchlist_snapshot` | read-only | Return synthetic pre-market watchlist candidates and review notes. |
| `get_signal_summary` | read-only | Return synthetic market setup, breadth, volatility, and signal context. |
| `get_research_digest` | read-only | Return synthetic research notes, counterevidence, and pattern citations. |
| `create_pre_market_briefing` | read-only | Compose portfolio, watchlist, signal, research, and risk sections into a briefing. |
| `run_momentum_screener` | read-only | Return synthetic screener candidates and evidence. |
| `list_data_providers` | read-only | Return provider catalog, capabilities, and configuration state without credential values. |
| `get_data_provider_health` | read-only | Return provider availability, configured JSON market-data/universe/fundamentals/sentiment/volatility/macro state, and not-configured statuses without credential values. |
| `validate_data_provider_imports` | read-only | Validate configured local JSON provider files and report missing, unsupported, malformed, or valid imports without exposing paths or credentials. |
| `list_provider_source_templates` | read-only | Return synthetic adapter-valid JSON templates, accepted wrapper names, and required fields for configured market, universe, fundamentals, sentiment, volatility, and macro source files without exposing local paths or provider data. |
| `list_provider_source_onboarding` | read-only | Return one guided card per configured source that links the template, validation state, setup gaps, refresh readiness, and safe next actions without exposing local paths or provider data. |
| `list_provider_import_previews` | read-only | Dry-run configured-provider imports and return normalized counts, sample identifiers, target stores, warnings, and would-write status without initializing stores, writing cache rows, or exposing local paths. |
| `list_provider_import_reconciliation` | read-only | Compare dry-run preview counts, latest sanitized refresh-job counts, and stored row counts so operators can identify pending refresh, in-sync, source-changed, store-mismatch, or needs-attention states without exposing paths or payloads. |
| `list_provider_profiles` | read-only | Return configured provider profile metadata, validation status, env key names, counts, and sample identifiers without resolved paths. |
| `list_provider_import_jobs` | read-only | Return sanitized provider import-refresh job history without raw payloads, credentials, or path values. |
| `get_provider_refresh_readiness` | read-only | Return configured-provider readiness, stale state, retry backoff, and next-attempt timing without exposing local paths. |
| `refresh_provider_import_profile` | draft-only | Validate one configured provider profile, persist a sanitized refresh job summary, and import configured market, universe, fundamentals, sentiment, volatility, or macro records into structured local storage when configured. |
| `run_provider_refresh_schedule` | draft-only | Run one bounded configured-provider refresh cycle, record sanitized import jobs, and return readiness for review. |
| `get_fyers_connection_health` | read-only | Return sanitized FYERS read-only connector health, fixture state, allowed read surfaces, and reconnect status without credential values. |
| `get_fyers_quote` | read-only | Return one normalized FYERS quote snapshot for an exchange-qualified symbol, failing as unavailable when the fixture/source has no quote. |
| `get_fyers_account_snapshot` | read-only | Return a normalized FYERS account snapshot with signed holdings/positions and funds while keeping provider data separate from the paper ledger. |
| `get_market_data_snapshot` | read-only | Return fixture-backed or configured JSON OHLCV snapshot and metrics for one symbol, with optional local cache persistence. |
| `list_market_data_snapshots` | read-only | Return cached market-data snapshots without exposing storage paths. |
| `get_universe_members` | read-only | Return fixture-backed or configured JSON universe members through the provider boundary. |
| `list_universes` | read-only | Return fixture-backed or configured tradable universes with source metadata. |
| `run_screener` | read-only | Run a deterministic screener over a selected fixture or configured universe using hard gates, provider refresh readiness, import-reconciliation gates, and weighted score components, with optional local run persistence. |
| `list_screener_runs` | read-only | Return cached screener runs without exposing storage paths. |
| `explain_candidate_evidence` | read-only | Explain technical, fundamental, sentiment, volatility, market-regime, portfolio-fit, and missing-data evidence for a candidate. |
| `search_pattern_library` | read-only | Search public-safe pattern cards and playbooks. |
| `search_curated_research` | read-only | Search curated allowlisted research documents through the repository research-store boundary; current MCP payloads are fixture-backed lexical hits, and the runtime `PostgresResearchStore` contract executes tenant-scoped full-text search for production wiring. |
| `get_pattern_playbook` | read-only | Retrieve one versioned pattern card with citation metadata. |
| `cite_strategy_evidence` | read-only | Return citation-backed evidence for a strategy explanation or draft paper proposal. |
| `explain_factor_stack` | read-only | Compose deterministic factor evidence, retrieved citations, counterevidence, and paper-only next actions. |
| `get_recommendation_explanation` | read-only | Join screener/factor evidence, provider refresh readiness, import-reconciliation gates, strategy history, backtest history, risk gates, ledger context, and citations into a paper-only recommendation explanation. |
| `generate_paper_trading_report` | read-only | Return a paper-trading review report with accounting, positions, orders, fills, approvals, risk state, optional recommendation context, and redacted audit export rows. |
| `create_backtest_request` | draft-only | Draft an offline paper backtest request for a symbol, setup, and date window. |
| `list_backtest_requests` | read-only | Return persisted paper backtest request history. |
| `get_backtest_request` | read-only | Return one persisted paper backtest request by id. |
| `get_backtest_result` | read-only | Return a deterministic simulated backtest result for a drafted request. |
| `list_paper_orders` | read-only | Return paper order proposals and their approval/fill status. |
| `list_paper_positions` | read-only | Return fixture-backed paper positions for exposure review. |
| `create_paper_order_proposal` | draft-only | Build a recommendation readiness preflight, block unsafe or incomplete proposals before draft creation, or create a paper order proposal that enters the human approval queue with no fill. |
| `list_paper_fills` | read-only | Return simulated paper fills without broker access. |
| `get_paper_portfolio_accounting` | read-only | Summarize paper market value, unrealized PnL, order state, and fill counts. |
| `get_approval_queue` | read-only | Return pending human approvals for paper-only actions. |
| `get_audit_events` | read-only | Return redacted paper-ledger audit events. |
| `get_risk_review` | read-only | Return demo risk state and safety switches. |
| `draft_paper_strategy` | draft-only | Draft a paper-trading strategy without execution. |
| `list_strategy_drafts` | read-only | Return persisted paper strategy draft history. |
| `get_strategy_draft` | read-only | Return one persisted paper strategy draft by id. |
| `create_paper_trade_proposal` | draft-only | Create a pending paper proposal that requires human approval before any simulation. |

## Forbidden Compatibility Traps

These functions exist only for protected server-side paths or deterministic
policy tests and must not be registered as MCP tools or exported from the
package-level `portfolio_mcp` public API:

| Tool | Tier | Reason |
| --- | --- | --- |
| `approve_paper_order_simulation` | approval-required | Human approval identity belongs to the protected API `ActorContext`, not model-visible MCP. |
| `simulate_approved_paper_fill` | approval-required | Paper-ledger mutation belongs to protected human/API or future execution-grant paths, not model-visible MCP. |
| `place_live_order` | forbidden | Live order placement is out of scope and unsafe. |
| `get_broker_trading_token` | forbidden | Broker trading-token access is prohibited. |

## Policy Rule

Unknown tools are forbidden by default. Every new tool must be classified before exposure.

The product data, provider, pattern, research, recommendation, report, strategy-history, backtest, and paper-ledger tools do not write live orders, retrieve broker trading tokens, expose provider credential values, or bypass paper-trading approval gates. Research tools search only curated repository fixtures or tenant-scoped allowlisted Postgres research documents. They do not accept arbitrary URLs, administer research sources, ingest user-supplied pages, or embed FYERS market/account data. Read-only provider tools may read locally configured JSON snapshot, universe, fundamentals, sentiment, volatility, and macro files when `PORTFOLIO_MARKET_DATA_PROVIDER=json_file` / `PORTFOLIO_MARKET_DATA_JSON_PATH`, `PORTFOLIO_UNIVERSE_PROVIDER=json_file` / `PORTFOLIO_UNIVERSE_JSON_PATH`, `PORTFOLIO_FUNDAMENTALS_PROVIDER=json_file` / `PORTFOLIO_FUNDAMENTALS_JSON_PATH`, `PORTFOLIO_SENTIMENT_PROVIDER=json_file` / `PORTFOLIO_SENTIMENT_JSON_PATH`, `PORTFOLIO_VOLATILITY_PROVIDER=json_file` / `PORTFOLIO_VOLATILITY_JSON_PATH`, and `PORTFOLIO_MACRO_PROVIDER=json_file` / `PORTFOLIO_MACRO_JSON_PATH` are set, and may persist local cache rows when `MARKET_DATA_DB_PATH` is configured. Template guidance is synthetic and schema-oriented: it returns accepted wrapper names, required fields, and minimal sample payloads only. Guided onboarding composes template guidance, validation, setup gaps, refresh readiness, and policy-classified safe actions into read-only cards. Import validation uses the same provider parsers, reports only status and sample identifiers, and does not return local paths or provider data files. Import previews reuse the same sanitizing normalization path to report target stores, counts, sample identifiers, and warnings before refresh, but do not initialize profile, market, or provider-context stores and do not write cache rows. Import reconciliation returns counts and status deltas only: preview count, latest sanitized job count, stored row count, and safe next action. Configured screener and recommendation tools consume that reconciliation state as evidence and as a paper-readiness gate; source-changed, store-mismatch, and needs-attention states downgrade confidence and remove paper-order next actions until refresh/reconciliation is reviewed. Paper order proposals must pass a deterministic readiness preflight that records recommendation stance, provider refresh readiness, import reconciliation, strategy/backtest history, risk gates, paper-only policy, and human approval requirement; blocked preflights return no draft order. Provider profile refresh jobs are draft-only writes when `PROVIDER_CONFIG_DB_PATH` is configured; they store validation status, counts, sample identifiers, env key names, source labels, sanitized execution metadata, retry/backoff state, and stale-data readiness, not resolved paths or raw provider payloads. Configured refreshes may additionally write normalized records to `market_data_snapshots`, `provider_universe_members`, and `provider_factor_snapshots`; credential-looking metric keys and raw payload notes are not retained by that import path. FYERS tools currently expose an offline, read-only connector fixture that preserves FYERS symbol normalization, source/freshness status, signed positions, and funds. They do not start OAuth, disconnect accounts, administer provider apps, retrieve credential values, call broker mutation methods, silently fall back to another data provider, or mix FYERS account snapshots into the simulated paper ledger. Cache writes are limited to market snapshots, provider context records, screener-run payloads, paper-ledger state, and provider metadata. Simulated fills are paper-only, require prior approval, and update only the paper ledger. Report tools return JSON-ready data and do not write files.

## Reference Boundary

The pre-market briefing workflow borrows product concepts from local market-review and screener scripts: index setup, breadth, volatility, watchlist candidates, evidence, counterevidence, and risk switches. The implementation is rewritten around synthetic demo data and safe MCP tools. It does not import private source, connect to broker providers, read account positions, or retrieve live credentials.
