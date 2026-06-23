from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .models import (
    MarketDataSnapshot,
    ProviderConfigurationProfile,
    ProviderImportJob,
    ProviderImportValidation,
)
from .market_data_store import build_market_data_store
from .providers import (
    CONFIGURED_JSON_SOURCE,
    list_configured_market_data_snapshots,
    validate_configured_provider_imports,
)

PROVIDER_CONFIG_DB_ENV = "PROVIDER_CONFIG_DB_PATH"
PROFILE_UPDATED_AT = "2026-06-22T09:20:00+05:30"
JOB_TIMESTAMP = "2026-06-22T09:21:00+05:30"
SENSITIVE_METRIC_KEY_PARTS = (
    "api_key",
    "apikey",
    "access_key",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)


def _to_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _from_json(value: str) -> Any:
    return json.loads(value)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _profile_id(provider_id: str) -> str:
    return f"profile-{_slug(provider_id)}"


def _path_env(validation: ProviderImportValidation) -> str:
    if len(validation.required_env) >= 2:
        return validation.required_env[1]
    return ""


def _source_label(validation: ProviderImportValidation) -> str:
    path_env = _path_env(validation)
    if validation.provider_mode == "json_file" and path_env:
        return f"env:{path_env}"
    if validation.provider_mode == "fixture":
        return "fixture_provider"
    return f"provider_mode:{validation.provider_mode}"


def _profile_from_validation(
    validation: ProviderImportValidation,
) -> ProviderConfigurationProfile:
    path_env = _path_env(validation)
    return ProviderConfigurationProfile(
        profile_id=_profile_id(validation.provider_id),
        provider_id=validation.provider_id,
        kind=validation.kind,
        display_name=validation.display_name,
        configured=validation.configured,
        provider_mode=validation.provider_mode,
        required_env=validation.required_env,
        path_env=path_env,
        source_label=_source_label(validation),
        last_validation_status=validation.status,
        missing_env=validation.missing_env,
        payload_count=validation.payload_count,
        sample_identifiers=validation.sample_identifiers or [],
        updated_at=PROFILE_UPDATED_AT,
        notes=[
            "Profile metadata is derived from configured provider environment keys.",
            "Raw provider payloads and resolved file path values are not persisted.",
        ],
    )


def _job_status(validation_status: str) -> str:
    if validation_status == "valid":
        return "completed"
    if validation_status == "not_configured":
        return "skipped"
    return "needs_attention"


def _contains_sensitive_key(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_METRIC_KEY_PARTS)


def _safe_metrics(
    metrics: Mapping[str, float | int | str],
) -> dict[str, float | int | str]:
    return {
        str(key): value
        for key, value in metrics.items()
        if not _contains_sensitive_key(str(key))
    }


def _safe_market_snapshot(snapshot: MarketDataSnapshot) -> MarketDataSnapshot:
    return MarketDataSnapshot(
        provider_id=snapshot.provider_id,
        source=CONFIGURED_JSON_SOURCE,
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        bars=snapshot.bars,
        latest_close=snapshot.latest_close,
        metrics=_safe_metrics(snapshot.metrics),
        notes=[
            "Configured market data snapshot imported through provider refresh.",
            "Resolved source paths and raw provider payload details were not persisted.",
        ],
    )


