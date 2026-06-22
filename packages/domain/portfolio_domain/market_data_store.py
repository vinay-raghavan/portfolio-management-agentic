from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .models import (
    GateResult,
    MarketDataSnapshot,
    OHLCVBar,
    RankedScreenerCandidate,
    ScoreComponent,
    ScreenerRunResult,
)

MARKET_DATA_DB_ENV = "MARKET_DATA_DB_PATH"
RECORDED_AT = "2026-06-22T00:00:00+05:30"


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: str) -> Any:
    return json.loads(value)


def _bar_from_dict(payload: Mapping[str, Any]) -> OHLCVBar:
    return OHLCVBar(
        date=str(payload["date"]),
        open=float(payload["open"]),
        high=float(payload["high"]),
        low=float(payload["low"]),
        close=float(payload["close"]),
        volume=int(payload["volume"]),
    )


def _market_snapshot_from_dict(payload: Mapping[str, Any]) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        provider_id=str(payload["provider_id"]),
        source=str(payload["source"]),
        symbol=str(payload["symbol"]),
        as_of=str(payload["as_of"]),
        bars=[_bar_from_dict(item) for item in payload["bars"]],
        latest_close=float(payload["latest_close"]),
        metrics=dict(payload["metrics"]),
        notes=[str(item) for item in payload["notes"]],
    )


def _gate_from_dict(payload: Mapping[str, Any]) -> GateResult:
    return GateResult(
        name=str(payload["name"]),
        status=str(payload["status"]),
        reason=str(payload["reason"]),
    )


def _score_component_from_dict(payload: Mapping[str, Any]) -> ScoreComponent:
    return ScoreComponent(
        name=str(payload["name"]),
        score=float(payload["score"]),
        weight=float(payload["weight"]),
        evidence=[str(item) for item in payload["evidence"]],
        counterevidence=[str(item) for item in payload["counterevidence"]],
        citations=[str(item) for item in payload["citations"]],
    )


def _candidate_from_dict(payload: Mapping[str, Any]) -> RankedScreenerCandidate:
    return RankedScreenerCandidate(
        rank=int(payload["rank"]),
        symbol=str(payload["symbol"]),
        setup=str(payload["setup"]),
        score=float(payload["score"]),
        passed_screeners=[str(item) for item in payload["passed_screeners"]],
        gates=[_gate_from_dict(item) for item in payload["gates"]],
        score_components=[
            _score_component_from_dict(item) for item in payload["score_components"]
        ],
        evidence=[str(item) for item in payload["evidence"]],
        counterevidence=[str(item) for item in payload["counterevidence"]],
        missing_data=[str(item) for item in payload["missing_data"]],
        citations=[str(item) for item in payload["citations"]],
        next_allowed_actions=[str(item) for item in payload["next_allowed_actions"]],
    )


def _screener_run_from_dict(payload: Mapping[str, Any]) -> ScreenerRunResult:
    return ScreenerRunResult(
        run_id=str(payload["run_id"]),
        mode=str(payload["mode"]),
        source=str(payload["source"]),
        universe_id=str(payload["universe_id"]),
        preset=str(payload["preset"]),
        run_summary=dict(payload["run_summary"]),
        candidates=[_candidate_from_dict(item) for item in payload["candidates"]],
        rejected_symbols=[str(item) for item in payload["rejected_symbols"]],
        multi_hit_symbols=[str(item) for item in payload["multi_hit_symbols"]],
        notes=[str(item) for item in payload["notes"]],
    )


