from __future__ import annotations

import json
from pathlib import Path

from portfolio_domain.provider_profiles import (
    PostgresProviderProfileStore,
    PROVIDER_CONFIG_DB_ENV,
    build_provider_profile_store,
    list_provider_configuration_profiles,
    list_provider_import_reconciliation,
    list_provider_import_jobs,
    refresh_provider_import_profile_metadata,
)
from portfolio_domain.market_data_store import SQLiteMarketDataStore
from portfolio_domain.models import ProviderImportJob


def _write_market_snapshot(tmp_path) -> str:
    json_path = tmp_path / "private-market-snapshots.json"
    json_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(json_path),
                        "as_of": "2026-06-22",
                        "bars": [
                            {
                                "date": "2026-06-22",
                                "open": 100.0,
                                "high": 104.0,
                                "low": 98.0,
                                "close": 102.0,
                                "volume": 100000,
                            }
                        ],
                        "metrics": {
                            "atr_pct": 2.1,
                            "median_turnover_cr": 6.2,
                            "roc20_pct": 5.4,
                            "rsi14": 57.0,
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-market-snapshots token leak candidate"],
                    }
                ]
            }
        )
    )
    return str(json_path)


def test_provider_profiles_are_metadata_only_and_path_safe(tmp_path) -> None:
    json_path = _write_market_snapshot(tmp_path)
    env = {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
    }

    profiles = [
        profile.to_dict() for profile in list_provider_configuration_profiles(env=env)
    ]
    by_provider = {profile["provider_id"]: profile for profile in profiles}

    market_profile = by_provider["configured_market_data"]
    assert market_profile["profile_id"] == "profile-configured-market-data"
    assert market_profile["provider_mode"] == "json_file"
    assert market_profile["source_label"] == "env:PORTFOLIO_MARKET_DATA_JSON_PATH"
    assert market_profile["path_env"] == "PORTFOLIO_MARKET_DATA_JSON_PATH"
    assert market_profile["last_validation_status"] == "valid"
    assert market_profile["payload_count"] == 1
    assert market_profile["sample_identifiers"] == ["DEMODATA"]

    combined = f"{profiles}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-snapshots" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


TENANT_ID = "11111111-1111-1111-1111-111111111111"


class _FakeCursor:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.executed: list[tuple[str, dict]] = []
        self._rows = rows or []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def execute(self, sql: str, params: dict) -> None:
        self.executed.append((sql, params))

    def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)

    def fetchall(self):
        if not self._rows:
            return []
        return [self._rows.pop(0)]


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self.cursor_instance = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True


def test_migration_adds_tenant_scoped_provider_profile_metadata_tables() -> None:
    migration = Path(
        "infra/db/alembic/versions/20260727_0009_provider_profile_store.py"
    ).read_text()

    assert 'revision = "20260727_0009"' in migration
    assert 'down_revision = "20260727_0008"' in migration
    assert "provider_configuration_profiles" in migration
    assert "provider_import_jobs" in migration
    assert "tenant_id" in migration
    assert "payload" in migration
    assert "jsonb" in migration.lower()
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "tenant_isolation_{table_name}" in migration
    assert "DROP POLICY IF EXISTS" in migration
    assert "access_token" not in migration
    assert "credential" not in migration


def test_postgres_provider_profile_store_records_tenant_scoped_metadata_without_paths(
    tmp_path,
) -> None:
    json_path = _write_market_snapshot(tmp_path)
    env = {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
    }
    profile = {
        item.provider_id: item for item in list_provider_configuration_profiles(env=env)
    }["configured_market_data"]
    cursor = _FakeCursor()
    connection = _FakeConnection(cursor)
    store = PostgresProviderProfileStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    stored = store.upsert_profile(profile)

    tenant_sql, tenant_params = cursor.executed[0]
    sql, params = cursor.executed[1]
    serialized = f"{sql} {params}".lower()
    assert "set_config('app.tenant_id'" in tenant_sql
    assert tenant_params == {"tenant_id": TENANT_ID}
    assert "INSERT INTO provider_configuration_profiles" in sql
    assert "ON CONFLICT (tenant_id, profile_id)" in sql
    assert params["tenant_id"] == TENANT_ID
    assert params["profile_id"] == "profile-configured-market-data"
    assert params["provider_id"] == "configured_market_data"
    assert params["payload"] == profile.to_dict()
    assert stored.to_dict() == profile.to_dict()
    assert connection.committed is True
    assert str(tmp_path).lower() not in serialized
    assert "private-market-snapshots" not in serialized
    assert "access_token" not in serialized
    assert "secret" not in serialized


