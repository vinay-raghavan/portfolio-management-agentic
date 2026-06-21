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
| `get_risk_review` | read-only | Return demo risk state and safety switches. |
| `draft_paper_strategy` | draft-only | Draft a paper-trading strategy without execution. |
| `create_paper_trade_proposal` | draft-only | Create a pending paper proposal that requires human approval before any simulation. |

## Forbidden Compatibility Traps

These functions exist only for deterministic policy tests and must not be registered as MCP tools:

| Tool | Tier | Reason |
| --- | --- | --- |
| `place_live_order` | forbidden | Live order placement is out of scope and unsafe. |
| `get_broker_trading_token` | forbidden | Broker trading-token access is prohibited. |

## Policy Rule

Unknown tools are forbidden by default. Every new tool must be classified before exposure.

## Reference Boundary

The pre-market briefing workflow borrows product concepts from local market-review and screener scripts: index setup, breadth, volatility, watchlist candidates, evidence, counterevidence, and risk switches. The implementation is rewritten around synthetic demo data and safe MCP tools. It does not import private source, connect to broker providers, read account positions, or retrieve live credentials.
