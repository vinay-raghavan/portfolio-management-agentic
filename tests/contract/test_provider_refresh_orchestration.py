from __future__ import annotations

import json
from pathlib import Path

from portfolio_domain.market_data_store import MARKET_DATA_DB_ENV, SQLiteMarketDataStore
from portfolio_domain.provider_data_store import SQLiteProviderDataStore
from portfolio_domain.provider_profiles import (
    PROVIDER_CONFIG_DB_ENV,
    list_provider_refresh_readiness,
    run_provider_refresh_schedule,
)


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload))
    return str(path)


def _configured_schedule_env(tmp_path) -> dict[str, str]:
    market_path = tmp_path / "private-market-schedule.json"
    macro_path = tmp_path / "private-macro-schedule.json"
    sentiment_path = tmp_path / "private-sentiment-schedule.json"
    return {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        MARKET_DATA_DB_ENV: str(tmp_path / "market-data.db"),
        "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
        "PORTFOLIO_MARKET_DATA_JSON_PATH": _write_json(
            market_path,
            {
                "snapshots": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(market_path),
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
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-market-schedule token leak candidate"],
                    }
                ]
            },
        ),
        "PORTFOLIO_MACRO_PROVIDER": "json_file",
        "PORTFOLIO_MACRO_JSON_PATH": _write_json(
            macro_path,
            {
                "macro": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(macro_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "market_regime_score": 0.72,
                            "private_key_hint": "should_not_persist",
                        },
                        "notes": ["private-macro-schedule token leak candidate"],
                    }
                ]
            },
        ),
        "PORTFOLIO_SENTIMENT_PROVIDER": "json_file",
        "PORTFOLIO_SENTIMENT_JSON_PATH": _write_json(sentiment_path, {"sentiment": []}),
    }


def test_provider_refresh_schedule_records_backoff_and_staleness(
    tmp_path,
) -> None:
    env = _configured_schedule_env(tmp_path)

    result = run_provider_refresh_schedule(
        env=env,
        trigger="scheduled_contract",
        current_at="2026-06-22T09:30:00+05:30",
    )
    readiness = {item["provider_id"]: item for item in result["readiness"]}
    market_snapshot = SQLiteMarketDataStore(
        env[MARKET_DATA_DB_ENV]
    ).get_market_snapshot(
        "DEMODATA",
        provider_id="configured_market_data",
    )
    macro_snapshot = SQLiteProviderDataStore(
        env[MARKET_DATA_DB_ENV]
    ).get_macro_snapshot(
        "DEMODATA",
        provider_id="configured_macro",
    )

    assert result["status"] == "needs_attention"
    assert result["summary"]["providers_evaluated"] == 6
    assert result["summary"]["jobs_recorded"] == 3
    assert result["summary"]["completed"] == 2
    assert result["summary"]["needs_attention"] == 1
    assert readiness["configured_market_data"]["readiness_status"] == "ready"
    assert readiness["configured_macro"]["readiness_status"] == "ready"
    assert readiness["configured_sentiment"]["readiness_status"] == "backoff"
    assert readiness["configured_sentiment"]["retry_after_seconds"] == 900
    assert readiness["configured_sentiment"]["next_attempt_at"] == (
        "2026-06-22T09:36:00+05:30"
    )
    assert readiness["configured_universe"]["readiness_status"] == "not_configured"
    assert market_snapshot.symbol == "DEMODATA"
    assert macro_snapshot.metrics["market_regime_score"] == 0.72

    stale = {
        item["provider_id"]: item
        for item in list_provider_refresh_readiness(
            env=env,
            current_at="2026-06-24T09:30:00+05:30",
            stale_after_seconds=86_400,
        )
    }
    assert stale["configured_market_data"]["readiness_status"] == "stale"
    assert stale["configured_market_data"]["needs_refresh"] is True
    assert stale["configured_macro"]["readiness_status"] == "stale"

    combined = f"{result} {stale} {market_snapshot.to_dict()} {macro_snapshot.to_dict()}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-schedule" not in combined
    assert "private-macro-schedule" not in combined
    assert "private-sentiment-schedule" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "private_key" not in combined


def test_provider_refresh_schedule_reports_current_run_readiness_without_metadata_db(
    tmp_path,
) -> None:
    env = _configured_schedule_env(tmp_path)
    env.pop(PROVIDER_CONFIG_DB_ENV)

    result = run_provider_refresh_schedule(
        env=env,
        trigger="memory_schedule_contract",
        current_at="2026-06-22T09:30:00+05:30",
    )
    readiness = {item["provider_id"]: item for item in result["readiness"]}

    assert result["summary"]["jobs_recorded"] == 3
    assert readiness["configured_market_data"]["readiness_status"] == "ready"
    assert readiness["configured_macro"]["readiness_status"] == "ready"
    assert readiness["configured_sentiment"]["readiness_status"] == "backoff"
