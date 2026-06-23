from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .market_data_store import MARKET_DATA_DB_ENV
from .models import (
    FundamentalsSnapshot,
    MacroSnapshot,
    SentimentSnapshot,
    UniverseMembers,
    VolatilitySnapshot,
)

RECORDED_AT = "2026-06-22T00:00:00+05:30"
FACTOR_KINDS = {"fundamentals", "sentiment", "volatility", "macro"}
FactorSnapshot = (
    FundamentalsSnapshot | SentimentSnapshot | VolatilitySnapshot | MacroSnapshot
)


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: str) -> Any:
    return json.loads(value)


def _universe_members_from_dict(payload: Mapping[str, Any]) -> UniverseMembers:
    return UniverseMembers(
        provider_id=str(payload["provider_id"]),
        universe_id=str(payload["universe_id"]),
        source=str(payload["source"]),
        as_of=str(payload["as_of"]),
        symbols=[str(item) for item in payload["symbols"]],
        notes=[str(item) for item in payload["notes"]],
    )


def _factor_snapshot_from_dict(
    kind: str,
    payload: Mapping[str, Any],
) -> FactorSnapshot:
    data = {
        "provider_id": str(payload["provider_id"]),
        "source": str(payload["source"]),
        "symbol": str(payload["symbol"]),
        "as_of": str(payload["as_of"]),
        "metrics": dict(payload["metrics"]),
        "notes": [str(item) for item in payload["notes"]],
    }
    if kind == "fundamentals":
        return FundamentalsSnapshot(**data)
    if kind == "sentiment":
        return SentimentSnapshot(**data)
    if kind == "volatility":
        return VolatilitySnapshot(**data)
    if kind == "macro":
        return MacroSnapshot(**data)
    raise ValueError(f"Unknown factor snapshot kind: {kind}")


class ProviderDataStore:
    """In-memory provider context store for fixture and test runs."""

    def __init__(self) -> None:
        self._universes: dict[tuple[str, str, str], UniverseMembers] = {}
        self._factor_snapshots: dict[tuple[str, str, str, str], FactorSnapshot] = {}

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "memory",
            "backend": "memory",
            "configured": False,
            "path_configured": False,
        }

    def record_universe_members(self, members: UniverseMembers) -> UniverseMembers:
        key = (members.provider_id, members.universe_id, members.as_of)
        self._universes[key] = members
        return members

    def get_universe_members(
        self,
        universe_id: str,
        provider_id: str | None = None,
    ) -> UniverseMembers:
        normalized_universe_id = universe_id.strip()
        matches = [
            members
            for (
                stored_provider,
                stored_universe,
                _,
            ), members in self._universes.items()
            if stored_universe == normalized_universe_id
            and (provider_id is None or stored_provider == provider_id)
        ]
        if not matches:
            raise ValueError(f"Unknown stored universe members: {universe_id}")
        return sorted(
            matches, key=lambda members: (members.as_of, members.provider_id)
        )[-1]

    def record_fundamentals_snapshot(
        self,
        snapshot: FundamentalsSnapshot,
    ) -> FundamentalsSnapshot:
        self._record_factor_snapshot("fundamentals", snapshot)
        return snapshot

    def get_fundamentals_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> FundamentalsSnapshot:
        snapshot = self._get_factor_snapshot("fundamentals", symbol, provider_id)
        if not isinstance(snapshot, FundamentalsSnapshot):
            raise ValueError(f"Unknown stored fundamentals snapshot: {symbol}")
        return snapshot

    def record_sentiment_snapshot(
        self,
        snapshot: SentimentSnapshot,
    ) -> SentimentSnapshot:
        self._record_factor_snapshot("sentiment", snapshot)
        return snapshot

    def get_sentiment_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> SentimentSnapshot:
        snapshot = self._get_factor_snapshot("sentiment", symbol, provider_id)
        if not isinstance(snapshot, SentimentSnapshot):
            raise ValueError(f"Unknown stored sentiment snapshot: {symbol}")
        return snapshot

    def record_volatility_snapshot(
        self,
        snapshot: VolatilitySnapshot,
    ) -> VolatilitySnapshot:
        self._record_factor_snapshot("volatility", snapshot)
        return snapshot

    def get_volatility_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> VolatilitySnapshot:
        snapshot = self._get_factor_snapshot("volatility", symbol, provider_id)
        if not isinstance(snapshot, VolatilitySnapshot):
            raise ValueError(f"Unknown stored volatility snapshot: {symbol}")
        return snapshot

    def record_macro_snapshot(self, snapshot: MacroSnapshot) -> MacroSnapshot:
        self._record_factor_snapshot("macro", snapshot)
        return snapshot

    def get_macro_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> MacroSnapshot:
        snapshot = self._get_factor_snapshot("macro", symbol, provider_id)
        if not isinstance(snapshot, MacroSnapshot):
            raise ValueError(f"Unknown stored macro snapshot: {symbol}")
        return snapshot

    def _record_factor_snapshot(
        self,
        kind: str,
        snapshot: FactorSnapshot,
    ) -> FactorSnapshot:
        key = (kind, snapshot.provider_id, snapshot.symbol, snapshot.as_of)
        self._factor_snapshots[key] = snapshot
        return snapshot

    def _get_factor_snapshot(
        self,
        kind: str,
        symbol: str,
        provider_id: str | None = None,
    ) -> FactorSnapshot:
        normalized_symbol = symbol.upper().strip()
        matches = [
            snapshot
            for (
                stored_kind,
                stored_provider,
                stored_symbol,
                _,
            ), snapshot in self._factor_snapshots.items()
            if stored_kind == kind
            and stored_symbol == normalized_symbol
            and (provider_id is None or stored_provider == provider_id)
        ]
        if not matches:
            raise ValueError(f"Unknown stored {kind} snapshot: {symbol}")
        return sorted(
            matches, key=lambda snapshot: (snapshot.as_of, snapshot.provider_id)
        )[-1]


