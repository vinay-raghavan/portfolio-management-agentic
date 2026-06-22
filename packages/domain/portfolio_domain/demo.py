from __future__ import annotations

from .models import (
    Holding,
    MarketSignal,
    PortfolioSummary,
    PreMarketBriefing,
    ResearchDigest,
    RiskReview,
    ScreenerCandidate,
    SignalSummary,
    StrategyDraft,
    WatchlistItem,
    WatchlistSnapshot,
)

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
            counterevidence=[
                "Financial sector exposure is already present in demo portfolio."
            ],
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


def get_demo_watchlist_snapshot() -> WatchlistSnapshot:
    return WatchlistSnapshot(
        session="pre_market",
        source="synthetic_demo",
        items=[
            WatchlistItem(
                symbol="TATAMOTORS",
                last_price=992.4,
                change_percent=1.18,
                setup="breakout-continuation",
                notes=[
                    "Synthetic watchlist candidate also appears in momentum screen.",
                    "Needs confirmation above prior session high before any paper draft.",
                ],
            ),
            WatchlistItem(
                symbol="SBIN",
                last_price=821.7,
                change_percent=0.42,
                setup="pullback-to-support",
                notes=[
                    "Improving relative strength in demo signals.",
                    "Financials exposure should be reviewed before sizing.",
                ],
            ),
            WatchlistItem(
                symbol="SUNPHARMA",
                last_price=1518.2,
                change_percent=-0.22,
                setup="defensive-trend-resumption",
                notes=[
                    "Defensive diversification candidate in synthetic data.",
                    "Momentum evidence is weaker than top watchlist names.",
                ],
            ),
        ],
        notes=[
            "Synthetic watchlist only; no live market feed is connected.",
            "Use as pre-market review context, not as trading instruction.",
        ],
    )


def get_demo_signal_summary() -> SignalSummary:
    return SignalSummary(
        regime="constructive",
        confidence=0.68,
        index_moves={
            "NIFTY 50": 0.34,
            "NIFTY 500": 0.27,
            "BANK NIFTY": 0.12,
            "INDIA VIX": -1.8,
        },
        breadth={
            "sample": 500,
            "above_20ema_pct": 57.4,
            "above_50ema_pct": 53.2,
            "advance_decline_ratio": 1.24,
        },
        signals=[
            MarketSignal(
                label="Index trend",
                value="NIFTY 50 above short-term average",
                interpretation="Bias supports reviewing momentum candidates first.",
            ),
            MarketSignal(
                label="Volatility",
                value="INDIA VIX softening in synthetic snapshot",
                interpretation="Paper risk can stay enabled, but stops still need review.",
            ),
            MarketSignal(
                label="Breadth",
                value="More than half the demo universe above 20EMA",
                interpretation="Constructive but not broad enough to ignore concentration risk.",
            ),
        ],
        notes=[
            "Signal summary is modeled after market setup review scripts but uses synthetic data.",
            "No provider credentials, live quotes, or account positions are accessed.",
        ],
    )


def get_demo_research_digest() -> ResearchDigest:
    return ResearchDigest(
        theme="Momentum continuation with risk controls",
        source="synthetic_demo",
        notes=[
            "Breakout candidates should be checked against volume confirmation.",
            "Pullback candidates should remain above key moving-average support.",
            "Defensive candidates can reduce sector concentration if signal quality is acceptable.",
        ],
        counterevidence=[
            "Information Technology concentration is already high in the demo portfolio.",
            "High ATR candidates need reduced paper sizing.",
        ],
        citations=[
            "synthetic://pattern-library/breakout-continuation-v1",
            "synthetic://pattern-library/pullback-to-support-v1",
            "synthetic://policy/paper-trading-only-v1",
        ],
    )


def create_demo_pre_market_briefing() -> PreMarketBriefing:
    return PreMarketBriefing(
        session="pre_market",
        mode="read_only",
        source="synthetic_demo",
        portfolio=get_demo_portfolio_summary(),
        watchlist=get_demo_watchlist_snapshot(),
        signal_summary=get_demo_signal_summary(),
        research_digest=get_demo_research_digest(),
        risk_review=get_demo_risk_review(),
        suggested_review_actions=[
            "Review sector concentration before prioritizing candidates.",
            "Compare top watchlist setups against signal confidence and counterevidence.",
            "Confirm paper risk switches remain enabled and live trading remains disabled.",
            "Draft paper strategies only after the user explicitly asks for a candidate.",
        ],
        non_goals=[
            "No live trading.",
            "No broker-token access.",
            "No simulated execution without a separate human approval step.",
        ],
    )


def draft_strategy(symbol: str, rationale: str) -> StrategyDraft:
    normalized_symbol = symbol.upper().strip()
    normalized_rationale = rationale.strip()
    return StrategyDraft(
        strategy_id=f"paper-{normalized_symbol.lower()}-momentum-001",
        symbol=normalized_symbol,
        mode="paper",
        status="draft",
        source="offline_fixture",
        created_at="2026-06-22T09:15:00+05:30",
        rationale=normalized_rationale,
        entry_rule="Enter paper position only after price confirms above prior day high.",
        exit_rule="Exit paper position on 2 percent stop loss or failed breakout close.",
        risk_notes=[
            "Paper trading only.",
            "Requires human approval before simulated execution.",
            f"Rationale: {normalized_rationale}",
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
