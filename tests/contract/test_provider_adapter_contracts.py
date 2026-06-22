import json

from portfolio_domain.providers import build_data_provider_registry
from portfolio_mcp.tools import (
    get_data_provider_health,
    get_market_data_snapshot,
    get_universe_members,
    list_market_data_snapshots,
    list_data_providers,
    run_screener,
)


def _write_configured_snapshot(tmp_path) -> str:
    json_path = tmp_path / "market-snapshots.json"
    json_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "symbol": "DEMODATA",
                        "as_of": "2026-06-22",
                        "bars": [
                            {
                                "date": "2026-06-18",
                                "open": 101.2,
                                "high": 105.4,
                                "low": 100.9,
                                "close": 104.8,
                                "volume": 120000,
                            },
                            {
                                "date": "2026-06-19",
                                "open": 105.0,
                                "high": 108.1,
                                "low": 103.7,
                                "close": 107.4,
                                "volume": 142000,
                            },
                            {
                                "date": "2026-06-22",
                                "open": 108.0,
                                "high": 111.3,
                                "low": 107.2,
                                "close": 110.6,
                                "volume": 188000,
                            },
                        ],
                        "latest_close": 110.6,
                        "metrics": {
                            "atr_pct": 2.6,
                            "median_turnover_cr": 7.4,
                            "roc20_pct": 5.9,
                            "rsi14": 58.2,
                        },
                        "notes": ["Configured fixture-like snapshot for tests."],
                    }
                ]
            }
        )
    )
    return str(json_path)


def test_data_provider_catalog_defaults_to_fixture_providers() -> None:
    result = list_data_providers()

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    providers = {provider["provider_id"]: provider for provider in result["providers"]}

    assert providers["fixture_market_data"]["status"] == "available"
    assert providers["fixture_market_data"]["configured"] is True
    assert providers["fixture_universe"]["status"] == "available"
    assert providers["configured_market_data"]["status"] == "not_configured"
    assert providers["configured_market_data"]["configured"] is False
    assert "PORTFOLIO_MARKET_DATA_PROVIDER" in providers["configured_market_data"]["required_env"]
    assert "PORTFOLIO_MARKET_DATA_JSON_PATH" in providers["configured_market_data"]["required_env"]
    assert "api_key" not in str(result).lower()
    assert "token" not in str(result).lower()


def test_data_provider_health_reports_not_configured_without_credentials() -> None:
    result = get_data_provider_health()

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    health = {item["provider_id"]: item for item in result["health"]}

    assert health["fixture_market_data"]["status"] == "available"
    assert health["configured_fundamentals"]["status"] == "not_configured"
    assert "missing optional configuration" in health["configured_fundamentals"]["message"].lower()
    assert "secret" not in str(result).lower()


def test_market_data_snapshot_uses_fixture_provider_without_network() -> None:
    result = get_market_data_snapshot("TATAMOTORS")

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    snapshot = result["snapshot"]

    assert snapshot["provider_id"] == "fixture_market_data"
    assert snapshot["source"] == "offline_fixture"
    assert snapshot["symbol"] == "TATAMOTORS"
    assert snapshot["latest_close"] > 0
    assert len(snapshot["bars"]) >= 3
    assert snapshot["metrics"]["atr_pct"] > 0


def test_configured_json_market_data_provider_preserves_snapshot_shape(tmp_path) -> None:
    json_path = _write_configured_snapshot(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
            "PORTFOLIO_MARKET_DATA_JSON_PATH": json_path,
        }
    )

    descriptor = registry.market_data.descriptor().to_dict()
    health = registry.market_data.health().to_dict()
    snapshot = registry.market_data.get_snapshot("demodata").to_dict()

    assert descriptor["provider_id"] == "configured_market_data"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert snapshot["provider_id"] == "configured_market_data"
    assert snapshot["source"] == "configured_json_file"
    assert snapshot["symbol"] == "DEMODATA"
    assert snapshot["latest_close"] == 110.6
    assert snapshot["bars"][-1]["close"] == 110.6
    assert registry.providers_used()["market_data"] == "configured_market_data"

    combined = f"{descriptor} {health} {snapshot}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_market_data_tool_caches_configured_json_snapshot(
    monkeypatch,
    tmp_path,
) -> None:
    json_path = _write_configured_snapshot(tmp_path)
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", json_path)

    result = get_market_data_snapshot("DEMODATA")
    cached = list_market_data_snapshots("DEMODATA", 5)

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["snapshot"]["provider_id"] == "configured_market_data"
    assert result["snapshot"]["source"] == "configured_json_file"
    assert cached["snapshots"][0]["symbol"] == "DEMODATA"
    assert cached["snapshots"][0]["latest_close"] == 110.6

    combined = f"{result} {cached}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_universe_members_come_through_provider_abstraction() -> None:
    result = get_universe_members("fixture_nifty50")

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    universe = result["universe"]

    assert universe["provider_id"] == "fixture_universe"
    assert universe["universe_id"] == "fixture_nifty50"
    assert "TATAMOTORS" in universe["symbols"]


def test_screener_records_provider_inputs() -> None:
    result = run_screener("fixture_nifty50", "momentum", 3)
    run = result["screener_run"]

    assert run["run_summary"]["providers_used"] == {
        "market_data": "fixture_market_data",
        "universe": "fixture_universe",
        "fundamentals": "fixture_fundamentals",
        "sentiment": "fixture_sentiment",
        "volatility": "fixture_volatility",
        "macro": "fixture_macro",
    }
