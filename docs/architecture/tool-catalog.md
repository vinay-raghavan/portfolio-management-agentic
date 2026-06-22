# Tool Catalog

This catalog documents the first MCP-style tool slice. The MCP server must expose only tools that are explicitly classified by `packages/policy`.

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
| `get_data_provider_health` | read-only | Return provider availability and not-configured statuses without network side effects. |
| `get_market_data_snapshot` | read-only | Return fixture-backed OHLCV snapshot and metrics for one symbol. |
| `get_universe_members` | read-only | Return fixture-backed universe members through the provider boundary. |
| `list_universes` | read-only | Return fixture-backed tradable universes with source metadata. |
| `run_screener` | read-only | Run a deterministic screener over a selected universe using hard gates and weighted score components. |
| `explain_candidate_evidence` | read-only | Explain technical, fundamental, sentiment, volatility, market-regime, portfolio-fit, and missing-data evidence for a candidate. |
| `search_pattern_library` | read-only | Search public-safe pattern cards and playbooks. |
| `get_pattern_playbook` | read-only | Retrieve one versioned pattern card with citation metadata. |
| `cite_strategy_evidence` | read-only | Return citation-backed evidence for a strategy explanation or draft paper proposal. |
| `explain_factor_stack` | read-only | Compose deterministic factor evidence, retrieved citations, counterevidence, and paper-only next actions. |
| `get_recommendation_explanation` | read-only | Join screener/factor evidence, strategy history, backtest history, risk gates, ledger context, and citations into a paper-only recommendation explanation. |
| `generate_paper_trading_report` | read-only | Return a paper-trading review report with accounting, positions, orders, fills, approvals, risk state, optional recommendation context, and redacted audit export rows. |
| `create_backtest_request` | draft-only | Draft an offline paper backtest request for a symbol, setup, and date window. |
| `list_backtest_requests` | read-only | Return persisted paper backtest request history. |
| `get_backtest_request` | read-only | Return one persisted paper backtest request by id. |
| `get_backtest_result` | read-only | Return a deterministic simulated backtest result for a drafted request. |
| `list_paper_orders` | read-only | Return paper order proposals and their approval/fill status. |
| `list_paper_positions` | read-only | Return fixture-backed paper positions for exposure review. |
| `create_paper_order_proposal` | draft-only | Create a paper order proposal that enters the human approval queue with no fill. |
| `approve_paper_order_simulation` | approval-required | Mark a paper order as human-approved for simulated fill processing only. |
| `simulate_approved_paper_fill` | approval-required | Create a simulated paper fill only after approval and update paper positions. |
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

These functions exist only for deterministic policy tests and must not be registered as MCP tools:

| Tool | Tier | Reason |
| --- | --- | --- |
| `place_live_order` | forbidden | Live order placement is out of scope and unsafe. |
| `get_broker_trading_token` | forbidden | Broker trading-token access is prohibited. |

## Policy Rule

Unknown tools are forbidden by default. Every new tool must be classified before exposure.

The product data, provider, pattern, recommendation, report, strategy-history, backtest, and paper-ledger tools do not write live orders, retrieve broker trading tokens, expose provider credential values, or bypass paper-trading approval gates. Simulated fills are paper-only, require prior approval, and update only the paper ledger. Report tools return JSON-ready data and do not write files.

## Reference Boundary

The pre-market briefing workflow borrows product concepts from local market-review and screener scripts: index setup, breadth, volatility, watchlist candidates, evidence, counterevidence, and risk switches. The implementation is rewritten around synthetic demo data and safe MCP tools. It does not import private source, connect to broker providers, read account positions, or retrieve live credentials.
