# Tool Catalog

This catalog documents the first MCP-style tool slice. The MCP server must expose only tools that are explicitly classified by `packages/policy`.

## Exposed Tools

| Tool | Tier | Purpose |
| --- | --- | --- |
| `get_portfolio_summary` | read-only | Return synthetic portfolio holdings, value, and notes. |
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

