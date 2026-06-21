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

