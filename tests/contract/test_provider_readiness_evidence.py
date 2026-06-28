from __future__ import annotations

import json
from pathlib import Path

from portfolio_mcp.tools import (
    create_backtest_request,
    create_paper_order_proposal,
    draft_paper_strategy,
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


def test_provider_import_reconciliation_gates_configured_paper_readiness(
    monkeypatch,
    tmp_path,
) -> None:
    private_root = _configured_readiness_env(monkeypatch, tmp_path)
    run_provider_refresh_schedule()

    market_path = tmp_path / "private-market-readiness.json"
    market_payload = json.loads(market_path.read_text())
    market_payload["snapshots"].append(
        {
            "symbol": "NEWDATA",
            "source": str(market_path),
            "as_of": "2026-06-22",
            "bars": [
                {
                    "date": "2026-06-18",
                    "open": 200.0,
                    "high": 204.0,
                    "low": 198.0,
                    "close": 202.0,
                    "volume": 200000,
                },
                {
                    "date": "2026-06-19",
                    "open": 203.0,
                    "high": 206.0,
                    "low": 201.0,
                    "close": 205.0,
                    "volume": 230000,
                },
                {
                    "date": "2026-06-22",
                    "open": 206.0,
                    "high": 210.0,
                    "low": 204.0,
                    "close": 209.0,
                    "volume": 260000,
                },
            ],
            "metrics": {
                "atr_pct": 2.9,
                "median_turnover_cr": 5.1,
                "roc20_pct": 8.1,
                "rsi14": 61.0,
                "api_token": "should_not_persist",
            },
            "notes": ["private-market-readiness token leak candidate"],
        }
    )
    market_path.write_text(json.dumps(market_payload))

    draft_paper_strategy(
        "DEMODATA",
        "Configured strategy should remain gated while imports are out of sync.",
    )
    create_backtest_request(
        "DEMODATA",
        "breakout-continuation",
        "2026-01-02",
        "2026-06-22",
    )

    screener = run_screener("configured_growth", "momentum", 5)
    candidate = screener["screener_run"]["candidates"][0]
    recommendation = get_recommendation_explanation(
        "DEMODATA",
        "breakout-continuation",
    )["recommendation"]
    blocked_without_history = get_recommendation_explanation(
        "NEWDATA",
        "breakout-continuation",
    )["recommendation"]

    reconciliation_summary = screener["screener_run"]["run_summary"][
        "provider_import_reconciliation"
    ]
    assert reconciliation_summary["source_changed"] == 1
    assert (
        reconciliation_summary["provider_statuses"]["configured_market_data"]
        == "source_changed"
    )
    assert "configured_market_data_import_source_changed" in candidate["missing_data"]
    assert "provider_import_reconciliation" in {
        item["name"] for item in candidate["score_components"]
    }
    assert any(
        gate["name"] == "provider_import_reconciliation"
        and gate["status"] == "review"
        for gate in candidate["gates"]
    )
    assert "draft_paper_strategy" not in candidate["next_allowed_actions"]

    assert recommendation["stance"] == "blocked"
    assert "provider_import_reconciliation" in recommendation["factor_summary"]
    assert (
        "configured_market_data_import_source_changed"
        in recommendation["missing_data"]
    )
    assert any(
        gate["name"] == "provider_import_reconciliation"
        and gate["status"] == "fail"
        for gate in recommendation["risk_gates"]
    )
    assert "create_paper_order_proposal" not in recommendation["next_allowed_actions"]
    assert blocked_without_history["stance"] == "blocked"
    assert "draft_paper_strategy" not in blocked_without_history["next_allowed_actions"]
    assert (
        "create_backtest_request"
        not in blocked_without_history["next_allowed_actions"]
    )
    blocked_order = create_paper_order_proposal(
        strategy_id="paper-demodata-source-changed",
        symbol="DEMODATA",
        side="buy",
        quantity=2,
        order_type="market",
    )
    assert blocked_order["status"] == "blocked"
    assert blocked_order["readiness_preflight"]["status"] == "blocked"
    assert blocked_order["readiness_preflight"]["provider_import_reconciliation"][
        "status"
    ] == "fail"
    assert "paper_order" not in blocked_order

    combined = (
        f"{screener} {recommendation} {blocked_without_history} {blocked_order}"
    ).lower()
    assert str(private_root).lower() not in combined
    assert "private-market-readiness" not in combined
    assert "api_key" not in combined
    assert "api_token" not in combined
    assert "should_not_persist" not in combined
    assert "token leak candidate" not in combined