def test_postgres_provider_profile_store_reads_profiles_and_jobs() -> None:
    profile = list_provider_configuration_profiles()[0]
    job = ProviderImportJob(
        job_id="provider-import-configured-market-data-001",
        profile_id=profile.profile_id,
        provider_id=profile.provider_id,
        kind=profile.kind,
        status="skipped",
        trigger="contract_test",
        provider_mode=profile.provider_mode,
        source_label=profile.source_label,
        validation_status=profile.last_validation_status,
        payload_count=profile.payload_count,
        sample_identifiers=profile.sample_identifiers,
        message="fixture provider remains active",
        started_at="2026-06-22T09:21:00+05:30",
        completed_at="2026-06-22T09:21:00+05:30",
        progress_state="skipped",
        attempts=1,
        imported_count=0,
        skipped_count=0,
        target_store="none",
        audit_event={
            "event_type": "provider_import_skipped",
            "provider_id": profile.provider_id,
        },
        notes=[
            "Provider import refresh records sanitized execution metadata.",
            "No raw provider payload, account data, sensitive value, or resolved path is stored.",
        ],
    )
    cursor = _FakeCursor(
        rows=[
            {"payload": profile.to_dict()},
            {"payload": job.to_dict()},
        ]
    )
    connection = _FakeConnection(cursor)
    store = PostgresProviderProfileStore(
        tenant_id=TENANT_ID,
        connection_factory=lambda: connection,
    )

    profiles = store.list_profiles(limit=5)
    jobs = store.list_import_jobs(limit=5)

    profile_tenant_sql, profile_tenant_params = cursor.executed[0]
    profile_sql, profile_params = cursor.executed[1]
    job_tenant_sql, job_tenant_params = cursor.executed[2]
    job_sql, job_params = cursor.executed[3]
    assert "set_config('app.tenant_id'" in profile_tenant_sql
    assert profile_tenant_params == {"tenant_id": TENANT_ID}
    assert "FROM provider_configuration_profiles" in profile_sql
    assert "tenant_id = %(tenant_id)s" in profile_sql
    assert profile_params == {"tenant_id": TENANT_ID, "limit": 5}
    assert "set_config('app.tenant_id'" in job_tenant_sql
    assert job_tenant_params == {"tenant_id": TENANT_ID}
    assert "FROM provider_import_jobs" in job_sql
    assert "tenant_id = %(tenant_id)s" in job_sql
    assert job_params == {"tenant_id": TENANT_ID, "limit": 5}
    assert [item.to_dict() for item in profiles] == [profile.to_dict()]
    assert [item.to_dict() for item in jobs] == [job.to_dict()]


def test_provider_profile_store_uses_postgres_for_production_like_backend() -> None:
    store = build_provider_profile_store(
        {
            "PORTFOLIO_STORAGE_BACKEND": "postgres",
            "PORTFOLIO_DATABASE_URL": "postgresql+psycopg://portfolio:secret@db:5432/portfolio_agentic",
            "PORTFOLIO_TENANT_ID": TENANT_ID,
        }
    )

    assert isinstance(store, PostgresProviderProfileStore)
    assert store.storage_status() == {
        "status": "persisted",
        "backend": "postgres",
        "configured": True,
        "tenant_scoped": True,
    }