def _safe_execution_error(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return "Configured provider payload is missing a required field."
    if isinstance(exc, OSError):
        return "Configured provider file is not readable."
    message = str(exc).strip()
    if not message:
        return "Configured provider import failed."
    return message


def _execution_result(
    validation: ProviderImportValidation,
    env: Mapping[str, str] | None,
    attempt: int,
) -> dict[str, Any]:
    base_event: dict[str, Any] = {
        "provider_id": validation.provider_id,
        "kind": validation.kind,
        "provider_mode": validation.provider_mode,
        "validation_status": validation.status,
        "attempt": attempt,
    }
    if validation.status == "not_configured":
        return {
            "status": "skipped",
            "progress_state": "skipped",
            "imported_count": 0,
            "skipped_count": 0,
            "target_store": "none",
            "message": validation.message,
            "audit_event": {
                **base_event,
                "event_type": "provider_import_skipped",
                "imported_count": 0,
                "skipped_count": 0,
                "target_store": "none",
            },
        }
    if validation.status != "valid":
        return {
            "status": "needs_attention",
            "progress_state": "validation_failed",
            "imported_count": 0,
            "skipped_count": validation.payload_count or 0,
            "target_store": "none",
            "message": validation.message,
            "audit_event": {
                **base_event,
                "event_type": "provider_import_validation_failed",
                "imported_count": 0,
                "skipped_count": validation.payload_count or 0,
                "target_store": "none",
            },
        }
    if validation.kind != "market_data":
        return {
            "status": "completed",
            "progress_state": "validated_metadata_only",
            "imported_count": 0,
            "skipped_count": validation.payload_count or 0,
            "target_store": "metadata_only",
            "message": validation.message,
            "audit_event": {
                **base_event,
                "event_type": "provider_import_validated",
                "imported_count": 0,
                "skipped_count": validation.payload_count or 0,
                "target_store": "metadata_only",
            },
        }

    try:
        snapshots = [
            _safe_market_snapshot(snapshot)
            for snapshot in list_configured_market_data_snapshots(env=env)
        ]
        market_store = build_market_data_store(env=env)
        for snapshot in snapshots:
            market_store.record_market_snapshot(snapshot)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        message = _safe_execution_error(exc)
        return {
            "status": "needs_attention",
            "progress_state": "import_failed",
            "imported_count": 0,
            "skipped_count": validation.payload_count or 0,
            "target_store": "market_data_snapshots",
            "message": message,
            "audit_event": {
                **base_event,
                "event_type": "provider_import_failed",
                "imported_count": 0,
                "skipped_count": validation.payload_count or 0,
                "target_store": "market_data_snapshots",
            },
        }

    return {
        "status": "completed",
        "progress_state": "imported",
        "imported_count": len(snapshots),
        "skipped_count": 0,
        "target_store": "market_data_snapshots",
        "message": validation.message,
        "audit_event": {
            **base_event,
            "event_type": "provider_import_executed",
            "imported_count": len(snapshots),
            "skipped_count": 0,
            "target_store": "market_data_snapshots",
        },
    }


def _job_from_validation(
    validation: ProviderImportValidation,
    trigger: str,
    sequence: int,
    execution: Mapping[str, Any],
) -> ProviderImportJob:
    profile_id = _profile_id(validation.provider_id)
    return ProviderImportJob(
        job_id=f"provider-import-{_slug(validation.provider_id)}-{sequence:03d}",
        profile_id=profile_id,
        provider_id=validation.provider_id,
        kind=validation.kind,
        status=str(execution.get("status") or _job_status(validation.status)),
        trigger=trigger.strip() or "manual",
        provider_mode=validation.provider_mode,
        source_label=_source_label(validation),
        validation_status=validation.status,
        payload_count=validation.payload_count,
        sample_identifiers=validation.sample_identifiers or [],
        message=str(execution.get("message") or validation.message),
        started_at=JOB_TIMESTAMP,
        completed_at=JOB_TIMESTAMP,
        progress_state=str(execution.get("progress_state") or "metadata_only"),
        attempts=sequence,
        imported_count=int(execution.get("imported_count") or 0),
        skipped_count=int(execution.get("skipped_count") or 0),
        target_store=str(execution.get("target_store") or "metadata_only"),
        audit_event=dict(execution.get("audit_event") or {}),
        notes=[
            "Provider import refresh records sanitized execution metadata.",
            "No raw provider payload, account data, credential, or resolved path is stored.",
        ],
    )


def _profile_from_dict(payload: Mapping[str, Any]) -> ProviderConfigurationProfile:
    return ProviderConfigurationProfile(
        profile_id=str(payload["profile_id"]),
        provider_id=str(payload["provider_id"]),
        kind=str(payload["kind"]),
        display_name=str(payload["display_name"]),
        configured=bool(payload["configured"]),
        provider_mode=str(payload["provider_mode"]),
        required_env=[str(item) for item in payload["required_env"]],
        path_env=str(payload["path_env"]),
        source_label=str(payload["source_label"]),
        last_validation_status=str(payload["last_validation_status"]),
        missing_env=[str(item) for item in payload["missing_env"]],
        payload_count=(
            None
            if payload.get("payload_count") is None
            else int(payload["payload_count"])
        ),
        sample_identifiers=[str(item) for item in payload["sample_identifiers"]],
        updated_at=str(payload["updated_at"]),
        notes=[str(item) for item in payload["notes"]],
    )


def _job_from_dict(payload: Mapping[str, Any]) -> ProviderImportJob:
    return ProviderImportJob(
        job_id=str(payload["job_id"]),
        profile_id=str(payload["profile_id"]),
        provider_id=str(payload["provider_id"]),
        kind=str(payload["kind"]),
        status=str(payload["status"]),
        trigger=str(payload["trigger"]),
        provider_mode=str(payload["provider_mode"]),
        source_label=str(payload["source_label"]),
        validation_status=str(payload["validation_status"]),
        payload_count=(
            None
            if payload.get("payload_count") is None
            else int(payload["payload_count"])
        ),
        sample_identifiers=[str(item) for item in payload["sample_identifiers"]],
        message=str(payload["message"]),
        started_at=str(payload["started_at"]),
        completed_at=str(payload["completed_at"]),
        progress_state=str(payload.get("progress_state") or payload["status"]),
        attempts=int(payload.get("attempts") or 1),
        imported_count=int(payload.get("imported_count") or 0),
        skipped_count=int(payload.get("skipped_count") or 0),
        target_store=str(payload.get("target_store") or "metadata_only"),
        audit_event=dict(payload.get("audit_event") or {}),
        notes=[str(item) for item in payload["notes"]],
    )


class ProviderProfileStore:
    """In-memory provider profile store for unconfigured local runs."""

    def __init__(self) -> None:
        self._profiles: dict[str, ProviderConfigurationProfile] = {}
        self._jobs: dict[str, ProviderImportJob] = {}

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "memory",
            "backend": "memory",
            "configured": False,
            "path_configured": False,
        }

    def upsert_profile(
        self,
        profile: ProviderConfigurationProfile,
    ) -> ProviderConfigurationProfile:
        self._profiles[profile.profile_id] = profile
        return profile

    def list_profiles(self, limit: int = 20) -> list[ProviderConfigurationProfile]:
        profiles = sorted(self._profiles.values(), key=lambda item: item.profile_id)
        return profiles[: max(0, limit)]

    def record_import_job(self, job: ProviderImportJob) -> ProviderImportJob:
        self._jobs[job.job_id] = job
        return job

    def list_import_jobs(self, limit: int = 20) -> list[ProviderImportJob]:
        jobs = sorted(
            self._jobs.values(),
            key=lambda item: (item.completed_at, item.job_id),
            reverse=True,
        )
        return jobs[: max(0, limit)]