class SQLiteProviderDataStore(ProviderDataStore):
    """SQLite-backed provider context store using JSON payload columns."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "persisted",
            "backend": "sqlite",
            "configured": True,
            "path_configured": True,
        }

    def record_universe_members(self, members: UniverseMembers) -> UniverseMembers:
        with self._connect() as connection:
            connection.execute(
                """
                insert into provider_universe_members (
                    provider_id,
                    universe_id,
                    as_of,
                    source,
                    payload_json,
                    recorded_at
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(provider_id, universe_id, as_of) do update set
                    source = excluded.source,
                    payload_json = excluded.payload_json,
                    recorded_at = excluded.recorded_at
                """,
                (
                    members.provider_id,
                    members.universe_id,
                    members.as_of,
                    members.source,
                    _to_json(members.to_dict()),
                    RECORDED_AT,
                ),
            )
            connection.commit()
        return members

    def get_universe_members(
        self,
        universe_id: str,
        provider_id: str | None = None,
    ) -> UniverseMembers:
        query = """
            select payload_json from provider_universe_members
            where universe_id = ?
        """
        params: list[str] = [universe_id.strip()]
        if provider_id is not None:
            query += " and provider_id = ?"
            params.append(provider_id)
        query += " order by as_of desc, provider_id limit 1"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            raise ValueError(f"Unknown stored universe members: {universe_id}")
        return _universe_members_from_dict(_from_json(row["payload_json"]))

    def _record_factor_snapshot(
        self,
        kind: str,
        snapshot: FactorSnapshot,
    ) -> FactorSnapshot:
        _validate_factor_kind(kind)
        with self._connect() as connection:
            connection.execute(
                """
                insert into provider_factor_snapshots (
                    kind,
                    provider_id,
                    symbol,
                    as_of,
                    source,
                    payload_json,
                    recorded_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                on conflict(kind, provider_id, symbol, as_of) do update set
                    source = excluded.source,
                    payload_json = excluded.payload_json,
                    recorded_at = excluded.recorded_at
                """,
                (
                    kind,
                    snapshot.provider_id,
                    snapshot.symbol,
                    snapshot.as_of,
                    snapshot.source,
                    _to_json(snapshot.to_dict()),
                    RECORDED_AT,
                ),
            )
            connection.commit()
        return snapshot

    def _get_factor_snapshot(
        self,
        kind: str,
        symbol: str,
        provider_id: str | None = None,
    ) -> FactorSnapshot:
        _validate_factor_kind(kind)
        query = """
            select payload_json from provider_factor_snapshots
            where kind = ? and symbol = ?
        """
        params: list[str] = [kind, symbol.upper().strip()]
        if provider_id is not None:
            query += " and provider_id = ?"
            params.append(provider_id)
        query += " order by as_of desc, provider_id limit 1"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            raise ValueError(f"Unknown stored {kind} snapshot: {symbol}")
        return _factor_snapshot_from_dict(kind, _from_json(row["payload_json"]))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists provider_universe_members (
                    provider_id text not null,
                    universe_id text not null,
                    as_of text not null,
                    source text not null,
                    payload_json text not null,
                    recorded_at text not null,
                    primary key (provider_id, universe_id, as_of)
                );

                create table if not exists provider_factor_snapshots (
                    kind text not null check (
                        kind in ('fundamentals', 'sentiment', 'volatility', 'macro')
                    ),
                    provider_id text not null,
                    symbol text not null,
                    as_of text not null,
                    source text not null,
                    payload_json text not null,
                    recorded_at text not null,
                    primary key (kind, provider_id, symbol, as_of)
                );
                """
            )
            connection.commit()


def _validate_factor_kind(kind: str) -> None:
    if kind not in FACTOR_KINDS:
        raise ValueError(f"Unknown provider factor kind: {kind}")


def build_provider_data_store(
    env: Mapping[str, str] | None = None,
) -> ProviderDataStore | SQLiteProviderDataStore:
    config = env if env is not None else os.environ
    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if db_path:
        return SQLiteProviderDataStore(db_path)
    return ProviderDataStore()
