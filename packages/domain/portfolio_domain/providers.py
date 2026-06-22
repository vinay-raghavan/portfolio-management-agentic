from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
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
CONFIGURED_JSON_SOURCE = "configured_json_file"
MARKET_DATA_PROVIDER_ENV = "PORTFOLIO_MARKET_DATA_PROVIDER"
MARKET_DATA_JSON_PATH_ENV = "PORTFOLIO_MARKET_DATA_JSON_PATH"
UNIVERSE_PROVIDER_ENV = "PORTFOLIO_UNIVERSE_PROVIDER"
UNIVERSE_JSON_PATH_ENV = "PORTFOLIO_UNIVERSE_JSON_PATH"
JSON_FILE_PROVIDER = "json_file"


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


def _bar_from_payload(payload: Mapping[str, Any]) -> OHLCVBar:
    return OHLCVBar(
        date=str(payload["date"]),
        open=float(payload["open"]),
        high=float(payload["high"]),
        low=float(payload["low"]),
        close=float(payload["close"]),
        volume=int(payload["volume"]),
    )


def _snapshot_from_payload(
    payload: Mapping[str, Any],
    provider_id: str,
) -> MarketDataSnapshot:
    symbol = str(payload["symbol"]).upper().strip()
    bars = [_bar_from_payload(item) for item in payload.get("bars", [])]
    if not symbol or not bars:
        raise ValueError("Configured market snapshot requires symbol and bars.")
    latest_close = float(payload.get("latest_close", bars[-1].close))
    metrics_payload = payload.get("metrics", {})
    if not isinstance(metrics_payload, Mapping):
        raise ValueError("Configured market snapshot metrics must be an object.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    return MarketDataSnapshot(
        provider_id=provider_id,
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        symbol=symbol,
        as_of=str(payload.get("as_of") or bars[-1].date),
        bars=bars,
        latest_close=latest_close,
        metrics=dict(metrics_payload),
        notes=[
            "Read-only configured market data snapshot.",
            *notes,
        ],
    )


