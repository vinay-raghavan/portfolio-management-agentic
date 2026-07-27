from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

from .database_runtime import DatabaseBackend
from .database_runtime import load_database_runtime_profile
from .models import (
    FundamentalsSnapshot,
    MacroSnapshot,
    MarketDataSnapshot,
    ProviderConfigurationProfile,
    ProviderImportJob,
    ProviderImportValidation,
    SentimentSnapshot,
    UniverseMembers,
    VolatilitySnapshot,
)
from .market_data_store import build_market_data_store
from .market_data_store import count_stored_market_snapshots
from .provider_data_store import build_provider_data_store
from .provider_data_store import count_stored_factor_snapshots
from .provider_data_store import count_stored_universe_members
from .providers import (
    CONFIGURED_JSON_SOURCE,
    list_configured_fundamentals_snapshots,
    list_configured_macro_snapshots,
    list_configured_market_data_snapshots,
    list_configured_sentiment_snapshots,
    list_configured_universe_members,
    list_configured_volatility_snapshots,
    validate_configured_provider_imports,
)

PROVIDER_CONFIG_DB_ENV = "PROVIDER_CONFIG_DB_PATH"
PROFILE_UPDATED_AT = "2026-06-22T09:20:00+05:30"
JOB_TIMESTAMP = "2026-06-22T09:21:00+05:30"
REFRESH_ORCHESTRATION_TIMESTAMP = "2026-06-22T09:30:00+05:30"
DEFAULT_STALE_AFTER_SECONDS = 86_400
BASE_RETRY_AFTER_SECONDS = 900
MAX_RETRY_AFTER_SECONDS = 21_600
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


def _safe_universe_members(members: UniverseMembers) -> UniverseMembers:
    return UniverseMembers(
        provider_id=members.provider_id,
        universe_id=members.universe_id,
        source=CONFIGURED_JSON_SOURCE,
        as_of=members.as_of,
        symbols=members.symbols,
        notes=[
            "Configured universe membership imported through provider refresh.",
            "Resolved source paths and raw provider payload details were not persisted.",
        ],
    )


def _safe_fundamentals_snapshot(
    snapshot: FundamentalsSnapshot,
) -> FundamentalsSnapshot:
    return FundamentalsSnapshot(
        provider_id=snapshot.provider_id,
        source=CONFIGURED_JSON_SOURCE,
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        metrics=_safe_metrics(snapshot.metrics),
        notes=[
            "Configured fundamentals snapshot imported through provider refresh.",
            "Resolved source paths and raw provider payload details were not persisted.",
        ],
    )


def _safe_sentiment_snapshot(snapshot: SentimentSnapshot) -> SentimentSnapshot:
    return SentimentSnapshot(
        provider_id=snapshot.provider_id,
        source=CONFIGURED_JSON_SOURCE,
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        metrics=_safe_metrics(snapshot.metrics),
        notes=[
            "Configured sentiment snapshot imported through provider refresh.",
            "Resolved source paths and raw provider payload details were not persisted.",
        ],
    )


def _safe_volatility_snapshot(snapshot: VolatilitySnapshot) -> VolatilitySnapshot:
    return VolatilitySnapshot(
        provider_id=snapshot.provider_id,
        source=CONFIGURED_JSON_SOURCE,
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        metrics=_safe_metrics(snapshot.metrics),
        notes=[
            "Configured volatility snapshot imported through provider refresh.",
            "Resolved source paths and raw provider payload details were not persisted.",
        ],
    )


