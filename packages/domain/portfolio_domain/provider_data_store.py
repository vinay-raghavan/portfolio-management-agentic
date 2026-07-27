from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .database_runtime import DatabaseBackend, load_database_runtime_profile
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

    def count_universe_members(self, provider_id: str | None = None) -> int:
        normalized_provider_id = provider_id.strip() if provider_id else None
        return sum(
            1
            for (stored_provider, _, _) in self._universes
            if normalized_provider_id is None
            or stored_provider == normalized_provider_id
        )

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

    def count_factor_snapshots(
        self,
        kind: str,
        provider_id: str | None = None,
    ) -> int:
        _validate_factor_kind(kind)
        normalized_provider_id = provider_id.strip() if provider_id else None
        return sum(
            1
            for (stored_kind, stored_provider, _, _) in self._factor_snapshots
            if stored_kind == kind
            and (
                normalized_provider_id is None
                or stored_provider == normalized_provider_id
            )
        )


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

    def count_universe_members(self, provider_id: str | None = None) -> int:
        query = "select count(*) as row_count from provider_universe_members"
        params: list[str] = []
        if provider_id:
            query += " where provider_id = ?"
            params.append(provider_id.strip())
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["row_count"] if row is not None else 0)

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

    def count_factor_snapshots(
        self,
        kind: str,
        provider_id: str | None = None,
    ) -> int:
        _validate_factor_kind(kind)
        query = """
            select count(*) as row_count from provider_factor_snapshots
            where kind = ?
        """
        params: list[str] = [kind]
        if provider_id:
            query += " and provider_id = ?"
            params.append(provider_id.strip())
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["row_count"] if row is not None else 0)

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


class PostgresProviderDataStore(ProviderDataStore):
    """Tenant-scoped Postgres provider context store using JSONB payload columns."""

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for Postgres provider context storage")
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

    def record_universe_members(self, members: UniverseMembers) -> UniverseMembers:
        params = {
            "tenant_id": self._tenant_id,
            "provider_id": members.provider_id,
            "universe_id": members.universe_id.strip(),
            "as_of": members.as_of,
            "source": members.source,
            "payload": members.to_dict(),
            "recorded_at": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    INSERT INTO provider_universe_members (
                        tenant_id,
                        provider_id,
                        universe_id,
                        as_of,
                        source,
                        payload,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(provider_id)s,
                        %(universe_id)s,
                        %(as_of)s,
                        %(source)s,
                        %(payload)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, provider_id, universe_id, as_of)
                    DO UPDATE SET
                        source = EXCLUDED.source,
                        payload = EXCLUDED.payload,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return members

    def get_universe_members(
        self,
        universe_id: str,
        provider_id: str | None = None,
    ) -> UniverseMembers:
        query = """
            SELECT payload
            FROM provider_universe_members
            WHERE tenant_id = %(tenant_id)s
              AND universe_id = %(universe_id)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "universe_id": universe_id.strip(),
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
            raise ValueError(f"Unknown stored universe members: {universe_id}")
        return _universe_members_from_dict(_payload_from_row(row))

    def count_universe_members(self, provider_id: str | None = None) -> int:
        query = """
            SELECT count(*) AS row_count
            FROM provider_universe_members
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

    def _record_factor_snapshot(
        self,
        kind: str,
        snapshot: FactorSnapshot,
    ) -> FactorSnapshot:
        _validate_factor_kind(kind)
        params = {
            "tenant_id": self._tenant_id,
            "kind": kind,
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
                    INSERT INTO provider_factor_snapshots (
                        tenant_id,
                        kind,
                        provider_id,
                        symbol,
                        as_of,
                        source,
                        payload,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(kind)s,
                        %(provider_id)s,
                        %(symbol)s,
                        %(as_of)s,
                        %(source)s,
                        %(payload)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, kind, provider_id, symbol, as_of)
                    DO UPDATE SET
                        source = EXCLUDED.source,
                        payload = EXCLUDED.payload,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
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
            SELECT payload
            FROM provider_factor_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND kind = %(kind)s
              AND symbol = %(symbol)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "kind": kind,
            "symbol": symbol.upper().strip(),
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
            raise ValueError(f"Unknown stored {kind} snapshot: {symbol}")
        return _factor_snapshot_from_dict(kind, _payload_from_row(row))

    def count_factor_snapshots(
        self,
        kind: str,
        provider_id: str | None = None,
    ) -> int:
        _validate_factor_kind(kind)
        query = """
            SELECT count(*) AS row_count
            FROM provider_factor_snapshots
            WHERE tenant_id = %(tenant_id)s
              AND kind = %(kind)s
        """
        params: dict[str, Any] = {
            "tenant_id": self._tenant_id,
            "kind": kind,
        }
        if provider_id:
            query += " AND provider_id = %(provider_id)s"
            params["provider_id"] = provider_id.strip()
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(query.strip(), params)
                row = _cursor_one(cursor)
        return int(row["row_count"] if row is not None else 0)

    def _set_tenant_context(self, cursor: Any) -> None:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %(tenant_id)s, true)",
            {"tenant_id": self._tenant_id},
        )


