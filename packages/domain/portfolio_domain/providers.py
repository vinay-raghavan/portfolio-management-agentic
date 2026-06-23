from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import Protocol

from .models import (
    FundamentalsSnapshot,
    MacroSnapshot,
    MarketDataSnapshot,
    OHLCVBar,
    ProviderDescriptor,
    ProviderHealth,
    SentimentSnapshot,
    UniverseDefinition,
    UniverseMembers,
    VolatilitySnapshot,
)

OFFLINE_SOURCE = "offline_fixture"
CONFIGURED_JSON_SOURCE = "configured_json_file"
MARKET_DATA_PROVIDER_ENV = "PORTFOLIO_MARKET_DATA_PROVIDER"
MARKET_DATA_JSON_PATH_ENV = "PORTFOLIO_MARKET_DATA_JSON_PATH"
UNIVERSE_PROVIDER_ENV = "PORTFOLIO_UNIVERSE_PROVIDER"
UNIVERSE_JSON_PATH_ENV = "PORTFOLIO_UNIVERSE_JSON_PATH"
FUNDAMENTALS_PROVIDER_ENV = "PORTFOLIO_FUNDAMENTALS_PROVIDER"
FUNDAMENTALS_JSON_PATH_ENV = "PORTFOLIO_FUNDAMENTALS_JSON_PATH"
SENTIMENT_PROVIDER_ENV = "PORTFOLIO_SENTIMENT_PROVIDER"
SENTIMENT_JSON_PATH_ENV = "PORTFOLIO_SENTIMENT_JSON_PATH"
VOLATILITY_PROVIDER_ENV = "PORTFOLIO_VOLATILITY_PROVIDER"
VOLATILITY_JSON_PATH_ENV = "PORTFOLIO_VOLATILITY_JSON_PATH"
MACRO_PROVIDER_ENV = "PORTFOLIO_MACRO_PROVIDER"
MACRO_JSON_PATH_ENV = "PORTFOLIO_MACRO_JSON_PATH"
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

    def get_metrics(self, symbol: str) -> FundamentalsSnapshot: ...


class SentimentProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...

    def get_context(self, symbol: str) -> SentimentSnapshot: ...


class VolatilityProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...

    def get_context(self, symbol: str) -> VolatilitySnapshot: ...


class MacroProvider(Protocol):
    def descriptor(self) -> ProviderDescriptor: ...

    def health(self) -> ProviderHealth: ...

    def get_context(self, symbol: str) -> MacroSnapshot: ...


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

FIXTURE_FUNDAMENTALS: dict[str, dict[str, float | int | str]] = {
    "TATAMOTORS": {
        "quality_score": 0.66,
        "value_score": 0.54,
        "growth_score": 0.70,
        "earnings_revision_score": 0.52,
        "leverage_score": 0.61,
    },
    "SBIN": {
        "quality_score": 0.68,
        "value_score": 0.62,
        "growth_score": 0.58,
        "earnings_revision_score": 0.55,
        "leverage_score": 0.57,
    },
    "SUNPHARMA": {
        "quality_score": 0.72,
        "value_score": 0.59,
        "growth_score": 0.64,
        "earnings_revision_score": 0.60,
        "leverage_score": 0.74,
    },
    "LOWLIQ": {
        "quality_score": 0.42,
        "value_score": 0.45,
        "growth_score": 0.36,
        "earnings_revision_score": 0.33,
        "leverage_score": 0.40,
    },
}

FIXTURE_SENTIMENT: dict[str, dict[str, float | int | str]] = {
    "TATAMOTORS": {
        "news_score": 0.58,
        "investor_score": 0.56,
        "contradiction_score": 0.28,
    },
    "SBIN": {
        "news_score": 0.61,
        "investor_score": 0.59,
        "contradiction_score": 0.24,
    },
    "SUNPHARMA": {
        "news_score": 0.54,
        "investor_score": 0.55,
        "contradiction_score": 0.22,
    },
    "LOWLIQ": {
        "news_score": 0.38,
        "investor_score": 0.41,
        "contradiction_score": 0.52,
    },
}

