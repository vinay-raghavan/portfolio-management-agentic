from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse, urlunparse


class DatabaseBackend(StrEnum):
    POSTGRES = "postgres"
    SQLITE = "sqlite"


@dataclass(frozen=True)
class DatabaseRuntimeProfile:
    backend: DatabaseBackend
    database_url: str | None
    redacted_database_url: str | None
    redis_url: str | None
    redacted_redis_url: str | None
    production_like: bool
    migrations_required: bool
    alembic_config_path: str
    sqlite_paths: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend.value,
            "database_url": self.redacted_database_url,
            "redis_url": self.redacted_redis_url,
            "production_like": self.production_like,
            "migrations_required": self.migrations_required,
            "alembic_config_path": self.alembic_config_path,
            "sqlite_paths": dict(self.sqlite_paths),
        }


@dataclass(frozen=True)
class DatabaseRuntimeReadiness:
    ready: bool
    backend: DatabaseBackend
    production_like_required: bool
    blocking_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "backend": self.backend.value,
            "production_like_required": self.production_like_required,
            "blocking_reasons": list(self.blocking_reasons),
        }


def load_database_runtime_profile(env: Mapping[str, str]) -> DatabaseRuntimeProfile:
    raw_backend = env.get("PORTFOLIO_STORAGE_BACKEND", "").strip().lower()
    database_url = _blank_to_none(
        env.get("PORTFOLIO_DATABASE_URL") or env.get("DATABASE_URL")
    )
    backend = _select_backend(raw_backend, database_url)
    redis_url = _blank_to_none(env.get("REDIS_URL"))
    sqlite_paths = {
        label: value
        for label, value in {
            "paper_ledger": _blank_to_none(env.get("PAPER_LEDGER_DB_PATH")),
            "market_data": _blank_to_none(env.get("MARKET_DATA_DB_PATH")),
            "provider_config": _blank_to_none(env.get("PROVIDER_CONFIG_DB_PATH")),
        }.items()
        if value is not None
    }

    return DatabaseRuntimeProfile(
        backend=backend,
        database_url=database_url if backend == DatabaseBackend.POSTGRES else None,
        redacted_database_url=(
            _redact_url(database_url)
            if backend == DatabaseBackend.POSTGRES and database_url is not None
            else None
        ),
        redis_url=redis_url,
        redacted_redis_url=_redact_url(redis_url) if redis_url is not None else None,
        production_like=backend == DatabaseBackend.POSTGRES,
        migrations_required=backend == DatabaseBackend.POSTGRES,
        alembic_config_path=env.get("ALEMBIC_CONFIG_PATH", "infra/db/alembic.ini"),
        sqlite_paths=sqlite_paths,
    )


def evaluate_database_runtime_readiness(
    profile: DatabaseRuntimeProfile,
    *,
    require_production_like: bool = False,
) -> DatabaseRuntimeReadiness:
    blocking_reasons: list[str] = []

    if require_production_like and profile.backend != DatabaseBackend.POSTGRES:
        blocking_reasons.append("postgres_required_for_production_like_testing")
    if profile.backend == DatabaseBackend.POSTGRES and not profile.database_url:
        blocking_reasons.append("postgres_database_url_missing")
    if profile.migrations_required and not Path(profile.alembic_config_path).exists():
        blocking_reasons.append("alembic_config_missing")

    return DatabaseRuntimeReadiness(
        ready=not blocking_reasons,
        backend=profile.backend,
        production_like_required=require_production_like,
        blocking_reasons=tuple(blocking_reasons),
    )


def _select_backend(raw_backend: str, database_url: str | None) -> DatabaseBackend:
    if raw_backend == DatabaseBackend.POSTGRES.value:
        return DatabaseBackend.POSTGRES
    if raw_backend == DatabaseBackend.SQLITE.value:
        return DatabaseBackend.SQLITE
    if database_url and database_url.startswith(("postgresql://", "postgresql+")):
        return DatabaseBackend.POSTGRES
    return DatabaseBackend.SQLITE


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.password is None:
        return url

    username = parsed.username or ""
    hostname = parsed.hostname or ""
    host = hostname
    if ":" in hostname and not hostname.startswith("["):
        host = f"[{hostname}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    netloc = f"{username}:***@{host}"
    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