def _validate_factor_kind(kind: str) -> None:
    if kind not in FACTOR_KINDS:
        raise ValueError(f"Unknown provider factor kind: {kind}")


def build_provider_data_store(
    env: Mapping[str, str] | None = None,
) -> ProviderDataStore | SQLiteProviderDataStore | PostgresProviderDataStore:
    config = env if env is not None else os.environ
    profile = load_database_runtime_profile(config)
    if profile.backend == DatabaseBackend.POSTGRES:
        database_url = profile.database_url
        tenant_id = config.get("PORTFOLIO_TENANT_ID", "").strip()
        if not database_url:
            raise ValueError("PORTFOLIO_DATABASE_URL is required for Postgres provider context storage")
        if not tenant_id:
            raise ValueError("PORTFOLIO_TENANT_ID is required for Postgres provider context storage")
        return PostgresProviderDataStore(
            tenant_id=tenant_id,
            connection_factory=_postgres_connection_factory(database_url),
        )
    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if db_path:
        return SQLiteProviderDataStore(db_path)
    return ProviderDataStore()


def _read_only_count(
    env: Mapping[str, str] | None,
    table: str,
    filters: Mapping[str, str],
) -> int:
    config = env if env is not None else os.environ
    profile = load_database_runtime_profile(config)
    if profile.backend == DatabaseBackend.POSTGRES:
        store = build_provider_data_store(config)
        if table == "provider_universe_members":
            return store.count_universe_members(filters.get("provider_id"))
        if table == "provider_factor_snapshots":
            return store.count_factor_snapshots(
                filters["kind"],
                filters.get("provider_id"),
            )
        return 0

    db_path = config.get(MARKET_DATA_DB_ENV, "").strip()
    if not db_path:
        return 0

    path = Path(db_path)
    if not path.is_file():
        return 0

    query = f"select count(*) as row_count from {table}"
    params: list[str] = []
    if filters:
        query += " where " + " and ".join(f"{key} = ?" for key in filters)
        params.extend(filters.values())

    try:
        with sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(query, params).fetchone()
    except sqlite3.OperationalError:
        return 0
    return int(row["row_count"] if row is not None else 0)


def count_stored_universe_members(
    env: Mapping[str, str] | None = None,
    provider_id: str | None = None,
) -> int:
    filters = {"provider_id": provider_id.strip()} if provider_id else {}
    return _read_only_count(env, "provider_universe_members", filters)


def count_stored_factor_snapshots(
    kind: str,
    env: Mapping[str, str] | None = None,
    provider_id: str | None = None,
) -> int:
    _validate_factor_kind(kind)
    filters = {"kind": kind}
    if provider_id:
        filters["provider_id"] = provider_id.strip()
    return _read_only_count(env, "provider_factor_snapshots", filters)


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


def _cursor_one(cursor: Any) -> dict[str, Any] | None:
    row = cursor.fetchone()
    if row is None:
        return None
    return _row_mapping(cursor, row)


def _row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if not isinstance(row, Sequence):
        raise TypeError("Postgres provider context cursor rows must be mappings or sequences")
    description = getattr(cursor, "description", None)
    if not description:
        raise TypeError("Postgres provider context sequence rows require description")
    keys = [str(column[0]) for column in description]
    return dict(zip(keys, row, strict=False))


def _payload_from_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = row["payload"]
    if isinstance(payload, str):
        return _from_json(payload)
    if isinstance(payload, Mapping):
        return payload
    raise TypeError("Postgres provider context payload must be a mapping or JSON string")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