def _universe_from_payload(payload: Mapping[str, Any]) -> UniverseDefinition:
    symbols_payload = payload.get("symbols", [])
    if not isinstance(symbols_payload, list) or not symbols_payload:
        raise ValueError("Configured universe requires a non-empty symbols list.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    universe_id = str(payload["universe_id"]).strip()
    if not universe_id:
        raise ValueError("Configured universe requires universe_id.")
    return UniverseDefinition(
        universe_id=universe_id,
        name=str(payload.get("name") or universe_id),
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        as_of=str(payload.get("as_of") or ""),
        symbols=[str(symbol).upper().strip() for symbol in symbols_payload],
        notes=[
            "Read-only configured universe.",
            *notes,
        ],
    )


@dataclass(frozen=True)
class JsonFileMarketDataProvider:
    json_path: Path
    provider_id: str = "configured_market_data"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="market_data",
            display_name="Configured JSON Market Data",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["daily_ohlcv", "snapshot_metrics", "json_snapshot_file"],
            required_env=[MARKET_DATA_PROVIDER_ENV, MARKET_DATA_JSON_PATH_ENV],
            notes=[
                "Read-only market data adapter using a configured JSON snapshot file.",
                "Fixture provider remains the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._snapshot_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="market_data",
                status="error",
                configured=True,
                message=f"Configured JSON market data is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="market_data",
            status="available",
            configured=True,
            message="Configured JSON market data is readable.",
        )

    def get_snapshot(self, symbol: str) -> MarketDataSnapshot:
        normalized = symbol.upper().strip()
        for payload in self._snapshot_payloads():
            snapshot = _snapshot_from_payload(payload, self.provider_id)
            if snapshot.symbol == normalized:
                return snapshot
        raise ValueError(f"Unknown configured market data symbol: {symbol}")

    def _snapshot_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        snapshots: Any
        if isinstance(payload, list):
            snapshots = payload
        elif isinstance(payload, Mapping) and "snapshots" in payload:
            snapshots = payload["snapshots"]
            if isinstance(snapshots, Mapping):
                snapshots = list(snapshots.values())
        elif isinstance(payload, Mapping) and "symbol" in payload:
            snapshots = [payload]
        else:
            raise ValueError("configured JSON must contain snapshot payloads")
        if not isinstance(snapshots, list) or not snapshots:
            raise ValueError("configured JSON contains no snapshots")
        if not all(isinstance(item, Mapping) for item in snapshots):
            raise ValueError("configured JSON snapshots must be objects")
        return snapshots


@dataclass(frozen=True)
class JsonFileUniverseProvider:
    json_path: Path
    provider_id: str = "configured_universe"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="universe",
            display_name="Configured JSON Universe",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["list_universes", "universe_members", "json_universe_file"],
            required_env=[UNIVERSE_PROVIDER_ENV, UNIVERSE_JSON_PATH_ENV],
            notes=[
                "Read-only universe adapter using a configured JSON file.",
                "Fixture universe remains the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._universe_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="universe",
                status="error",
                configured=True,
                message=f"Configured JSON universe is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="universe",
            status="available",
            configured=True,
            message="Configured JSON universe is readable.",
        )

    def list_universes(self) -> list[UniverseDefinition]:
        return [
            _universe_from_payload(payload)
            for payload in self._universe_payloads()
        ]

    def get_members(self, universe_id: str) -> UniverseMembers:
        normalized = universe_id.strip()
        for universe in self.list_universes():
            if universe.universe_id == normalized:
                return UniverseMembers(
                    provider_id=self.provider_id,
                    universe_id=universe.universe_id,
                    source=universe.source,
                    as_of=universe.as_of,
                    symbols=universe.symbols,
                    notes=universe.notes,
                )
        raise ValueError(f"Unknown configured universe_id: {universe_id}")

    def _universe_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        universes: Any
        if isinstance(payload, list):
            universes = payload
        elif isinstance(payload, Mapping) and "universes" in payload:
            universes = payload["universes"]
            if isinstance(universes, Mapping):
                universes = list(universes.values())
        elif isinstance(payload, Mapping) and "universe_id" in payload:
            universes = [payload]
        else:
            raise ValueError("configured JSON must contain universe payloads")
        if not isinstance(universes, list) or not universes:
            raise ValueError("configured JSON contains no universes")
        if not all(isinstance(item, Mapping) for item in universes):
            raise ValueError("configured JSON universes must be objects")
        return universes


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


def _configured_market_data_provider(
    config: Mapping[str, str],
) -> JsonFileMarketDataProvider | None:
    provider_name = config.get(MARKET_DATA_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(MARKET_DATA_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileMarketDataProvider(Path(json_path))


def _configured_universe_provider(
    config: Mapping[str, str],
) -> JsonFileUniverseProvider | None:
    provider_name = config.get(UNIVERSE_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(UNIVERSE_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileUniverseProvider(Path(json_path))


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
    configured_market_data = _configured_market_data_provider(config)
    configured_universe = _configured_universe_provider(config)
    market_data: MarketDataProvider = configured_market_data or FixtureMarketDataProvider()
    universe: UniverseProvider = configured_universe or FixtureUniverseProvider()
    configured_placeholders: list[ConfiguredProviderPlaceholder] = []
    if configured_market_data is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_market_data",
                kind="market_data",
                display_name="Configured Market Data",
                capabilities=["daily_ohlcv", "snapshot_metrics"],
                required_env=[MARKET_DATA_PROVIDER_ENV, MARKET_DATA_JSON_PATH_ENV],
                env=config,
            )
        )
    if configured_universe is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_universe",
                kind="universe",
                display_name="Configured Universe",
                capabilities=["list_universes", "universe_members"],
                required_env=[UNIVERSE_PROVIDER_ENV, UNIVERSE_JSON_PATH_ENV],
                env=config,
            )
        )
    configured_placeholders.extend(
        [
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
        ]
    )
    return DataProviderRegistry(
        market_data=market_data,
        universe=universe,
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
        configured_placeholders=configured_placeholders,
    )


def get_data_provider_registry() -> DataProviderRegistry:
    return build_data_provider_registry()
