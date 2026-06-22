from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .models import (
    MarketDataSnapshot,
    OHLCVBar,
    ProviderDescriptor,
    ProviderHealth,
    UniverseDefinition,
    UniverseMembers,
)

OFFLINE_SOURCE = "offline_fixture"


class MarketDataProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...

    def get_snapshot(self, symbol: str) -> MarketDataSnapshot: ...


class UniverseProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...

    def list_universes(self) -> list[UniverseDefinition]: ...

    def get_members(self, universe_id: str) -> UniverseMembers: ...


class FundamentalsProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...


class SentimentProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...


class VolatilityProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...


class MacroProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...


FIXTURE_UNIVERSES = [
    UniverseDefinition(
        universe_id="fixture_nifty50",
        name="Offline Fixture NIFTY 50 Slice",
        source=OFFLINE_SOURCE,
        as_of="2026-06-22",
        symbols=["TATAMOTORS", "SBIN", "SUNPHARMA", "LOWLIQ"],
        notes=[
            "Deterministic fixture for tests and capstone evidence.",
            "No live market feed, broker account, or provider credential is required.",
        ],
    )
]

FIXTURE_BARS: dict[str, list[OHLCVBar]] = {
    "TATAMOTORS": [
        OHLCVBar("2026-06-18", 962.4, 979.8, 956.1, 973.5, 4_920_000),
        OHLCVBar("2026-06-19", 974.0, 986.2, 969.0, 982.1, 5_240_000),
        OHLCVBar("2026-06-22", 984.6, 1002.4, 981.2, 997.8, 7_180_000),
    ],
    "SBIN": [
        OHLCVBar("2026-06-18", 812.1, 820.0, 805.4, 817.6, 8_840_000),
        OHLCVBar("2026-06-19", 817.9, 824.2, 812.8, 821.7, 7_920_000),
        OHLCVBar("2026-06-22", 822.0, 829.5, 816.1, 824.3, 8_110_000),
    ],
    "SUNPHARMA": [
        OHLCVBar("2026-06-18", 1506.0, 1522.2, 1494.4, 1518.2, 1_210_000),
        OHLCVBar("2026-06-19", 1517.0, 1531.8, 1511.3, 1525.4, 1_340_000),
        OHLCVBar("2026-06-22", 1526.1, 1539.0, 1519.8, 1534.6, 1_420_000),
    ],
    "LOWLIQ": [
        OHLCVBar("2026-06-18", 101.0, 104.0, 99.8, 102.2, 2_000),
        OHLCVBar("2026-06-19", 102.1, 103.2, 99.9, 100.4, 1_600),
        OHLCVBar("2026-06-22", 100.5, 102.4, 98.5, 99.1, 1_800),
    ],
}

FIXTURE_METRICS: dict[str, dict[str, float | int | str]] = {
    "TATAMOTORS": {
        "atr_pct": 3.4,
        "median_turnover_cr": 71.6,
        "roc20_pct": 8.6,
        "rsi14": 61.8,
    },
    "SBIN": {
        "atr_pct": 2.1,
        "median_turnover_cr": 66.9,
        "roc20_pct": 4.2,
        "rsi14": 55.4,
    },
    "SUNPHARMA": {
        "atr_pct": 1.8,
        "median_turnover_cr": 21.8,
        "roc20_pct": 2.7,
        "rsi14": 52.1,
    },
    "LOWLIQ": {
        "atr_pct": 6.8,
        "median_turnover_cr": 0.02,
        "roc20_pct": -3.3,
        "rsi14": 41.2,
    },
}


