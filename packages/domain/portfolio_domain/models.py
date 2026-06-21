from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Holding:
    symbol: str
    quantity: int
    average_price: float
    last_price: float
    sector: str

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.last_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        return round((self.last_price - self.average_price) * self.quantity, 2)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["market_value"] = self.market_value
        payload["unrealized_pnl"] = self.unrealized_pnl
        return payload


@dataclass(frozen=True)
class PortfolioSummary:
    currency: str
    total_value: float
    day_pnl: float
    holdings: list[Holding]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "total_value": self.total_value,
            "day_pnl": self.day_pnl,
            "holdings": [holding.to_dict() for holding in self.holdings],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ScreenerCandidate:
    symbol: str
    setup: str
    score: float
    evidence: list[str]
    counterevidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WatchlistItem:
    symbol: str
    last_price: float
    change_percent: float
    setup: str
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WatchlistSnapshot:
    session: str
    source: str
    items: list[WatchlistItem]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "source": self.source,
            "items": [item.to_dict() for item in self.items],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class MarketSignal:
    label: str
    value: str
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SignalSummary:
    regime: str
    confidence: float
    index_moves: dict[str, float]
    breadth: dict[str, float | int | str]
    signals: list[MarketSignal]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime,
            "confidence": self.confidence,
            "index_moves": self.index_moves,
            "breadth": self.breadth,
            "signals": [signal.to_dict() for signal in self.signals],
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ResearchDigest:
    theme: str
    source: str
    notes: list[str]
    counterevidence: list[str]
    citations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyDraft:
    strategy_id: str
    symbol: str
    mode: str
    status: str
    entry_rule: str
    exit_rule: str
    risk_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskReview:
    status: str
    concentration_notes: list[str]
    safety_switches: dict[str, str]
    recommended_pauses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreMarketBriefing:
    session: str
    mode: str
    source: str
    portfolio: PortfolioSummary
    watchlist: WatchlistSnapshot
    signal_summary: SignalSummary
    research_digest: ResearchDigest
    risk_review: RiskReview
    suggested_review_actions: list[str]
    non_goals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "mode": self.mode,
            "source": self.source,
            "portfolio": self.portfolio.to_dict(),
            "watchlist": self.watchlist.to_dict(),
            "signal_summary": self.signal_summary.to_dict(),
            "research_digest": self.research_digest.to_dict(),
            "risk_review": self.risk_review.to_dict(),
            "suggested_review_actions": self.suggested_review_actions,
            "non_goals": self.non_goals,
        }