class MarketDataStore:
    """In-memory market-data store for fixture and test runs."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str, str], MarketDataSnapshot] = {}
        self._screener_runs: dict[str, ScreenerRunResult] = {}

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "memory",
            "backend": "memory",
            "configured": False,
            "path_configured": False,
        }

    def record_market_snapshot(
        self,
        snapshot: MarketDataSnapshot,
    ) -> MarketDataSnapshot:
        key = (snapshot.provider_id, snapshot.symbol, snapshot.as_of)
        self._snapshots[key] = snapshot
        return snapshot

    def get_market_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> MarketDataSnapshot:
        normalized_symbol = symbol.upper().strip()
        matches = [
            snapshot
            for (stored_provider, stored_symbol, _), snapshot in self._snapshots.items()
            if stored_symbol == normalized_symbol
            and (provider_id is None or stored_provider == provider_id)
        ]
        if not matches:
            raise ValueError(f"Unknown stored market snapshot: {symbol}")
        return sorted(matches, key=lambda snapshot: (snapshot.as_of, snapshot.provider_id))[-1]

    def list_market_snapshots(
        self,
        symbol: str | None = None,
        limit: int = 20,
    ) -> list[MarketDataSnapshot]:
        normalized_symbol = symbol.upper().strip() if symbol else None
        snapshots = [
            snapshot
            for (_, stored_symbol, _), snapshot in self._snapshots.items()
            if normalized_symbol is None or stored_symbol == normalized_symbol
        ]
        snapshots.sort(key=lambda snapshot: (snapshot.as_of, snapshot.provider_id, snapshot.symbol))
        return snapshots[: max(0, limit)]

    def record_screener_run(self, screener_run: ScreenerRunResult) -> ScreenerRunResult:
        self._screener_runs[screener_run.run_id] = screener_run
        return screener_run

    def get_screener_run(self, run_id: str) -> ScreenerRunResult:
        try:
            return self._screener_runs[run_id]
        except KeyError as exc:
            raise ValueError(f"Unknown screener run: {run_id}") from exc

    def list_screener_runs(
        self,
        universe_id: str | None = None,
        preset: str | None = None,
        limit: int = 20,
    ) -> list[ScreenerRunResult]:
        normalized_preset = preset.strip().lower() if preset else None
        runs = [
            run
            for run in self._screener_runs.values()
            if (universe_id is None or run.universe_id == universe_id)
            and (normalized_preset is None or run.preset == normalized_preset)
        ]
        runs.sort(key=lambda run: (run.universe_id, run.preset, run.run_id))
        return runs[: max(0, limit)]


class SQLiteMarketDataStore(MarketDataStore):
    """SQLite-backed market-data store using JSON payload columns."""

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

    def record_market_snapshot(
        self,
        snapshot: MarketDataSnapshot,
    ) -> MarketDataSnapshot:
        with self._connect() as connection:
            connection.execute(
                """
                insert into market_data_snapshots (
                    provider_id,
                    symbol,
                    as_of,
                    source,
                    payload_json,
                    recorded_at
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(provider_id, symbol, as_of) do update set
                    source = excluded.source,
                    payload_json = excluded.payload_json,
                    recorded_at = excluded.recorded_at
                """,
                (
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

    def get_market_snapshot(
        self,
        symbol: str,
        provider_id: str | None = None,
    ) -> MarketDataSnapshot:
        normalized_symbol = symbol.upper().strip()
        query = """
            select payload_json from market_data_snapshots
            where symbol = ?
        """
        params: list[str] = [normalized_symbol]
        if provider_id is not None:
            query += " and provider_id = ?"
            params.append(provider_id)
        query += " order by as_of desc, provider_id limit 1"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            raise ValueError(f"Unknown stored market snapshot: {symbol}")
        return _market_snapshot_from_dict(_from_json(row["payload_json"]))

    def list_market_snapshots(
        self,
        symbol: str | None = None,
        limit: int = 20,
    ) -> list[MarketDataSnapshot]:
        query = "select payload_json from market_data_snapshots"
        params: list[str | int] = []
        if symbol:
            query += " where symbol = ?"
            params.append(symbol.upper().strip())
        query += " order by as_of, provider_id, symbol limit ?"
        params.append(max(0, limit))
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            _market_snapshot_from_dict(_from_json(row["payload_json"]))
            for row in rows
        ]

    def record_screener_run(self, screener_run: ScreenerRunResult) -> ScreenerRunResult:
        with self._connect() as connection:
            connection.execute(
                """
                insert into screener_runs (
                    run_id,
                    universe_id,
                    preset,
                    mode,
                    source,
                    payload_json,
                    recorded_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                on conflict(run_id) do update set
                    universe_id = excluded.universe_id,
                    preset = excluded.preset,
                    mode = excluded.mode,
                    source = excluded.source,
                    payload_json = excluded.payload_json,
                    recorded_at = excluded.recorded_at
                """,
                (
                    screener_run.run_id,
                    screener_run.universe_id,
                    screener_run.preset,
                    screener_run.mode,
                    screener_run.source,
                    _to_json(screener_run.to_dict()),
                    RECORDED_AT,
                ),
            )
            connection.commit()
        return screener_run

    def get_screener_run(self, run_id: str) -> ScreenerRunResult:
        with self._connect() as connection:
            row = connection.execute(
                "select payload_json from screener_runs where run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Unknown screener run: {run_id}")
        return _screener_run_from_dict(_from_json(row["payload_json"]))

    def list_screener_runs(
        self,
        universe_id: str | None = None,
        preset: str | None = None,
        limit: int = 20,
    ) -> list[ScreenerRunResult]:
        query = "select payload_json from screener_runs"
        filters: list[str] = []
        params: list[str | int] = []
        if universe_id:
            filters.append("universe_id = ?")
            params.append(universe_id)
        if preset:
            filters.append("preset = ?")
            params.append(preset.strip().lower())
        if filters:
            query += " where " + " and ".join(filters)
        query += " order by universe_id, preset, run_id limit ?"
        params.append(max(0, limit))
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            _screener_run_from_dict(_from_json(row["payload_json"]))
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists market_data_snapshots (
                    provider_id text not null,
                    symbol text not null,
                    as_of text not null,
                    source text not null,
                    payload_json text not null,
                    recorded_at text not null,
                    primary key (provider_id, symbol, as_of)
                );

                create table if not exists screener_runs (
                    run_id text primary key,
                    universe_id text not null,
                    preset text not null,
                    mode text not null check (mode = 'read_only'),
                    source text not null,
                    payload_json text not null,
                    recorded_at text not null
                );
                """
            )


def build_market_data_store(
    env: Mapping[str, str] | None = None,
) -> MarketDataStore | SQLiteMarketDataStore:
    config = env if env is not None else os.environ
    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if db_path:
        return SQLiteMarketDataStore(db_path)
    return MarketDataStore()


_MARKET_DATA_STORE = build_market_data_store()


def get_market_data_store() -> MarketDataStore | SQLiteMarketDataStore:
    return _MARKET_DATA_STORE


def get_market_data_storage_status() -> dict[str, Any]:
    return _MARKET_DATA_STORE.storage_status()


def record_market_data_snapshot(snapshot: MarketDataSnapshot) -> MarketDataSnapshot:
    return _MARKET_DATA_STORE.record_market_snapshot(snapshot)


def record_screener_run(screener_run: ScreenerRunResult) -> ScreenerRunResult:
    return _MARKET_DATA_STORE.record_screener_run(screener_run)


def list_stored_market_snapshots(
    symbol: str | None = None,
    limit: int = 20,
) -> list[MarketDataSnapshot]:
    return _MARKET_DATA_STORE.list_market_snapshots(symbol, limit)


def list_stored_screener_runs(
    universe_id: str | None = None,
    preset: str | None = None,
    limit: int = 20,
) -> list[ScreenerRunResult]:
    return _MARKET_DATA_STORE.list_screener_runs(universe_id, preset, limit)
