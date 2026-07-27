from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database_runtime import DatabaseBackend, load_database_runtime_profile
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

    def count_market_snapshots(self, provider_id: str | None = None) -> int:
        normalized_provider_id = provider_id.strip() if provider_id else None
        return sum(
            1
            for (stored_provider, _, _) in self._snapshots
            if normalized_provider_id is None
            or stored_provider == normalized_provider_id
        )

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

    def count_market_snapshots(self, provider_id: str | None = None) -> int:
        query = "select count(*) as row_count from market_data_snapshots"
        params: list[str] = []
        if provider_id:
            query += " where provider_id = ?"
            params.append(provider_id.strip())
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["row_count"] if row is not None else 0)

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


class PostgresMarketDataStore(MarketDataStore):
    """Tenant-scoped Postgres market-data store using JSONB payload columns."""

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for Postgres market-data storage")
        self._tenant_id = tenant_id.strip()
        self._connection_factory = connection_factory
        self._now = now or (lambda: datetime.now(UTC))

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "persisted",
            "backend": "postgres",
            "configured": True,
            "tenant_scoped": True,
        }

    def record_market_snapshot(
        self,
        snapshot: MarketDataSnapshot,
    ) -> MarketDataSnapshot:
        params = {
            "tenant_id": self._tenant_id,
            "provider_id": snapshot.provider_id,
            "symbol": snapshot.symbol.upper().strip(),
            "as_of": snapshot.as_of,
            "source": snapshot.source,
            "payload": snapshot.to_dict(),
            "recorded_at": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    INSERT INTO market_data_snapshots (
                        tenant_id,
                        provider_id,
                        symbol,
                        as_of,
                        source,
                        payload,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(provider_id)s,
                        %(symbol)s,
                        %(as_of)s,
                        %(source)s,
                        %(payload)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, provider_id, symbol, as_of)
                    DO UPDATE SET
                        source = EXCLUDED.source,
                        payload = EXCLUDED.payload,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
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
            SELECT payload
            FROM market_data_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND symbol = %(symbol)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "symbol": normalized_symbol,
        }
        if provider_id is not None:
            query += " AND provider_id = %(provider_id)s"
            params["provider_id"] = provider_id
        query += " ORDER BY as_of DESC, provider_id LIMIT 1"
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(query.strip(), params)
                row = _cursor_one(cursor)
        if row is None:
            raise ValueError(f"Unknown stored market snapshot: {symbol}")
        return _market_snapshot_from_dict(_payload_from_row(row))

    def list_market_snapshots(
        self,
        symbol: str | None = None,
        limit: int = 20,
    ) -> list[MarketDataSnapshot]:
        query = """
            SELECT payload
            FROM market_data_snapshots
            WHERE tenant_id = %(tenant_id)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "limit": max(0, limit),
        }
        if symbol:
            query += " AND symbol = %(symbol)s"
            params["symbol"] = symbol.upper().strip()
        query += " ORDER BY as_of, provider_id, symbol LIMIT %(limit)s"
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(query.strip(), params)
                rows = _cursor_rows(cursor)
        return [_market_snapshot_from_dict(_payload_from_row(row)) for row in rows]

    def count_market_snapshots(self, provider_id: str | None = None) -> int:
        query = """
            SELECT count(*) AS row_count
            FROM market_data_snapshots
            WHERE tenant_id = %(tenant_id)s
        """
        params: dict[str, Any] = {"tenant_id": self._tenant_id}
        if provider_id:
            query += " AND provider_id = %(provider_id)s"
            params["provider_id"] = provider_id.strip()
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(query.strip(), params)
                row = _cursor_one(cursor)
        return int(row["row_count"] if row is not None else 0)

    def record_screener_run(self, screener_run: ScreenerRunResult) -> ScreenerRunResult:
        params = {
            "tenant_id": self._tenant_id,
            "run_id": screener_run.run_id,
            "universe_id": screener_run.universe_id,
            "preset": screener_run.preset.strip().lower(),
            "mode": screener_run.mode,
            "source": screener_run.source,
            "payload": screener_run.to_dict(),
            "recorded_at": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    INSERT INTO screener_runs (
                        tenant_id,
                        run_id,
                        universe_id,
                        preset,
                        mode,
                        source,
                        payload,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(run_id)s,
                        %(universe_id)s,
                        %(preset)s,
                        %(mode)s,
                        %(source)s,
                        %(payload)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, run_id)
                    DO UPDATE SET
                        universe_id = EXCLUDED.universe_id,
                        preset = EXCLUDED.preset,
                        mode = EXCLUDED.mode,
                        source = EXCLUDED.source,
                        payload = EXCLUDED.payload,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return screener_run

    def get_screener_run(self, run_id: str) -> ScreenerRunResult:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    SELECT payload
                    FROM screener_runs
                    WHERE tenant_id = %(tenant_id)s
                      AND run_id = %(run_id)s
                    """.strip(),
                    {
                        "tenant_id": self._tenant_id,
                        "run_id": run_id,
                    },
                )
                row = _cursor_one(cursor)
        if row is None:
            raise ValueError(f"Unknown screener run: {run_id}")
        return _screener_run_from_dict(_payload_from_row(row))

    def list_screener_runs(
        self,
        universe_id: str | None = None,
        preset: str | None = None,
        limit: int = 20,
    ) -> list[ScreenerRunResult]:
        query = """
            SELECT payload
            FROM screener_runs
            WHERE tenant_id = %(tenant_id)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "limit": max(0, limit),
        }
        if universe_id:
            query += " AND universe_id = %(universe_id)s"
            params["universe_id"] = universe_id
        if preset:
            query += " AND preset = %(preset)s"
            params["preset"] = preset.strip().lower()
        query += " ORDER BY universe_id, preset, run_id LIMIT %(limit)s"
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(query.strip(), params)
                rows = _cursor_rows(cursor)
        return [_screener_run_from_dict(_payload_from_row(row)) for row in rows]

    def _set_tenant_context(self, cursor: Any) -> None:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %(tenant_id)s, true)",
            {"tenant_id": self._tenant_id},
        )


def build_market_data_store(
    env: Mapping[str, str] | None = None,
) -> MarketDataStore | SQLiteMarketDataStore | PostgresMarketDataStore:
    config = env if env is not None else os.environ
    profile = load_database_runtime_profile(config)
    if profile.backend == DatabaseBackend.POSTGRES:
        database_url = profile.database_url
        tenant_id = config.get("PORTFOLIO_TENANT_ID", "").strip()
        if not database_url:
            raise ValueError("PORTFOLIO_DATABASE_URL is required for Postgres market-data storage")
        if not tenant_id:
            raise ValueError("PORTFOLIO_TENANT_ID is required for Postgres market-data storage")
        return PostgresMarketDataStore(
            tenant_id=tenant_id,
            connection_factory=_postgres_connection_factory(database_url),
        )
    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if db_path:
        return SQLiteMarketDataStore(db_path)
    return MarketDataStore()


def count_stored_market_snapshots(
    env: Mapping[str, str] | None = None,
    provider_id: str | None = None,
) -> int:
    config = env if env is not None else os.environ
    profile = load_database_runtime_profile(config)
    if profile.backend == DatabaseBackend.POSTGRES:
        return build_market_data_store(config).count_market_snapshots(provider_id)

    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if not db_path:
        return _MARKET_DATA_STORE.count_market_snapshots(provider_id)

    path = Path(db_path)
    if not path.is_file():
        return 0

    query = "select count(*) as row_count from market_data_snapshots"
    params: list[str] = []
    if provider_id:
        query += " where provider_id = ?"
        params.append(provider_id.strip())

    try:
        with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(query, params).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row["row_count"] if row is not None else 0)

def _postgres_connection_factory(database_url: str) -> Callable[[], Any]:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg

        return psycopg.connect(connection_url)

    return connection_factory


def _psycopg_database_url(database_url: str) -> str:
    stripped = database_url.strip()
    if stripped.startswith("postgresql+psycopg://"):
        return "postgresql://" + stripped.removeprefix("postgresql+psycopg://")
    return stripped


def _cursor_rows(cursor: Any) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    return [_row_mapping(cursor, row) for row in rows]


def _cursor_one(cursor: Any) -> dict[str, Any] | None:
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_mapping(cursor, row)


def _row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if not isinstance(row, Sequence):
        raise TypeError("Postgres market-data cursor rows must be mappings or sequences")
    description = getattr(cursor, "description", None)
    if not description:
        raise TypeError("Postgres market-data sequence rows require description")
    keys = [str(column[0]) for column in description]
    return dict(zip(keys, row, strict=False))


def _payload_from_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = row["payload"]
    if isinstance(payload, str):
        return _from_json(payload)
    if isinstance(payload, Mapping):
        return payload
    raise TypeError("Postgres market-data payload must be a mapping or JSON string")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


_MARKET_DATA_STORE = build_market_data_store()


def get_market_data_store() -> MarketDataStore | SQLiteMarketDataStore | PostgresMarketDataStore:
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