def test_provider_import_refresh_tracks_job_without_storing_payload_or_path(
    tmp_path,
) -> None:
    json_path = _write_market_snapshot(tmp_path)
    env = {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
    }

    job = refresh_provider_import_profile_metadata(
        "configured_market_data",
        env=env,
        trigger="contract_test",
    )
    retry_job = refresh_provider_import_profile_metadata(
        "configured_market_data",
        env=env,
        trigger="contract_test_retry",
    )
    jobs = [item.to_dict() for item in list_provider_import_jobs(env=env)]

    assert job.status == "completed"
    assert retry_job.status == "completed"
    assert retry_job.job_id != job.job_id
    assert job.validation_status == "valid"
    assert job.payload_count == 1
    assert job.sample_identifiers == ["DEMODATA"]
    assert jobs[0]["job_id"] == retry_job.job_id
    assert jobs[0]["trigger"] == "contract_test_retry"
    assert jobs[1]["job_id"] == job.job_id
    assert jobs[1]["trigger"] == "contract_test"
    assert jobs[0]["source_label"] == "env:PORTFOLIO_MARKET_DATA_JSON_PATH"

    combined = f"{job.to_dict()} {jobs}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-snapshots" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_provider_refresh_execution_imports_market_snapshots_to_structured_store(
    tmp_path,
) -> None:
    json_path = _write_market_snapshot(tmp_path)
    market_db = tmp_path / "market-data.db"
    env = {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        "MARKET_DATA_DB_PATH": str(market_db),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
    }

    job = refresh_provider_import_profile_metadata(
        "configured_market_data",
        env=env,
        trigger="execution_test",
    )
    stored = SQLiteMarketDataStore(market_db).get_market_snapshot(
        "DEMODATA",
        provider_id="configured_market_data",
    )

    assert job.status == "completed"
    assert job.progress_state == "imported"
    assert job.attempts == 1
    assert job.imported_count == 1
    assert job.skipped_count == 0
    assert job.target_store == "market_data_snapshots"
    assert job.audit_event["event_type"] == "provider_import_executed"
    assert job.audit_event["provider_id"] == "configured_market_data"
    assert job.audit_event["imported_count"] == 1
    assert stored.symbol == "DEMODATA"
    assert stored.provider_id == "configured_market_data"

    combined = f"{job.to_dict()} {stored.to_dict()}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-snapshots" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_provider_import_reconciliation_compares_preview_job_and_cache_counts_safely(
    tmp_path,
) -> None:
    json_path = _write_market_snapshot(tmp_path)
    market_db = tmp_path / "market-data.db"
    env = {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        "MARKET_DATA_DB_PATH": str(market_db),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
    }

    before = list_provider_import_reconciliation(env=env)
    before_market = {
        item["provider_id"]: item for item in before
    }["configured_market_data"]

    assert before_market["reconciliation_status"] == "pending_refresh"
    assert before_market["preview"]["normalized_count"] == 1
    assert before_market["latest_job"]["status"] == "none"
    assert before_market["store"]["stored_count"] == 0

    job = refresh_provider_import_profile_metadata(
        "configured_market_data",
        env=env,
        trigger="reconciliation_test",
    )
    synced = list_provider_import_reconciliation(env=env)
    synced_market = {
        item["provider_id"]: item for item in synced
    }["configured_market_data"]

    assert job.status == "completed"
    assert synced_market["reconciliation_status"] == "in_sync"
    assert synced_market["preview"]["normalized_count"] == 1
    assert synced_market["latest_job"]["job_id"] == job.job_id
    assert synced_market["latest_job"]["imported_count"] == 1
    assert synced_market["store"]["target_store"] == "market_data_snapshots"
    assert synced_market["store"]["stored_count"] == 1
    assert synced_market["deltas"] == {
        "preview_minus_store": 0,
        "latest_job_minus_store": 0,
    }

    source_payload = json.loads(Path(json_path).read_text())
    source_payload["snapshots"].append(
        {
            "symbol": "NEWDATA",
            "source": str(json_path),
            "as_of": "2026-06-22",
            "bars": [
                {
                    "date": "2026-06-22",
                    "open": 200.0,
                    "high": 204.0,
                    "low": 198.0,
                    "close": 202.0,
                    "volume": 200000,
                }
            ],
            "metrics": {
                "atr_pct": 2.9,
                "api_token": "should_not_persist",
            },
            "notes": ["private-market-snapshots token leak candidate"],
        }
    )
    Path(json_path).write_text(json.dumps(source_payload))

    changed = list_provider_import_reconciliation(env=env)
    changed_market = {
        item["provider_id"]: item for item in changed
    }["configured_market_data"]

    assert changed_market["reconciliation_status"] == "source_changed"
    assert changed_market["preview"]["normalized_count"] == 2
    assert changed_market["latest_job"]["imported_count"] == 1
    assert changed_market["store"]["stored_count"] == 1
    assert changed_market["deltas"] == {
        "preview_minus_store": 1,
        "latest_job_minus_store": 0,
    }

    combined = f"{before} {synced} {changed}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-snapshots" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