class SQLiteProviderProfileStore(ProviderProfileStore):
    """SQLite-backed provider profile and import-job metadata store."""

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

    def upsert_profile(
        self,
        profile: ProviderConfigurationProfile,
    ) -> ProviderConfigurationProfile:
        with self._connect() as connection:
            connection.execute(
                """
                insert into provider_profiles (
                    profile_id,
                    provider_id,
                    kind,
                    source_label,
                    payload_json,
                    updated_at
                ) values (?, ?, ?, ?, ?, ?)
                on conflict(profile_id) do update set
                    provider_id = excluded.provider_id,
                    kind = excluded.kind,
                    source_label = excluded.source_label,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.profile_id,
                    profile.provider_id,
                    profile.kind,
                    profile.source_label,
                    _to_json(profile.to_dict()),
                    profile.updated_at,
                ),
            )
            connection.commit()
        return profile

    def list_profiles(self, limit: int = 20) -> list[ProviderConfigurationProfile]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select payload_json from provider_profiles
                order by profile_id
                limit ?
                """,
                (max(0, limit),),
            ).fetchall()
        return [_profile_from_dict(_from_json(row["payload_json"])) for row in rows]

    def record_import_job(self, job: ProviderImportJob) -> ProviderImportJob:
        with self._connect() as connection:
            connection.execute(
                """
                insert into provider_import_jobs (
                    job_id,
                    profile_id,
                    provider_id,
                    kind,
                    status,
                    source_label,
                    payload_json,
                    completed_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(job_id) do update set
                    profile_id = excluded.profile_id,
                    provider_id = excluded.provider_id,
                    kind = excluded.kind,
                    status = excluded.status,
                    source_label = excluded.source_label,
                    payload_json = excluded.payload_json,
                    completed_at = excluded.completed_at
                """,
                (
                    job.job_id,
                    job.profile_id,
                    job.provider_id,
                    job.kind,
                    job.status,
                    job.source_label,
                    _to_json(job.to_dict()),
                    job.completed_at,
                ),
            )
            connection.commit()
        return job

    def list_import_jobs(self, limit: int = 20) -> list[ProviderImportJob]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                select payload_json from provider_import_jobs
                order by completed_at desc, job_id desc
                limit ?
                """,
                (max(0, limit),),
            ).fetchall()
        return [_job_from_dict(_from_json(row["payload_json"])) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists provider_profiles (
                    profile_id text primary key,
                    provider_id text not null,
                    kind text not null,
                    source_label text not null,
                    payload_json text not null,
                    updated_at text not null
                );

                create table if not exists provider_import_jobs (
                    job_id text primary key,
                    profile_id text not null,
                    provider_id text not null,
                    kind text not null,
                    status text not null,
                    source_label text not null,
                    payload_json text not null,
                    completed_at text not null
                );
                """
            )
            connection.commit()