@dataclass(frozen=True)
class FixtureMarketDataProvider:
    provider_id: str = "fixture_market_data"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="market_data",
            display_name="Fixture Market Data",
            status="available",
            configured=True,
            capabilities=["daily_ohlcv", "snapshot_metrics"],
            required_env=[],
            notes=["Offline-safe deterministic OHLCV fixtures."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="market_data",
            status="available",
            configured=True,
            message="Fixture market data is available without network access.",
        )

    def get_snapshot(self, symbol: str) -> MarketDataSnapshot:
        normalized = symbol.upper().strip()
        bars = FIXTURE_BARS.get(normalized)
        if not bars:
            raise ValueError(f"Unknown fixture symbol: {symbol}")
        return MarketDataSnapshot(
            provider_id=self.provider_id,
            source=OFFLINE_SOURCE,
            symbol=normalized,
            as_of=bars[-1].date,
            bars=bars,
            latest_close=bars[-1].close,
            metrics=FIXTURE_METRICS[normalized],
            notes=[
                "Offline fixture market snapshot.",
                "No network or broker connection was used.",
            ],
        )


@dataclass(frozen=True)
class FixtureUniverseProvider:
    provider_id: str = "fixture_universe"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="universe",
            display_name="Fixture Universe",
            status="available",
            configured=True,
            capabilities=["list_universes", "universe_members"],
            required_env=[],
            notes=["Offline-safe deterministic universe membership."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="universe",
            status="available",
            configured=True,
            message="Fixture universe data is available without network access.",
        )

    def list_universes(self) -> list[UniverseDefinition]:
        return FIXTURE_UNIVERSES

    def get_members(self, universe_id: str) -> UniverseMembers:
        for universe in FIXTURE_UNIVERSES:
            if universe.universe_id == universe_id:
                return UniverseMembers(
                    provider_id=self.provider_id,
                    universe_id=universe.universe_id,
                    source=universe.source,
                    as_of=universe.as_of,
                    symbols=universe.symbols,
                    notes=universe.notes,
                )
        raise ValueError(f"Unknown universe_id: {universe_id}")


@dataclass(frozen=True)
class FixtureReferenceProvider:
    provider_id: str
    kind: str
    display_name: str
    capabilities: list[str]

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind=self.kind,
            display_name=self.display_name,
            status="available",
            configured=True,
            capabilities=self.capabilities,
            required_env=[],
            notes=["Offline-safe deterministic fixture provider."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind=self.kind,
            status="available",
            configured=True,
            message=f"{self.display_name} is available from fixtures.",
        )


@dataclass(frozen=True)
class ConfiguredProviderPlaceholder:
    provider_id: str
    kind: str
    display_name: str
    capabilities: list[str]
    required_env: list[str]
    env: Mapping[str, str]

    @property
    def configured(self) -> bool:
        return all(self.env.get(name) for name in self.required_env)

    @property
    def status(self) -> str:
        if self.configured:
            return "configured_pending_adapter"
        return "not_configured"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind=self.kind,
            display_name=self.display_name,
            status=self.status,
            configured=self.configured,
            capabilities=self.capabilities,
            required_env=self.required_env,
            notes=[
                "Configured provider placeholder; network adapter is not enabled in this slice.",
                "Health reports configuration state without exposing credential values.",
            ],
        )

    def health(self) -> ProviderHealth:
        if self.configured:
            message = "Configuration was detected; provider adapter implementation is pending."
        else:
            message = "Missing optional configuration; fixture provider remains active."
        return ProviderHealth(
            provider_id=self.provider_id,
            kind=self.kind,
            status=self.status,
            configured=self.configured,
            message=message,
        )


