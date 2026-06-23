from __future__ import annotations

import json
from pathlib import Path

from portfolio_mcp.tools import (
    get_recommendation_explanation,
    run_provider_refresh_schedule,
    run_screener,
)


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload))
    return str(path)


def _configured_readiness_env(monkeypatch, tmp_path) -> Path:
    metadata_db = tmp_path / "provider-config.db"
    market_db = tmp_path / "market-data.db"
    market_path = tmp_path / "private-market-readiness.json"
    universe_path = tmp_path / "private-universe-readiness.json"
    sentiment_path = tmp_path / "private-sentiment-readiness.json"
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(market_db))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv(
        "PORTFOLIO_MARKET_DATA_JSON_PATH",
        _write_json(
            market_path,
            {
                "snapshots": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(market_path),
                        "as_of": "2026-06-22",
                        "bars": [
                            {
                                "date": "2026-06-18",
                                "open": 100.0,
                                "high": 102.0,
                                "low": 98.0,
                                "close": 100.5,
                                "volume": 150000,
                            },
                            {
                                "date": "2026-06-19",
                                "open": 101.0,
                                "high": 104.0,
                                "low": 100.0,
                                "close": 103.2,
                                "volume": 180000,
                            },
                            {
                                "date": "2026-06-22",
                                "open": 104.0,
                                "high": 108.5,
                                "low": 103.4,
                                "close": 108.1,
                                "volume": 220000,
                            },
                        ],
                        "metrics": {
                            "atr_pct": 2.4,
                            "median_turnover_cr": 4.8,
                            "roc20_pct": 7.2,
                            "rsi14": 62.0,
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-market-readiness token leak candidate"],
                    }
                ]
            },
        ),
    )
    monkeypatch.setenv("PORTFOLIO_UNIVERSE_PROVIDER", "json_file")
    monkeypatch.setenv(
        "PORTFOLIO_UNIVERSE_JSON_PATH",
        _write_json(
            universe_path,
            {
                "universes": [
                    {
                        "universe_id": "configured_growth",
                        "name": "Configured Growth",
                        "source": str(universe_path),
                        "as_of": "2026-06-22",
                        "symbols": ["DEMODATA"],
                        "notes": ["private-universe-readiness token leak candidate"],
                    }
                ]
            },
        ),
    )
    monkeypatch.setenv("PORTFOLIO_SENTIMENT_PROVIDER", "json_file")
    monkeypatch.setenv(
        "PORTFOLIO_SENTIMENT_JSON_PATH",
        _write_json(sentiment_path, {"sentiment": []}),
    )
    return tmp_path


def test_provider_refresh_readiness_is_disclosed_in_screener_and_recommendation(
    monkeypatch,
    tmp_path,
) -> None:
    private_root = _configured_readiness_env(monkeypatch, tmp_path)
    schedule = run_provider_refresh_schedule()

    screener = run_screener("configured_growth", "momentum", 5)
    candidate = screener["screener_run"]["candidates"][0]
    component_names = {item["name"] for item in candidate["score_components"]}
    recommendation = get_recommendation_explanation(
        "DEMODATA",
        "breakout-continuation",
    )["recommendation"]

    assert schedule["status"] == "needs_attention"
    assert screener["policy"]["tier"] == "read_only"
    assert screener["screener_run"]["run_summary"]["provider_refresh_readiness"][
        "needs_attention"
    ] >= 1
    assert "provider_readiness" in component_names
    assert "configured_sentiment_refresh_backoff" in candidate["missing_data"]
    assert any(
        "configured_sentiment" in item and "backoff" in item.lower()
        for item in candidate["counterevidence"]
    )

    assert recommendation["mode"] == "analysis_only"
    assert "provider_readiness" in recommendation["factor_summary"]
    assert "configured_sentiment_refresh_backoff" in recommendation["missing_data"]
    assert any(
        "configured_sentiment" in item and "backoff" in item.lower()
        for item in recommendation["counterevidence"]
    )
    assert recommendation["history_refs"]["paper_order_ids"] == []
    assert "create_paper_order_proposal" not in recommendation["next_allowed_actions"]

    combined = f"{screener} {recommendation}".lower()
    assert str(private_root).lower() not in combined
    assert "private-market-readiness" not in combined
    assert "private-universe-readiness" not in combined
    assert "private-sentiment-readiness" not in combined
    assert "api_key" not in combined
    assert "api_token" not in combined
    assert "should_not_persist" not in combined
    assert "token leak candidate" not in combined