FIXTURE_VOLATILITY: dict[str, dict[str, float | int | str]] = {
    "TATAMOTORS": {
        "india_vix": 15.8,
        "vix_change_pct": 2.4,
        "regime_score": 0.52,
        "risk_multiplier": 0.68,
    },
    "SBIN": {
        "india_vix": 14.1,
        "vix_change_pct": -1.6,
        "regime_score": 0.64,
        "risk_multiplier": 0.76,
    },
    "SUNPHARMA": {
        "india_vix": 13.4,
        "vix_change_pct": -2.2,
        "regime_score": 0.70,
        "risk_multiplier": 0.82,
    },
    "LOWLIQ": {
        "india_vix": 21.6,
        "vix_change_pct": 9.2,
        "regime_score": 0.32,
        "risk_multiplier": 0.48,
    },
}

FIXTURE_MACRO: dict[str, dict[str, float | int | str]] = {
    "TATAMOTORS": {
        "market_regime_score": 0.62,
        "breadth_score": 0.58,
        "rate_pressure_score": 0.54,
        "event_risk_score": 0.34,
        "liquidity_condition_score": 0.60,
    },
    "SBIN": {
        "market_regime_score": 0.60,
        "breadth_score": 0.56,
        "rate_pressure_score": 0.52,
        "event_risk_score": 0.32,
        "liquidity_condition_score": 0.58,
    },
    "SUNPHARMA": {
        "market_regime_score": 0.57,
        "breadth_score": 0.53,
        "rate_pressure_score": 0.55,
        "event_risk_score": 0.28,
        "liquidity_condition_score": 0.61,
    },
    "LOWLIQ": {
        "market_regime_score": 0.42,
        "breadth_score": 0.38,
        "rate_pressure_score": 0.44,
        "event_risk_score": 0.58,
        "liquidity_condition_score": 0.35,
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


def _fundamentals_from_payload(
    payload: Mapping[str, Any],
    provider_id: str,
) -> FundamentalsSnapshot:
    symbol = str(payload["symbol"]).upper().strip()
    if not symbol:
        raise ValueError("Configured fundamentals requires symbol.")
    metrics_payload = payload.get("metrics", {})
    if not isinstance(metrics_payload, Mapping) or not metrics_payload:
        raise ValueError("Configured fundamentals metrics must be a non-empty object.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    return FundamentalsSnapshot(
        provider_id=provider_id,
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        symbol=symbol,
        as_of=str(payload.get("as_of") or ""),
        metrics=dict(metrics_payload),
        notes=[
            "Read-only configured fundamentals snapshot.",
            *notes,
        ],
    )


def _sentiment_from_payload(
    payload: Mapping[str, Any],
    provider_id: str,
) -> SentimentSnapshot:
    symbol = str(payload["symbol"]).upper().strip()
    if not symbol:
        raise ValueError("Configured sentiment requires symbol.")
    metrics_payload = payload.get("metrics", {})
    if not isinstance(metrics_payload, Mapping) or not metrics_payload:
        raise ValueError("Configured sentiment metrics must be a non-empty object.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    return SentimentSnapshot(
        provider_id=provider_id,
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        symbol=symbol,
        as_of=str(payload.get("as_of") or ""),
        metrics=dict(metrics_payload),
        notes=[
            "Read-only configured sentiment snapshot.",
            *notes,
        ],
    )


def _volatility_from_payload(
    payload: Mapping[str, Any],
    provider_id: str,
) -> VolatilitySnapshot:
    symbol = str(payload["symbol"]).upper().strip()
    if not symbol:
        raise ValueError("Configured volatility requires symbol.")
    metrics_payload = payload.get("metrics", {})
    if not isinstance(metrics_payload, Mapping) or not metrics_payload:
        raise ValueError("Configured volatility metrics must be a non-empty object.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    return VolatilitySnapshot(
        provider_id=provider_id,
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        symbol=symbol,
        as_of=str(payload.get("as_of") or ""),
        metrics=dict(metrics_payload),
        notes=[
            "Read-only configured volatility snapshot.",
            *notes,
        ],
    )


def _macro_from_payload(
    payload: Mapping[str, Any],
    provider_id: str,
) -> MacroSnapshot:
    symbol = str(payload["symbol"]).upper().strip()
    if not symbol:
        raise ValueError("Configured macro context requires symbol.")
    metrics_payload = payload.get("metrics", {})
    if not isinstance(metrics_payload, Mapping) or not metrics_payload:
        raise ValueError("Configured macro context metrics must be a non-empty object.")
    notes_payload = payload.get("notes", [])
    notes = [str(item) for item in notes_payload if str(item).strip()]
    return MacroSnapshot(
        provider_id=provider_id,
        source=str(payload.get("source") or CONFIGURED_JSON_SOURCE),
        symbol=symbol,
        as_of=str(payload.get("as_of") or ""),
        metrics=dict(metrics_payload),
        notes=[
            "Read-only configured macro context.",
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
class JsonFileFundamentalsProvider:
    json_path: Path
    provider_id: str = "configured_fundamentals"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="fundamentals",
            display_name="Configured JSON Fundamentals",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["company_facts", "factor_inputs", "json_fundamentals_file"],
            required_env=[FUNDAMENTALS_PROVIDER_ENV, FUNDAMENTALS_JSON_PATH_ENV],
            notes=[
                "Read-only fundamentals adapter using a configured JSON file.",
                "Fixture fundamentals remain the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._fundamentals_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="fundamentals",
                status="error",
                configured=True,
                message=f"Configured JSON fundamentals is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="fundamentals",
            status="available",
            configured=True,
            message="Configured JSON fundamentals is readable.",
        )

    def get_metrics(self, symbol: str) -> FundamentalsSnapshot:
        normalized = symbol.upper().strip()
        for payload in self._fundamentals_payloads():
            fundamentals = _fundamentals_from_payload(payload, self.provider_id)
            if fundamentals.symbol == normalized:
                return fundamentals
        raise ValueError(f"Unknown configured fundamentals symbol: {symbol}")

    def _fundamentals_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        fundamentals: Any
        if isinstance(payload, list):
            fundamentals = payload
        elif isinstance(payload, Mapping) and "fundamentals" in payload:
            fundamentals = payload["fundamentals"]
            if isinstance(fundamentals, Mapping):
                fundamentals = list(fundamentals.values())
        elif isinstance(payload, Mapping) and "symbol" in payload:
            fundamentals = [payload]
        else:
            raise ValueError("configured JSON must contain fundamentals payloads")
        if not isinstance(fundamentals, list) or not fundamentals:
            raise ValueError("configured JSON contains no fundamentals")
        if not all(isinstance(item, Mapping) for item in fundamentals):
            raise ValueError("configured JSON fundamentals must be objects")
        return fundamentals


@dataclass(frozen=True)
class JsonFileSentimentProvider:
    json_path: Path
    provider_id: str = "configured_sentiment"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="sentiment",
            display_name="Configured JSON Sentiment",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["sentiment_context", "json_sentiment_file"],
            required_env=[SENTIMENT_PROVIDER_ENV, SENTIMENT_JSON_PATH_ENV],
            notes=[
                "Read-only sentiment adapter using a configured JSON file.",
                "Fixture sentiment remains the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._sentiment_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="sentiment",
                status="error",
                configured=True,
                message=f"Configured JSON sentiment is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="sentiment",
            status="available",
            configured=True,
            message="Configured JSON sentiment is readable.",
        )

    def get_context(self, symbol: str) -> SentimentSnapshot:
        normalized = symbol.upper().strip()
        for payload in self._sentiment_payloads():
            sentiment = _sentiment_from_payload(payload, self.provider_id)
            if sentiment.symbol == normalized:
                return sentiment
        raise ValueError(f"Unknown configured sentiment symbol: {symbol}")

    def _sentiment_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        sentiment: Any
        if isinstance(payload, list):
            sentiment = payload
        elif isinstance(payload, Mapping) and "sentiment" in payload:
            sentiment = payload["sentiment"]
            if isinstance(sentiment, Mapping):
                sentiment = list(sentiment.values())
        elif isinstance(payload, Mapping) and "symbol" in payload:
            sentiment = [payload]
        else:
            raise ValueError("configured JSON must contain sentiment payloads")
        if not isinstance(sentiment, list) or not sentiment:
            raise ValueError("configured JSON contains no sentiment")
        if not all(isinstance(item, Mapping) for item in sentiment):
            raise ValueError("configured JSON sentiment must be objects")
        return sentiment


@dataclass(frozen=True)
class JsonFileVolatilityProvider:
    json_path: Path
    provider_id: str = "configured_volatility"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="volatility",
            display_name="Configured JSON Volatility",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["volatility_context", "json_volatility_file"],
            required_env=[VOLATILITY_PROVIDER_ENV, VOLATILITY_JSON_PATH_ENV],
            notes=[
                "Read-only volatility adapter using a configured JSON file.",
                "Fixture volatility remains the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._volatility_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="volatility",
                status="error",
                configured=True,
                message=f"Configured JSON volatility is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="volatility",
            status="available",
            configured=True,
            message="Configured JSON volatility is readable.",
        )

    def get_context(self, symbol: str) -> VolatilitySnapshot:
        normalized = symbol.upper().strip()
        for payload in self._volatility_payloads():
            volatility = _volatility_from_payload(payload, self.provider_id)
            if volatility.symbol == normalized:
                return volatility
        raise ValueError(f"Unknown configured volatility symbol: {symbol}")

    def _volatility_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        volatility: Any
        if isinstance(payload, list):
            volatility = payload
        elif isinstance(payload, Mapping) and "volatility" in payload:
            volatility = payload["volatility"]
            if isinstance(volatility, Mapping):
                volatility = list(volatility.values())
        elif isinstance(payload, Mapping) and "symbol" in payload:
            volatility = [payload]
        else:
            raise ValueError("configured JSON must contain volatility payloads")
        if not isinstance(volatility, list) or not volatility:
            raise ValueError("configured JSON contains no volatility")
        if not all(isinstance(item, Mapping) for item in volatility):
            raise ValueError("configured JSON volatility must be objects")
        return volatility


@dataclass(frozen=True)
class JsonFileMacroProvider:
    json_path: Path
    provider_id: str = "configured_macro"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="macro",
            display_name="Configured JSON Macro",
            status="available" if self.json_path.is_file() else "error",
            configured=True,
            capabilities=["macro_context", "json_macro_file"],
            required_env=[MACRO_PROVIDER_ENV, MACRO_JSON_PATH_ENV],
            notes=[
                "Read-only macro/regime adapter using a configured JSON file.",
                "Fixture macro context remains the default when this adapter is not configured.",
            ],
        )

    def health(self) -> ProviderHealth:
        try:
            self._macro_payloads()
        except ValueError as exc:
            return ProviderHealth(
                provider_id=self.provider_id,
                kind="macro",
                status="error",
                configured=True,
                message=f"Configured JSON macro context is not usable: {exc}",
            )
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="macro",
            status="available",
            configured=True,
            message="Configured JSON macro context is readable.",
        )

    def get_context(self, symbol: str) -> MacroSnapshot:
        normalized = symbol.upper().strip()
        for payload in self._macro_payloads():
            macro = _macro_from_payload(payload, self.provider_id)
            if macro.symbol == normalized:
                return macro
        raise ValueError(f"Unknown configured macro context symbol: {symbol}")

    def _macro_payloads(self) -> list[Mapping[str, Any]]:
        if not self.json_path.is_file():
            raise ValueError("configured JSON file is missing or unreadable")
        try:
            payload = json.loads(self.json_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError("configured JSON file is not valid JSON") from exc
        macro: Any
        if isinstance(payload, list):
            macro = payload
        elif isinstance(payload, Mapping) and "macro" in payload:
            macro = payload["macro"]
            if isinstance(macro, Mapping):
                macro = list(macro.values())
        elif isinstance(payload, Mapping) and "symbol" in payload:
            macro = [payload]
        else:
            raise ValueError("configured JSON must contain macro payloads")
        if not isinstance(macro, list) or not macro:
            raise ValueError("configured JSON contains no macro context")
        if not all(isinstance(item, Mapping) for item in macro):
            raise ValueError("configured JSON macro context must be objects")
        return macro


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
class FixtureFundamentalsProvider:
    provider_id: str = "fixture_fundamentals"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="fundamentals",
            display_name="Fixture Fundamentals",
            status="available",
            configured=True,
            capabilities=["factor_proxies", "company_facts"],
            required_env=[],
            notes=["Offline-safe deterministic fundamentals proxies."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="fundamentals",
            status="available",
            configured=True,
            message="Fixture fundamentals are available without network access.",
        )

    def get_metrics(self, symbol: str) -> FundamentalsSnapshot:
        normalized = symbol.upper().strip()
        metrics = FIXTURE_FUNDAMENTALS.get(normalized)
        if not metrics:
            raise ValueError(f"Unknown fixture fundamentals symbol: {symbol}")
        return FundamentalsSnapshot(
            provider_id=self.provider_id,
            source=OFFLINE_SOURCE,
            symbol=normalized,
            as_of="2026-06-22",
            metrics=metrics,
            notes=[
                "Offline fixture fundamentals proxy.",
                "No network or broker connection was used.",
            ],
        )


@dataclass(frozen=True)
class FixtureSentimentProvider:
    provider_id: str = "fixture_sentiment"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="sentiment",
            display_name="Fixture Sentiment",
            status="available",
            configured=True,
            capabilities=["sentiment_proxy", "sentiment_context"],
            required_env=[],
            notes=["Offline-safe deterministic sentiment proxies."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="sentiment",
            status="available",
            configured=True,
            message="Fixture sentiment is available without network access.",
        )

    def get_context(self, symbol: str) -> SentimentSnapshot:
        normalized = symbol.upper().strip()
        metrics = FIXTURE_SENTIMENT.get(normalized)
        if not metrics:
            raise ValueError(f"Unknown fixture sentiment symbol: {symbol}")
        return SentimentSnapshot(
            provider_id=self.provider_id,
            source=OFFLINE_SOURCE,
            symbol=normalized,
            as_of="2026-06-22",
            metrics=metrics,
            notes=[
                "Offline fixture sentiment proxy.",
                "No network or broker connection was used.",
            ],
        )


@dataclass(frozen=True)
class FixtureVolatilityProvider:
    provider_id: str = "fixture_volatility"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="volatility",
            display_name="Fixture Volatility",
            status="available",
            configured=True,
            capabilities=["volatility_proxy", "volatility_context"],
            required_env=[],
            notes=["Offline-safe deterministic volatility proxies."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="volatility",
            status="available",
            configured=True,
            message="Fixture volatility is available without network access.",
        )

    def get_context(self, symbol: str) -> VolatilitySnapshot:
        normalized = symbol.upper().strip()
        metrics = FIXTURE_VOLATILITY.get(normalized)
        if not metrics:
            raise ValueError(f"Unknown fixture volatility symbol: {symbol}")
        return VolatilitySnapshot(
            provider_id=self.provider_id,
            source=OFFLINE_SOURCE,
            symbol=normalized,
            as_of="2026-06-22",
            metrics=metrics,
            notes=[
                "Offline fixture volatility proxy.",
                "No network or broker connection was used.",
            ],
        )


@dataclass(frozen=True)
class FixtureMacroProvider:
    provider_id: str = "fixture_macro"

    def descriptor(self) -> ProviderDescriptor:
        return ProviderDescriptor(
            provider_id=self.provider_id,
            kind="macro",
            display_name="Fixture Macro",
            status="available",
            configured=True,
            capabilities=["macro_context", "macro_regime_proxy"],
            required_env=[],
            notes=["Offline-safe deterministic macro/regime proxies."],
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            kind="macro",
            status="available",
            configured=True,
            message="Fixture macro context is available without network access.",
        )

    def get_context(self, symbol: str) -> MacroSnapshot:
        normalized = symbol.upper().strip()
        metrics = FIXTURE_MACRO.get(normalized)
        if not metrics:
            raise ValueError(f"Unknown fixture macro context symbol: {symbol}")
        return MacroSnapshot(
            provider_id=self.provider_id,
            source=OFFLINE_SOURCE,
            symbol=normalized,
            as_of="2026-06-22",
            metrics=metrics,
            notes=[
                "Offline fixture macro/regime proxy.",
                "No network or broker connection was used.",
            ],
        )


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


def _configured_fundamentals_provider(
    config: Mapping[str, str],
) -> JsonFileFundamentalsProvider | None:
    provider_name = config.get(FUNDAMENTALS_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(FUNDAMENTALS_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileFundamentalsProvider(Path(json_path))


def _configured_sentiment_provider(
    config: Mapping[str, str],
) -> JsonFileSentimentProvider | None:
    provider_name = config.get(SENTIMENT_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(SENTIMENT_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileSentimentProvider(Path(json_path))


def _configured_volatility_provider(
    config: Mapping[str, str],
) -> JsonFileVolatilityProvider | None:
    provider_name = config.get(VOLATILITY_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(VOLATILITY_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileVolatilityProvider(Path(json_path))


def _configured_macro_provider(
    config: Mapping[str, str],
) -> JsonFileMacroProvider | None:
    provider_name = config.get(MACRO_PROVIDER_ENV, "").strip().lower()
    json_path = config.get(MACRO_JSON_PATH_ENV, "").strip()
    if provider_name != JSON_FILE_PROVIDER or not json_path:
        return None
    return JsonFileMacroProvider(Path(json_path))


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
    configured_fundamentals = _configured_fundamentals_provider(config)
    configured_sentiment = _configured_sentiment_provider(config)
    configured_volatility = _configured_volatility_provider(config)
    configured_macro = _configured_macro_provider(config)
    market_data: MarketDataProvider = configured_market_data or FixtureMarketDataProvider()
    universe: UniverseProvider = configured_universe or FixtureUniverseProvider()
    fundamentals: FundamentalsProvider = (
        configured_fundamentals or FixtureFundamentalsProvider()
    )
    sentiment: SentimentProvider = configured_sentiment or FixtureSentimentProvider()
    volatility: VolatilityProvider = configured_volatility or FixtureVolatilityProvider()
    macro: MacroProvider = configured_macro or FixtureMacroProvider()
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
    if configured_fundamentals is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_fundamentals",
                kind="fundamentals",
                display_name="Configured Fundamentals",
                capabilities=["company_facts", "factor_inputs"],
                required_env=[FUNDAMENTALS_PROVIDER_ENV, FUNDAMENTALS_JSON_PATH_ENV],
                env=config,
            )
        )
    if configured_sentiment is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_sentiment",
                kind="sentiment",
                display_name="Configured Sentiment",
                capabilities=["sentiment_context"],
                required_env=[SENTIMENT_PROVIDER_ENV, SENTIMENT_JSON_PATH_ENV],
                env=config,
            )
        )
    if configured_volatility is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_volatility",
                kind="volatility",
                display_name="Configured Volatility",
                capabilities=["volatility_context"],
                required_env=[VOLATILITY_PROVIDER_ENV, VOLATILITY_JSON_PATH_ENV],
                env=config,
            )
        )
    if configured_macro is None:
        configured_placeholders.append(
            ConfiguredProviderPlaceholder(
                provider_id="configured_macro",
                kind="macro",
                display_name="Configured Macro",
                capabilities=["macro_context"],
                required_env=[MACRO_PROVIDER_ENV, MACRO_JSON_PATH_ENV],
                env=config,
            )
        )
    return DataProviderRegistry(
        market_data=market_data,
        universe=universe,
        fundamentals=fundamentals,
        sentiment=sentiment,
        volatility=volatility,
        macro=macro,
        configured_placeholders=configured_placeholders,
    )


def get_data_provider_registry() -> DataProviderRegistry:
    return build_data_provider_registry()
