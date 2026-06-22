from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
for relative_path in (
    "packages/policy",
    "packages/domain",
    "apps/mcp-server",
):
    package_path = str(REPO_ROOT / relative_path)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)

from portfolio_mcp.tools import (  # noqa: E402
    create_pre_market_briefing,
    generate_paper_trading_report,
    get_approval_queue,
    get_audit_events,
    get_data_provider_health,
    get_paper_portfolio_accounting,
    get_recommendation_explanation,
    get_risk_review,
    list_paper_fills,
    list_paper_orders,
    list_paper_positions,
    run_screener,
)


def build_console_overview() -> dict[str, Any]:
    """Build the first web-console payload from policy-controlled tools."""
    return {
        "mode": "paper_only",
        "safety": {
            "live_trading": "blocked",
            "broker_trading_tokens": "forbidden",
            "simulated_fills": "approval_required",
        },
        "workflow_actions": [
            {
                "label": "Run pre-market briefing",
                "tool": "create_pre_market_briefing",
                "tier": "read_only",
            },
            {
                "label": "Review approval queue",
                "tool": "get_approval_queue",
                "tier": "read_only",
            },
            {
                "label": "Generate paper report",
                "tool": "generate_paper_trading_report",
                "tier": "read_only",
            },
        ],
        "briefing": create_pre_market_briefing(),
        "providers": get_data_provider_health(),
        "screener": run_screener(
            universe_id="fixture_nifty50",
            preset="momentum",
            limit=5,
        ),
        "recommendation": get_recommendation_explanation(
            "TATAMOTORS",
            "breakout-continuation",
        ),
        "paper_ledger": {
            "orders": list_paper_orders(),
            "positions": list_paper_positions(),
            "fills": list_paper_fills(),
            "accounting": get_paper_portfolio_accounting(),
            "approvals": get_approval_queue(),
        },
        "risk": get_risk_review(),
        "report": generate_paper_trading_report(
            "TATAMOTORS",
            "breakout-continuation",
        ),
        "audit": get_audit_events(),
    }