def _safe_macro_snapshot(snapshot: MacroSnapshot) -> MacroSnapshot:
    return MacroSnapshot(
        provider_id=snapshot.provider_id,
        source=CONFIGURED_JSON_SOURCE,
        symbol=snapshot.symbol,
        as_of=snapshot.as_of,
        metrics=_safe_metrics(snapshot.metrics),
        notes=[
            "Configured macro snapshot imported through provider refresh.",
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


def _preview_valid_import(
    validation: ProviderImportValidation,
    env: Mapping[str, str] | None,
) -> tuple[str, int]:
    if validation.kind == "market_data":
        snapshots = [
            _safe_market_snapshot(snapshot)
            for snapshot in list_configured_market_data_snapshots(env=env)
        ]
        return "market_data_snapshots", len(snapshots)
    if validation.kind == "universe":
        universes = [
            _safe_universe_members(members)
            for members in list_configured_universe_members(env=env)
        ]
        return "provider_universe_members", len(universes)
    if validation.kind == "fundamentals":
        snapshots = [
            _safe_fundamentals_snapshot(snapshot)
            for snapshot in list_configured_fundamentals_snapshots(env=env)
        ]
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "sentiment":
        snapshots = [
            _safe_sentiment_snapshot(snapshot)
            for snapshot in list_configured_sentiment_snapshots(env=env)
        ]
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "volatility":
        snapshots = [
            _safe_volatility_snapshot(snapshot)
            for snapshot in list_configured_volatility_snapshots(env=env)
        ]
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "macro":
        snapshots = [
            _safe_macro_snapshot(snapshot)
            for snapshot in list_configured_macro_snapshots(env=env)
        ]
        return "provider_factor_snapshots", len(snapshots)
    raise ValueError("Unknown configured provider kind.")


def _preview_status(validation_status: str) -> str:
    if validation_status == "valid":
        return "ready"
    if validation_status == "not_configured":
        return "skipped"
    return "needs_attention"


def _preview_warnings(
    validation: ProviderImportValidation,
    normalized_count: int,
) -> list[str]:
    if validation.status == "not_configured":
        return ["Fixture provider remains active; no configured import would run."]
    if validation.status != "valid":
        return [validation.message]
    expected_count = validation.payload_count or 0
    if expected_count != normalized_count:
        return [
            "Normalized record count differs from the validated payload count; review the configured source before refresh."
        ]
    return []


def _preview_from_validation(
    validation: ProviderImportValidation,
    env: Mapping[str, str] | None,
) -> dict[str, Any]:
    normalized_count = 0
    skipped_count = 0
    target_store = "none"
    status = _preview_status(validation.status)
    warnings: list[str] = []

    if validation.status == "valid":
        try:
            target_store, normalized_count = _preview_valid_import(validation, env=env)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            status = "needs_attention"
            skipped_count = validation.payload_count or 0
            target_store = "provider_import"
            warnings = [_safe_execution_error(exc)]
        else:
            warnings = _preview_warnings(validation, normalized_count)
    else:
        skipped_count = validation.payload_count or 0
        warnings = _preview_warnings(validation, normalized_count)

    would_write = validation.status == "valid" and status == "ready"
    return {
        "preview_id": f"provider-import-preview-{_slug(validation.provider_id)}",
        "provider_id": validation.provider_id,
        "kind": validation.kind,
        "display_name": validation.display_name,
        "status": status,
        "provider_mode": validation.provider_mode,
        "configured": validation.configured,
        "validation_status": validation.status,
        "source_label": _source_label(validation),
        "target_store": target_store,
        "payload_count": validation.payload_count,
        "normalized_count": normalized_count,
        "skipped_count": skipped_count,
        "would_write": would_write,
        "sample_identifiers": validation.sample_identifiers or [],
        "warnings": warnings,
        "notes": [
            "Dry-run preview parses and normalizes configured provider data without writing stores.",
            "Raw provider payloads, resolved paths, account data, and sensitive values are not returned.",
        ],
    }


def _execute_valid_import(
    validation: ProviderImportValidation,
    env: Mapping[str, str] | None,
) -> tuple[str, int]:
    if validation.kind == "market_data":
        snapshots = [
            _safe_market_snapshot(snapshot)
            for snapshot in list_configured_market_data_snapshots(env=env)
        ]
        market_store = build_market_data_store(env=env)
        for snapshot in snapshots:
            market_store.record_market_snapshot(snapshot)
        return "market_data_snapshots", len(snapshots)
    if validation.kind == "universe":
        universes = [
            _safe_universe_members(members)
            for members in list_configured_universe_members(env=env)
        ]
        provider_store = build_provider_data_store(env=env)
        for members in universes:
            provider_store.record_universe_members(members)
        return "provider_universe_members", len(universes)
    if validation.kind == "fundamentals":
        snapshots = [
            _safe_fundamentals_snapshot(snapshot)
            for snapshot in list_configured_fundamentals_snapshots(env=env)
        ]
        provider_store = build_provider_data_store(env=env)
        for snapshot in snapshots:
            provider_store.record_fundamentals_snapshot(snapshot)
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "sentiment":
        snapshots = [
            _safe_sentiment_snapshot(snapshot)
            for snapshot in list_configured_sentiment_snapshots(env=env)
        ]
        provider_store = build_provider_data_store(env=env)
        for snapshot in snapshots:
            provider_store.record_sentiment_snapshot(snapshot)
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "volatility":
        snapshots = [
            _safe_volatility_snapshot(snapshot)
            for snapshot in list_configured_volatility_snapshots(env=env)
        ]
        provider_store = build_provider_data_store(env=env)
        for snapshot in snapshots:
            provider_store.record_volatility_snapshot(snapshot)
        return "provider_factor_snapshots", len(snapshots)
    if validation.kind == "macro":
        snapshots = [
            _safe_macro_snapshot(snapshot)
            for snapshot in list_configured_macro_snapshots(env=env)
        ]
        provider_store = build_provider_data_store(env=env)
        for snapshot in snapshots:
            provider_store.record_macro_snapshot(snapshot)
        return "provider_factor_snapshots", len(snapshots)
    raise ValueError("Unknown configured provider kind.")


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

    try:
        target_store, imported_count = _execute_valid_import(validation, env=env)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        message = _safe_execution_error(exc)
        return {
            "status": "needs_attention",
            "progress_state": "import_failed",
            "imported_count": 0,
            "skipped_count": validation.payload_count or 0,
            "target_store": "provider_import",
            "message": message,
            "audit_event": {
                **base_event,
                "event_type": "provider_import_failed",
                "imported_count": 0,
                "skipped_count": validation.payload_count or 0,
                "target_store": "provider_import",
            },
        }

    return {
        "status": "completed",
        "progress_state": "imported",
        "imported_count": imported_count,
        "skipped_count": 0,
        "target_store": target_store,
        "message": validation.message,
        "audit_event": {
            **base_event,
            "event_type": "provider_import_executed",
            "imported_count": imported_count,
            "skipped_count": 0,
            "target_store": target_store,
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
            "No raw provider payload, account data, sensitive value, or resolved path is stored.",
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


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _retry_after_seconds(attempts: int) -> int:
    attempt_count = max(1, attempts)
    retry_after = BASE_RETRY_AFTER_SECONDS * (2 ** (attempt_count - 1))
    return min(retry_after, MAX_RETRY_AFTER_SECONDS)


def _latest_jobs_by_provider(
    jobs: list[ProviderImportJob],
) -> dict[str, ProviderImportJob]:
    latest: dict[str, ProviderImportJob] = {}
    for job in jobs:
        if job.provider_id not in latest:
            latest[job.provider_id] = job
    return latest


def _readiness_from_validation(
    validation: ProviderImportValidation,
    latest_job: ProviderImportJob | None,
    current_at: str,
    stale_after_seconds: int,
) -> dict[str, Any]:
    current_timestamp = _parse_timestamp(current_at)
    base = {
        "provider_id": validation.provider_id,
        "kind": validation.kind,
        "provider_mode": validation.provider_mode,
        "validation_status": validation.status,
        "configured": validation.configured,
        "source_label": _source_label(validation),
        "payload_count": validation.payload_count,
        "sample_identifiers": validation.sample_identifiers or [],
        "stale_after_seconds": max(0, stale_after_seconds),
        "latest_job_id": "",
        "latest_status": "none",
        "last_completed_at": "",
        "attempts": 0,
        "retry_after_seconds": 0,
        "next_attempt_at": "",
        "needs_refresh": False,
        "message": validation.message,
    }
    if validation.status == "not_configured":
        return {
            **base,
            "readiness_status": "not_configured",
        }
    if latest_job is None:
        readiness_status = (
            "pending_refresh" if validation.status == "valid" else "needs_attention"
        )
        return {
            **base,
            "readiness_status": readiness_status,
            "needs_refresh": True,
        }

    latest = {
        **base,
        "latest_job_id": latest_job.job_id,
        "latest_status": latest_job.status,
        "last_completed_at": latest_job.completed_at,
        "attempts": latest_job.attempts,
        "message": latest_job.message,
    }
    if latest_job.status == "completed":
        age_seconds = (
            current_timestamp - _parse_timestamp(latest_job.completed_at)
        ).total_seconds()
        stale = age_seconds > max(0, stale_after_seconds)
        return {
            **latest,
            "readiness_status": "stale" if stale else "ready",
            "needs_refresh": stale,
        }
    if latest_job.status == "skipped":
        return {
            **latest,
            "readiness_status": "not_configured",
        }

    retry_after = _retry_after_seconds(latest_job.attempts)
    next_attempt = _parse_timestamp(latest_job.completed_at) + timedelta(
        seconds=retry_after
    )
    retry_due = current_timestamp >= next_attempt
    return {
        **latest,
        "readiness_status": "retry_due" if retry_due else "backoff",
        "retry_after_seconds": retry_after,
        "next_attempt_at": _format_timestamp(next_attempt),
        "needs_refresh": retry_due,
    }


def _readiness_from_validations(
    validations: list[ProviderImportValidation],
    jobs: list[ProviderImportJob],
    current_at: str,
    stale_after_seconds: int,
) -> list[dict[str, Any]]:
    latest_jobs = _latest_jobs_by_provider(jobs)
    return [
        _readiness_from_validation(
            validation,
            latest_jobs.get(validation.provider_id),
            current_at=current_at,
            stale_after_seconds=stale_after_seconds,
        )
        for validation in validations
    ]


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


class PostgresProviderProfileStore(ProviderProfileStore):
    """Tenant-scoped Postgres provider profile and import-job metadata store."""

    def __init__(
        self,
        *,
        tenant_id: str,
        connection_factory: Callable[[], Any],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id is required for Postgres provider profile storage")
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

    def upsert_profile(
        self,
        profile: ProviderConfigurationProfile,
    ) -> ProviderConfigurationProfile:
        params = {
            "tenant_id": self._tenant_id,
            "profile_id": profile.profile_id,
            "provider_id": profile.provider_id,
            "kind": profile.kind,
            "source_label": profile.source_label,
            "payload": profile.to_dict(),
            "updated_at": profile.updated_at,
            "recorded_at": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    INSERT INTO provider_configuration_profiles (
                        tenant_id,
                        profile_id,
                        provider_id,
                        kind,
                        source_label,
                        payload,
                        updated_at,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(profile_id)s,
                        %(provider_id)s,
                        %(kind)s,
                        %(source_label)s,
                        %(payload)s,
                        %(updated_at)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, profile_id)
                    DO UPDATE SET
                        provider_id = EXCLUDED.provider_id,
                        kind = EXCLUDED.kind,
                        source_label = EXCLUDED.source_label,
                        payload = EXCLUDED.payload,
                        updated_at = EXCLUDED.updated_at,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return profile

    def list_profiles(self, limit: int = 20) -> list[ProviderConfigurationProfile]:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    SELECT payload
                    FROM provider_configuration_profiles
                    WHERE tenant_id = %(tenant_id)s
                    ORDER BY profile_id
                    LIMIT %(limit)s
                    """.strip(),
                    {"tenant_id": self._tenant_id, "limit": max(0, limit)},
                )
                rows = _cursor_rows(cursor)
        return [_profile_from_dict(_payload_from_row(row)) for row in rows]

    def record_import_job(self, job: ProviderImportJob) -> ProviderImportJob:
        params = {
            "tenant_id": self._tenant_id,
            "job_id": job.job_id,
            "profile_id": job.profile_id,
            "provider_id": job.provider_id,
            "kind": job.kind,
            "status": job.status,
            "source_label": job.source_label,
            "payload": job.to_dict(),
            "completed_at": job.completed_at,
            "recorded_at": _aware_utc(self._now()),
        }
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    INSERT INTO provider_import_jobs (
                        tenant_id,
                        job_id,
                        profile_id,
                        provider_id,
                        kind,
                        status,
                        source_label,
                        payload,
                        completed_at,
                        recorded_at
                    ) VALUES (
                        %(tenant_id)s,
                        %(job_id)s,
                        %(profile_id)s,
                        %(provider_id)s,
                        %(kind)s,
                        %(status)s,
                        %(source_label)s,
                        %(payload)s,
                        %(completed_at)s,
                        %(recorded_at)s
                    )
                    ON CONFLICT (tenant_id, job_id)
                    DO UPDATE SET
                        profile_id = EXCLUDED.profile_id,
                        provider_id = EXCLUDED.provider_id,
                        kind = EXCLUDED.kind,
                        status = EXCLUDED.status,
                        source_label = EXCLUDED.source_label,
                        payload = EXCLUDED.payload,
                        completed_at = EXCLUDED.completed_at,
                        recorded_at = EXCLUDED.recorded_at
                    """.strip(),
                    params,
                )
            connection.commit()
        return job

    def list_import_jobs(self, limit: int = 20) -> list[ProviderImportJob]:
        with self._connection_factory() as connection:
            with connection.cursor() as cursor:
                self._set_tenant_context(cursor)
                cursor.execute(
                    """
                    SELECT payload
                    FROM provider_import_jobs
                    WHERE tenant_id = %(tenant_id)s
                    ORDER BY completed_at DESC, job_id DESC
                    LIMIT %(limit)s
                    """.strip(),
                    {"tenant_id": self._tenant_id, "limit": max(0, limit)},
                )
                rows = _cursor_rows(cursor)
        return [_job_from_dict(_payload_from_row(row)) for row in rows]

    def _set_tenant_context(self, cursor: Any) -> None:
        cursor.execute(
            "SELECT set_config('app.tenant_id', %(tenant_id)s, true)",
            {"tenant_id": self._tenant_id},
        )


def build_provider_profile_store(
    env: Mapping[str, str] | None = None,
) -> ProviderProfileStore:
    config = env if env is not None else os.environ
    profile = load_database_runtime_profile(config)
    if profile.backend == DatabaseBackend.POSTGRES:
        database_url = profile.database_url
        tenant_id = config.get("PORTFOLIO_TENANT_ID", "").strip()
        if not database_url:
            raise ValueError("PORTFOLIO_DATABASE_URL is required for Postgres provider profile storage")
        if not tenant_id:
            raise ValueError("PORTFOLIO_TENANT_ID is required for Postgres provider profile storage")
        return PostgresProviderProfileStore(
            tenant_id=tenant_id,
            connection_factory=_postgres_connection_factory(database_url),
        )
    db_path = str(config.get(PROVIDER_CONFIG_DB_ENV, "")).strip()
    if db_path:
        return SQLiteProviderProfileStore(db_path)
    return ProviderProfileStore()


def get_provider_profile_storage_status(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    return build_provider_profile_store(env=env).storage_status()


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


def _row_mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    if not isinstance(row, Sequence):
        raise TypeError(
            "Postgres provider profile cursor rows must be mappings or sequences"
        )
    description = getattr(cursor, "description", None)
    if not description:
        raise TypeError("Postgres provider profile sequence rows require description")
    keys = [str(column[0]) for column in description]
    return dict(zip(keys, row, strict=False))


def _payload_from_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = row["payload"]
    if isinstance(payload, str):
        return _from_json(payload)
    if isinstance(payload, Mapping):
        return payload
    raise TypeError("Postgres provider profile payload must be a mapping or JSON string")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def list_provider_configuration_profiles(
    env: Mapping[str, str] | None = None,
) -> list[ProviderConfigurationProfile]:
    return [
        _profile_from_validation(validation)
        for validation in validate_configured_provider_imports(env=env)
    ]


def list_provider_import_previews(
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return dry-run import previews without initializing or writing stores."""
    return [
        _preview_from_validation(validation, env=env)
        for validation in validate_configured_provider_imports(env=env)
    ]


def _stored_count_for_preview(
    preview: Mapping[str, Any],
    env: Mapping[str, str] | None,
) -> int:
    provider_id = str(preview["provider_id"])
    kind = str(preview["kind"])
    target_store = str(preview["target_store"])
    if target_store == "market_data_snapshots":
        return count_stored_market_snapshots(env=env, provider_id=provider_id)
    if target_store == "provider_universe_members":
        return count_stored_universe_members(env=env, provider_id=provider_id)
    if target_store == "provider_factor_snapshots":
        return count_stored_factor_snapshots(
            kind,
            env=env,
            provider_id=provider_id,
        )
    return 0


def _latest_job_payload(job: ProviderImportJob | None) -> dict[str, Any]:
    if job is None:
        return {
            "job_id": "",
            "status": "none",
            "validation_status": "none",
            "imported_count": 0,
            "skipped_count": 0,
            "target_store": "none",
            "completed_at": "",
        }
    return {
        "job_id": job.job_id,
        "status": job.status,
        "validation_status": job.validation_status,
        "imported_count": job.imported_count,
        "skipped_count": job.skipped_count,
        "target_store": job.target_store,
        "completed_at": job.completed_at,
    }


def _reconciliation_status(
    preview: Mapping[str, Any],
    latest_job: ProviderImportJob | None,
    stored_count: int,
) -> str:
    preview_status = str(preview["status"])
    preview_count = int(preview["normalized_count"] or 0)
    if preview_status == "skipped":
        return "not_configured"
    if preview_status == "needs_attention":
        return "needs_attention"
    if latest_job is None:
        return "pending_refresh"
    if latest_job.status != "completed":
        return "needs_attention"
    if latest_job.imported_count != stored_count:
        return "store_mismatch"
    if preview_count != stored_count:
        return "source_changed"
    return "in_sync"


def _reconciliation_warnings(
    status: str,
    preview: Mapping[str, Any],
    latest_job: ProviderImportJob | None,
) -> list[str]:
    if status == "pending_refresh":
        return ["Configured source has not been refreshed into structured storage."]
    if status == "source_changed":
        return [
            "Configured source count differs from stored rows; run refresh before relying on configured screeners."
        ]
    if status == "store_mismatch":
        return [
            "Latest import job count differs from stored rows; inspect refresh history and rerun refresh."
        ]
    if status == "needs_attention":
        if latest_job is not None and latest_job.status != "completed":
            return ["Latest import job did not complete successfully."]
        return [str(item) for item in preview.get("warnings", [])]
    return []


def _reconciliation_next_step(status: str) -> str:
    return {
        "in_sync": "ready_for_configured_screening",
        "pending_refresh": "refresh_provider_profile",
        "source_changed": "run_provider_refresh",
        "store_mismatch": "rerun_provider_refresh",
        "needs_attention": "review_validation_or_job",
        "not_configured": "configure_provider_env",
    }.get(status, "review_provider_state")


def _reconciliation_from_preview(
    preview: Mapping[str, Any],
    latest_job: ProviderImportJob | None,
    env: Mapping[str, str] | None,
) -> dict[str, Any]:
    stored_count = _stored_count_for_preview(preview, env=env)
    status = _reconciliation_status(preview, latest_job, stored_count)
    preview_count = int(preview["normalized_count"] or 0)
    latest_imported = latest_job.imported_count if latest_job is not None else 0
    return {
        "reconciliation_id": f"provider-import-reconciliation-{_slug(str(preview['provider_id']))}",
        "provider_id": preview["provider_id"],
        "kind": preview["kind"],
        "display_name": preview["display_name"],
        "configured": preview["configured"],
        "provider_mode": preview["provider_mode"],
        "source_label": preview["source_label"],
        "reconciliation_status": status,
        "preview": {
            "status": preview["status"],
            "validation_status": preview["validation_status"],
            "target_store": preview["target_store"],
            "normalized_count": preview_count,
            "would_write": preview["would_write"],
            "sample_identifiers": preview["sample_identifiers"],
        },
        "latest_job": _latest_job_payload(latest_job),
        "store": {
            "target_store": preview["target_store"],
            "stored_count": stored_count,
        },
        "deltas": {
            "preview_minus_store": preview_count - stored_count,
            "latest_job_minus_store": latest_imported - stored_count,
        },
        "warnings": _reconciliation_warnings(status, preview, latest_job),
        "next_step": _reconciliation_next_step(status),
        "notes": [
            "Reconciliation compares dry-run preview counts, latest sanitized job counts, and structured store counts.",
            "It returns counts only, not database paths, raw provider payloads, or credential values.",
        ],
    }


def list_provider_import_reconciliation(
    env: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    previews = list_provider_import_previews(env=env)
    latest_jobs = _latest_jobs_by_provider(list_provider_import_jobs(env=env, limit=1000))
    return [
        _reconciliation_from_preview(
            preview,
            latest_jobs.get(str(preview["provider_id"])),
            env=env,
        )
        for preview in previews
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


def list_provider_refresh_readiness(
    env: Mapping[str, str] | None = None,
    current_at: str = REFRESH_ORCHESTRATION_TIMESTAMP,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> list[dict[str, Any]]:
    store = build_provider_profile_store(env=env)
    return _readiness_from_validations(
        validate_configured_provider_imports(env=env),
        store.list_import_jobs(limit=1000),
        current_at=current_at,
        stale_after_seconds=stale_after_seconds,
    )


def run_provider_refresh_schedule(
    env: Mapping[str, str] | None = None,
    trigger: str = "scheduled",
    current_at: str = REFRESH_ORCHESTRATION_TIMESTAMP,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> dict[str, Any]:
    validations = validate_configured_provider_imports(env=env)
    jobs: list[ProviderImportJob] = []
    normalized_trigger = trigger.strip() or "scheduled"
    for validation in validations:
        if validation.status == "not_configured":
            continue
        jobs.append(
            refresh_provider_import_profile_metadata(
                validation.provider_id,
                env=env,
                trigger=normalized_trigger,
            )
        )

    readiness = _readiness_from_validations(
        validations,
        jobs,
        current_at=current_at,
        stale_after_seconds=stale_after_seconds,
    )
    summary = {
        "providers_evaluated": len(validations),
        "jobs_recorded": len(jobs),
        "completed": sum(1 for job in jobs if job.status == "completed"),
        "needs_attention": sum(1 for job in jobs if job.status == "needs_attention"),
        "skipped": sum(1 for job in jobs if job.status == "skipped"),
        "ready": sum(1 for item in readiness if item["readiness_status"] == "ready"),
        "stale": sum(1 for item in readiness if item["readiness_status"] == "stale"),
        "backoff": sum(
            1 for item in readiness if item["readiness_status"] == "backoff"
        ),
        "retry_due": sum(
            1 for item in readiness if item["readiness_status"] == "retry_due"
        ),
        "not_configured": sum(
            1 for item in readiness if item["readiness_status"] == "not_configured"
        ),
    }
    return {
        "status": "needs_attention" if summary["needs_attention"] > 0 else "completed",
        "run_id": "provider-refresh-scheduled-20260622-093000",
        "trigger": normalized_trigger,
        "current_at": current_at,
        "stale_after_seconds": max(0, stale_after_seconds),
        "summary": summary,
        "jobs": [job.to_dict() for job in jobs],
        "readiness": readiness,
    }
