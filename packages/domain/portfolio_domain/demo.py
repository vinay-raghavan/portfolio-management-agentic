from __future__ import annotations

from .models import Holding, PortfolioSummary, RiskReview, ScreenerCandidate, StrategyDraft

DEMO_HOLDINGS = [
    Holding("INFY", 12, 1410.0, 1502.5, "Information Technology"),
    Holding("HDFCBANK", 9, 1540.0, 1628.2, "Financials"),
    Holding("TCS", 5, 3675.0, 3798.0, "Information Technology"),
    Holding("NIFTYBEES", 40, 236.0, 249.4, "Index ETF"),
]


def get_demo_portfolio_summary() -> PortfolioSummary:
    total_value = round(sum(holding.market_value for holding in DEMO_HOLDINGS), 2)
    return PortfolioSummary(
        currency="INR",
        total_value=total_value,
        day_pnl=842.35,
        holdings=DEMO_HOLDINGS,
        notes=[
            "Synthetic demo portfolio for capstone use.",
            "No real account, broker, or order data is included.",
        ],
    )


def run_demo_momentum_screener(limit: int) -> list[ScreenerCandidate]:
    candidates = [
        ScreenerCandidate(
            symbol="TATAMOTORS",
            setup="breakout-continuation",
            score=0.86,
            evidence=[
                "Price above 20-day and 50-day moving averages.",
                "Volume expansion in the last session.",
            ],
            counterevidence=["ATR is elevated, so position sizing should be reduced."],
        ),
        ScreenerCandidate(
            symbol="SBIN",
            setup="pullback-to-support",
            score=0.79,
            evidence=[
                "Higher-low structure remains intact.",
                "Relative strength is improving versus the index.",
            ],
            counterevidence=["Financial sector exposure is already present in demo portfolio."],
        ),
        ScreenerCandidate(
            symbol="SUNPHARMA",
            setup="trend-resumption",
            score=0.74,
            evidence=[
                "Price reclaimed short-term moving average.",
                "Defensive sector may diversify the demo portfolio.",
            ],
            counterevidence=["Momentum confirmation is weaker than top candidate."],
        ),
    ]
    return candidates[: max(0, limit)]


def draft_strategy(symbol: str, rationale: str) -> StrategyDraft:
    normalized_symbol = symbol.upper().strip()
    return StrategyDraft(
        strategy_id=f"paper-{normalized_symbol.lower()}-momentum-001",
        symbol=normalized_symbol,
        mode="paper",
        status="draft",
        entry_rule="Enter paper position only after price confirms above prior day high.",
        exit_rule="Exit paper position on 2 percent stop loss or failed breakout close.",
        risk_notes=[
            "Paper trading only.",
            "Requires human approval before simulated execution.",
            f"Rationale: {rationale}",
        ],
    )


def get_demo_risk_review() -> RiskReview:
    return RiskReview(
        status="review",
        concentration_notes=[
            "Information Technology is the largest synthetic exposure.",
            "No live broker positions are connected.",
        ],
        safety_switches={
            "live_trading": "disabled",
            "paper_trading": "enabled",
            "broker_token_access": "forbidden",
        },
        recommended_pauses=[
            "Pause any strategy that requests live order placement.",
            "Review position sizing for high-ATR candidates.",
        ],
    )

