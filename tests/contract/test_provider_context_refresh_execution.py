from __future__ import annotations

import json
from pathlib import Path

from portfolio_domain.market_data_store import MARKET_DATA_DB_ENV
from portfolio_domain.provider_data_store import SQLiteProviderDataStore
from portfolio_domain.provider_profiles import (
    PROVIDER_CONFIG_DB_ENV,
    refresh_provider_import_profile_metadata,
)


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload))
    return str(path)


def _configured_context_env(tmp_path) -> dict[str, str]:
    universe_path = tmp_path / "private-universe-provider.json"
    fundamentals_path = tmp_path / "private-fundamentals-provider.json"
    sentiment_path = tmp_path / "private-sentiment-provider.json"
    volatility_path = tmp_path / "private-volatility-provider.json"
    macro_path = tmp_path / "private-macro-provider.json"
    return {
        PROVIDER_CONFIG_DB_ENV: str(tmp_path / "provider-config.db"),
        MARKET_DATA_DB_ENV: str(tmp_path / "market-data.db"),
        "PORTFOLIO_UNIVERSE_PROVIDER": "json_file",
        "PORTFOLIO_UNIVERSE_JSON_PATH": _write_json(
            universe_path,
            {
                "universes": [
                    {
                        "universe_id": "configured_growth",
                        "source": str(universe_path),
                        "as_of": "2026-06-22",
                        "symbols": ["DEMODATA", "SLOWDATA"],
                        "notes": ["private-universe-provider token leak candidate"],
                    }
                ]
            },
        ),
        "PORTFOLIO_FUNDAMENTALS_PROVIDER": "json_file",
        "PORTFOLIO_FUNDAMENTALS_JSON_PATH": _write_json(
            fundamentals_path,
            {
                "fundamentals": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(fundamentals_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "quality_score": 0.82,
                            "growth_score": 0.74,
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-fundamentals-provider token leak candidate"],
                    }
                ]
            },
        ),
        "PORTFOLIO_SENTIMENT_PROVIDER": "json_file",
        "PORTFOLIO_SENTIMENT_JSON_PATH": _write_json(
            sentiment_path,
            {
                "sentiment": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(sentiment_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "news_score": 0.71,
                            "contradiction_score": 0.18,
                            "secret_score": "should_not_persist",
                        },
                        "notes": ["private-sentiment-provider token leak candidate"],
                    }
                ]
            },
        ),
        "PORTFOLIO_VOLATILITY_PROVIDER": "json_file",
        "PORTFOLIO_VOLATILITY_JSON_PATH": _write_json(
            volatility_path,
            {
                "volatility": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(volatility_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "india_vix": 13.8,
                            "risk_multiplier": 0.82,
                            "credential_hint": "should_not_persist",
                        },
                        "notes": ["private-volatility-provider token leak candidate"],
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
                            "event_risk_score": 0.22,
                            "private_key_hint": "should_not_persist",
                        },
                        "notes": ["private-macro-provider token leak candidate"],
                    }
                ]
            },
        ),
    }


def test_provider_refresh_imports_configured_contexts_to_structured_store(
    tmp_path,
) -> None:
    env = _configured_context_env(tmp_path)
    store = SQLiteProviderDataStore(env[MARKET_DATA_DB_ENV])

    jobs = [
        refresh_provider_import_profile_metadata(provider_id, env=env)
        for provider_id in [
            "configured_universe",
            "configured_fundamentals",
            "configured_sentiment",
            "configured_volatility",
            "configured_macro",
        ]
    ]

    universe = store.get_universe_members(
        "configured_growth",
        provider_id="configured_universe",
    )
    fundamentals = store.get_fundamentals_snapshot(
        "DEMODATA",
        provider_id="configured_fundamentals",
    )
    sentiment = store.get_sentiment_snapshot(
        "DEMODATA",
        provider_id="configured_sentiment",
    )
    volatility = store.get_volatility_snapshot(
        "DEMODATA",
        provider_id="configured_volatility",
    )
    macro = store.get_macro_snapshot("DEMODATA", provider_id="configured_macro")

    assert [job.status for job in jobs] == ["completed"] * 5
    assert [job.progress_state for job in jobs] == ["imported"] * 5
    assert [job.imported_count for job in jobs] == [1, 1, 1, 1, 1]
    assert [job.skipped_count for job in jobs] == [0, 0, 0, 0, 0]
    assert jobs[0].target_store == "provider_universe_members"
    assert jobs[1].target_store == "provider_factor_snapshots"
    assert jobs[-1].audit_event["event_type"] == "provider_import_executed"

    assert universe.symbols == ["DEMODATA", "SLOWDATA"]
    assert fundamentals.metrics["quality_score"] == 0.82
    assert sentiment.metrics["news_score"] == 0.71
    assert volatility.metrics["risk_multiplier"] == 0.82
    assert macro.metrics["market_regime_score"] == 0.72

    combined = (
        f"{[job.to_dict() for job in jobs]} "
        f"{universe.to_dict()} {fundamentals.to_dict()} "
        f"{sentiment.to_dict()} {volatility.to_dict()} {macro.to_dict()}"
    ).lower()
    assert str(tmp_path).lower() not in combined
    assert "private-universe-provider" not in combined
    assert "private-fundamentals-provider" not in combined
    assert "private-sentiment-provider" not in combined
    assert "private-volatility-provider" not in combined
    assert "private-macro-provider" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined
    assert "credential" not in combined
    assert "private_key" not in combined