@dataclass(frozen=True)
class DataProviderRegistry:
    market_data: MarketDataProvider
    universe: UniverseProvider
    fundamentals: FundamentalsProvider
    sentiment: SentimentProvider
    volatility: VolatilityProvider
    macro: MacroProvider
    configured_placeholders: list[ConfiguredProviderPlaceholder]

    def descriptors(self) -> list[ProviderDescriptor]:
        active = [
            self.market_data.descriptor(),
            self.universe.descriptor(),
            self.fundamentals.descriptor(),
            self.sentiment.descriptor(),
            self.volatility.descriptor(),
            self.macro.descriptor(),
        ]
        return active + [provider.descriptor() for provider in self.configured_placeholders]

    def health(self) -> list[ProviderHealth]:
        active = [
            self.market_data.health(),
            self.universe.health(),
            self.fundamentals.health(),
            self.sentiment.health(),
            self.volatility.health(),
            self.macro.health(),
        ]
        return active + [provider.health() for provider in self.configured_placeholders]

    def providers_used(self) -> dict[str, str]:
        return {
            "market_data": self.market_data.descriptor().provider_id,
            "universe": self.universe.descriptor().provider_id,
            "fundamentals": self.fundamentals.descriptor().provider_id,
            "sentiment": self.sentiment.descriptor().provider_id,
            "volatility": self.volatility.descriptor().provider_id,
            "macro": self.macro.descriptor().provider_id,
        }


def build_data_provider_registry(
    env: Mapping[str, str] | None = None,
) -> DataProviderRegistry:
    config = env if env is not None else os.environ
    return DataProviderRegistry(
        market_data=FixtureMarketDataProvider(),
        universe=FixtureUniverseProvider(),
        fundamentals=FixtureReferenceProvider(
            provider_id="fixture_fundamentals",
            kind="fundamentals",
            display_name="Fixture Fundamentals",
            capabilities=["factor_proxies"],
        ),
        sentiment=FixtureReferenceProvider(
            provider_id="fixture_sentiment",
            kind="sentiment",
            display_name="Fixture Sentiment",
            capabilities=["sentiment_proxy"],
        ),
        volatility=FixtureReferenceProvider(
            provider_id="fixture_volatility",
            kind="volatility",
            display_name="Fixture Volatility",
            capabilities=["volatility_proxy"],
        ),
        macro=FixtureReferenceProvider(
            provider_id="fixture_macro",
            kind="macro",
            display_name="Fixture Macro",
            capabilities=["macro_context"],
        ),
        configured_placeholders=[
            ConfiguredProviderPlaceholder(
                provider_id="configured_market_data",
                kind="market_data",
                display_name="Configured Market Data",
                capabilities=["daily_ohlcv", "snapshot_metrics"],
                required_env=["PORTFOLIO_MARKET_DATA_PROVIDER"],
                env=config,
            ),
            ConfiguredProviderPlaceholder(
                provider_id="configured_universe",
                kind="universe",
                display_name="Configured Universe",
                capabilities=["list_universes", "universe_members"],
                required_env=["PORTFOLIO_UNIVERSE_PROVIDER"],
                env=config,
            ),
            ConfiguredProviderPlaceholder(
                provider_id="configured_fundamentals",
                kind="fundamentals",
                display_name="Configured Fundamentals",
                capabilities=["company_facts", "factor_inputs"],
                required_env=["PORTFOLIO_FUNDAMENTALS_PROVIDER"],
                env=config,
            ),
            ConfiguredProviderPlaceholder(
                provider_id="configured_sentiment",
                kind="sentiment",
                display_name="Configured Sentiment",
                capabilities=["sentiment_context"],
                required_env=["PORTFOLIO_SENTIMENT_PROVIDER"],
                env=config,
            ),
            ConfiguredProviderPlaceholder(
                provider_id="configured_volatility",
                kind="volatility",
                display_name="Configured Volatility",
                capabilities=["volatility_context"],
                required_env=["PORTFOLIO_VOLATILITY_PROVIDER"],
                env=config,
            ),
            ConfiguredProviderPlaceholder(
                provider_id="configured_macro",
                kind="macro",
                display_name="Configured Macro",
                capabilities=["macro_context"],
                required_env=["PORTFOLIO_MACRO_PROVIDER"],
                env=config,
            ),
        ],
    )


def get_data_provider_registry() -> DataProviderRegistry:
    return build_data_provider_registry()
