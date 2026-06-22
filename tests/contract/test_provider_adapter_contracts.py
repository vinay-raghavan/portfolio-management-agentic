from portfolio_mcp.tools import (
    get_data_provider_health,
    get_market_data_snapshot,
    get_universe_members,
    list_data_providers,
    run_screener,
)


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