def build_provider_profile_store(
    env: Mapping[str, str] | None = None,
) -> ProviderProfileStore:
    config = env if env is not None else os.environ
    db_path = str(config.get(PROVIDER_CONFIG_DB_ENV, "")).strip()
    if db_path:
        return SQLiteProviderProfileStore(db_path)
    return ProviderProfileStore()


def get_provider_profile_storage_status(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return build_provider_profile_store(env=env).storage_status()


def list_provider_configuration_profiles(
    env: Mapping[str, str] | None = None,
) -> list[ProviderConfigurationProfile]:
    return [
        _profile_from_validation(validation)
        for validation in validate_configured_provider_imports(env=env)
    ]


def refresh_provider_import_profile_metadata(
    provider_id: str,
    env: Mapping[str, str] | None = None,
    trigger: str = "manual",
) -> ProviderImportJob:
    normalized_provider_id = provider_id.strip()
    validations = {
        validation.provider_id: validation
        for validation in validate_configured_provider_imports(env=env)
    }
    try:
        validation = validations[normalized_provider_id]
    except KeyError as exc:
        raise ValueError(f"Unknown configured provider profile: {provider_id}") from exc

    store = build_provider_profile_store(env=env)
    sequence = (
        sum(
            1
            for job in store.list_import_jobs(limit=1000)
            if job.provider_id == normalized_provider_id
        )
        + 1
    )
    store.upsert_profile(_profile_from_validation(validation))
    execution = _execution_result(validation, env=env, attempt=sequence)
    return store.record_import_job(
        _job_from_validation(validation, trigger, sequence, execution)
    )


def list_provider_import_jobs(
    env: Mapping[str, str] | None = None,
    limit: int = 20,
) -> list[ProviderImportJob]:
    return build_provider_profile_store(env=env).list_import_jobs(limit=limit)
