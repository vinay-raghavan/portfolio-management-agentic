from __future__ import annotations

import json

from portfolio_domain.provider_profiles import (
    PROVIDER_CONFIG_DB_ENV,
    list_provider_configuration_profiles,
    list_provider_import_jobs,
    refresh_provider_import_profile_metadata,
)
from portfolio_domain.market_data_store import SQLiteMarketDataStore


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
