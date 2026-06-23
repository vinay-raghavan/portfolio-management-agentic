import json

from portfolio_domain.providers import (
    build_data_provider_registry,
    validate_configured_provider_imports,
)
from portfolio_mcp.tools import (
    explain_factor_stack,
    get_data_provider_health,
    get_market_data_snapshot,
    get_universe_members,
    list_market_data_snapshots,
    list_data_providers,
    run_screener,
    validate_data_provider_imports,
)


def _snapshot_payload(
    symbol: str,
    latest_close: float,
    volume: int,
    metrics: dict[str, float],
) -> dict:
    previous_close = round(latest_close * 0.96, 2)
    middle_close = round(latest_close * 0.985, 2)
    return {
        "symbol": symbol,
        "as_of": "2026-06-22",
        "bars": [
            {
                "date": "2026-06-18",
                "open": round(previous_close * 0.97, 2),
                "high": round(previous_close * 1.01, 2),
                "low": round(previous_close * 0.96, 2),
                "close": previous_close,
                "volume": volume,
            },
            {
                "date": "2026-06-19",
                "open": round(middle_close * 0.98, 2),
                "high": round(middle_close * 1.01, 2),
                "low": round(middle_close * 0.97, 2),
                "close": middle_close,
                "volume": volume,
            },
            {
                "date": "2026-06-22",
                "open": round(latest_close * 0.98, 2),
                "high": round(latest_close * 1.01, 2),
                "low": round(latest_close * 0.97, 2),
                "close": latest_close,
                "volume": volume,
            },
        ],
        "latest_close": latest_close,
        "metrics": metrics,
        "notes": ["Configured fixture-like snapshot for tests."],
    }


def _write_configured_snapshot(tmp_path) -> str:
    json_path = tmp_path / "market-snapshots.json"
    json_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    _snapshot_payload(
                        "DEMODATA",
                        110.6,
                        188000,
                        {
                            "atr_pct": 2.6,
                            "median_turnover_cr": 7.4,
                            "roc20_pct": 5.9,
                            "rsi14": 58.2,
                        },
                    )
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_universe(tmp_path) -> str:
    json_path = tmp_path / "universes.json"
    json_path.write_text(
        json.dumps(
            {
                "universes": [
                    {
                        "universe_id": "configured_growth",
                        "name": "Configured Growth Watchlist",
                        "source": "configured_json_file",
                        "as_of": "2026-06-22",
                        "symbols": ["DEMODATA", "SLOWDATA", "THINLY"],
                        "notes": ["Local configured watchlist for tests."],
                    }
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_screener_snapshots(tmp_path) -> str:
    json_path = tmp_path / "configured-screener-snapshots.json"
    json_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    _snapshot_payload(
                        "DEMODATA",
                        110.6,
                        188000,
                        {
                            "atr_pct": 2.6,
                            "median_turnover_cr": 7.4,
                            "roc20_pct": 8.2,
                            "rsi14": 61.4,
                        },
                    ),
                    _snapshot_payload(
                        "SLOWDATA",
                        84.2,
                        155000,
                        {
                            "atr_pct": 1.9,
                            "median_turnover_cr": 4.8,
                            "roc20_pct": 3.4,
                            "rsi14": 54.1,
                        },
                    ),
                    _snapshot_payload(
                        "THINLY",
                        42.0,
                        900,
                        {
                            "atr_pct": 7.5,
                            "median_turnover_cr": 0.03,
                            "roc20_pct": 12.0,
                            "rsi14": 66.0,
                        },
                    ),
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_fundamentals(tmp_path) -> str:
    json_path = tmp_path / "fundamentals.json"
    json_path.write_text(
        json.dumps(
            {
                "fundamentals": [
                    {
                        "symbol": "DEMODATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "quality_score": 0.82,
                            "value_score": 0.58,
                            "growth_score": 0.74,
                            "earnings_revision_score": 0.66,
                            "leverage_score": 0.77,
                        },
                        "notes": ["Configured fundamentals for tests."],
                    },
                    {
                        "symbol": "SLOWDATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "quality_score": 0.48,
                            "value_score": 0.52,
                            "growth_score": 0.44,
                            "earnings_revision_score": 0.41,
                            "leverage_score": 0.55,
                        },
                        "notes": ["Weaker configured fundamentals for tests."],
                    },
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_sentiment(tmp_path) -> str:
    json_path = tmp_path / "sentiment.json"
    json_path.write_text(
        json.dumps(
            {
                "sentiment": [
                    {
                        "symbol": "DEMODATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "news_score": 0.71,
                            "investor_score": 0.63,
                            "contradiction_score": 0.18,
                        },
                        "notes": ["Configured sentiment for tests."],
                    },
                    {
                        "symbol": "SLOWDATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "news_score": 0.42,
                            "investor_score": 0.49,
                            "contradiction_score": 0.44,
                        },
                        "notes": ["Mixed configured sentiment for tests."],
                    },
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_volatility(tmp_path) -> str:
    json_path = tmp_path / "volatility.json"
    json_path.write_text(
        json.dumps(
            {
                "volatility": [
                    {
                        "symbol": "DEMODATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "india_vix": 13.8,
                            "vix_change_pct": -4.2,
                            "regime_score": 0.74,
                            "risk_multiplier": 0.82,
                        },
                        "notes": ["Configured volatility for tests."],
                    },
                    {
                        "symbol": "SLOWDATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "india_vix": 19.6,
                            "vix_change_pct": 7.4,
                            "regime_score": 0.38,
                            "risk_multiplier": 0.52,
                        },
                        "notes": ["Elevated volatility context for tests."],
                    },
                ]
            }
        )
    )
    return str(json_path)


def _write_configured_macro(tmp_path) -> str:
    json_path = tmp_path / "macro.json"
    json_path.write_text(
        json.dumps(
            {
                "macro": [
                    {
                        "symbol": "DEMODATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "market_regime_score": 0.72,
                            "breadth_score": 0.68,
                            "rate_pressure_score": 0.61,
                            "event_risk_score": 0.22,
                            "liquidity_condition_score": 0.66,
                        },
                        "notes": ["Configured macro context for tests."],
                    },
                    {
                        "symbol": "SLOWDATA",
                        "as_of": "2026-06-22",
                        "metrics": {
                            "market_regime_score": 0.46,
                            "breadth_score": 0.49,
                            "rate_pressure_score": 0.38,
                            "event_risk_score": 0.58,
                            "liquidity_condition_score": 0.44,
                        },
                        "notes": ["Mixed configured macro context for tests."],
                    },
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
    assert "PORTFOLIO_UNIVERSE_PROVIDER" in providers["configured_universe"]["required_env"]
    assert "PORTFOLIO_UNIVERSE_JSON_PATH" in providers["configured_universe"]["required_env"]
    assert "PORTFOLIO_FUNDAMENTALS_PROVIDER" in providers["configured_fundamentals"]["required_env"]
    assert "PORTFOLIO_FUNDAMENTALS_JSON_PATH" in providers["configured_fundamentals"]["required_env"]
    assert "PORTFOLIO_SENTIMENT_PROVIDER" in providers["configured_sentiment"]["required_env"]
    assert "PORTFOLIO_SENTIMENT_JSON_PATH" in providers["configured_sentiment"]["required_env"]
    assert "PORTFOLIO_VOLATILITY_PROVIDER" in providers["configured_volatility"]["required_env"]
    assert "PORTFOLIO_VOLATILITY_JSON_PATH" in providers["configured_volatility"]["required_env"]
    assert "PORTFOLIO_MACRO_PROVIDER" in providers["configured_macro"]["required_env"]
    assert "PORTFOLIO_MACRO_JSON_PATH" in providers["configured_macro"]["required_env"]
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


def test_configured_json_universe_provider_preserves_universe_shape(tmp_path) -> None:
    json_path = _write_configured_universe(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_UNIVERSE_PROVIDER": "json_file",
            "PORTFOLIO_UNIVERSE_JSON_PATH": json_path,
        }
    )

    descriptor = registry.universe.descriptor().to_dict()
    health = registry.universe.health().to_dict()
    universes = [universe.to_dict() for universe in registry.universe.list_universes()]
    members = registry.universe.get_members("configured_growth").to_dict()

    assert descriptor["provider_id"] == "configured_universe"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert universes[0]["universe_id"] == "configured_growth"
    assert members["provider_id"] == "configured_universe"
    assert members["symbols"] == ["DEMODATA", "SLOWDATA", "THINLY"]
    assert registry.providers_used()["universe"] == "configured_universe"

    combined = f"{descriptor} {health} {universes} {members}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_configured_json_fundamentals_provider_preserves_metrics_shape(tmp_path) -> None:
    json_path = _write_configured_fundamentals(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_FUNDAMENTALS_PROVIDER": "json_file",
            "PORTFOLIO_FUNDAMENTALS_JSON_PATH": json_path,
        }
    )

    descriptor = registry.fundamentals.descriptor().to_dict()
    health = registry.fundamentals.health().to_dict()
    fundamentals = registry.fundamentals.get_metrics("demodata").to_dict()

    assert descriptor["provider_id"] == "configured_fundamentals"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert fundamentals["provider_id"] == "configured_fundamentals"
    assert fundamentals["source"] == "configured_json_file"
    assert fundamentals["symbol"] == "DEMODATA"
    assert fundamentals["metrics"]["quality_score"] == 0.82
    assert fundamentals["metrics"]["growth_score"] == 0.74
    assert registry.providers_used()["fundamentals"] == "configured_fundamentals"

    combined = f"{descriptor} {health} {fundamentals}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_configured_json_sentiment_provider_preserves_metrics_shape(tmp_path) -> None:
    json_path = _write_configured_sentiment(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_SENTIMENT_PROVIDER": "json_file",
            "PORTFOLIO_SENTIMENT_JSON_PATH": json_path,
        }
    )

    descriptor = registry.sentiment.descriptor().to_dict()
    health = registry.sentiment.health().to_dict()
    sentiment = registry.sentiment.get_context("demodata").to_dict()

    assert descriptor["provider_id"] == "configured_sentiment"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert sentiment["provider_id"] == "configured_sentiment"
    assert sentiment["source"] == "configured_json_file"
    assert sentiment["symbol"] == "DEMODATA"
    assert sentiment["metrics"]["news_score"] == 0.71
    assert sentiment["metrics"]["contradiction_score"] == 0.18
    assert registry.providers_used()["sentiment"] == "configured_sentiment"

    combined = f"{descriptor} {health} {sentiment}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_configured_json_volatility_provider_preserves_metrics_shape(tmp_path) -> None:
    json_path = _write_configured_volatility(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_VOLATILITY_PROVIDER": "json_file",
            "PORTFOLIO_VOLATILITY_JSON_PATH": json_path,
        }
    )

    descriptor = registry.volatility.descriptor().to_dict()
    health = registry.volatility.health().to_dict()
    volatility = registry.volatility.get_context("demodata").to_dict()

    assert descriptor["provider_id"] == "configured_volatility"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert volatility["provider_id"] == "configured_volatility"
    assert volatility["source"] == "configured_json_file"
    assert volatility["symbol"] == "DEMODATA"
    assert volatility["metrics"]["india_vix"] == 13.8
    assert volatility["metrics"]["risk_multiplier"] == 0.82
    assert registry.providers_used()["volatility"] == "configured_volatility"

    combined = f"{descriptor} {health} {volatility}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_configured_json_macro_provider_preserves_metrics_shape(tmp_path) -> None:
    json_path = _write_configured_macro(tmp_path)
    registry = build_data_provider_registry(
        {
            "PORTFOLIO_MACRO_PROVIDER": "json_file",
            "PORTFOLIO_MACRO_JSON_PATH": json_path,
        }
    )

    descriptor = registry.macro.descriptor().to_dict()
    health = registry.macro.health().to_dict()
    macro = registry.macro.get_context("demodata").to_dict()

    assert descriptor["provider_id"] == "configured_macro"
    assert descriptor["status"] == "available"
    assert descriptor["configured"] is True
    assert health["status"] == "available"
    assert macro["provider_id"] == "configured_macro"
    assert macro["source"] == "configured_json_file"
    assert macro["symbol"] == "DEMODATA"
    assert macro["metrics"]["market_regime_score"] == 0.72
    assert macro["metrics"]["event_risk_score"] == 0.22
    assert registry.providers_used()["macro"] == "configured_macro"

    combined = f"{descriptor} {health} {macro}".lower()
    assert str(json_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_configured_provider_import_validation_reports_errors_without_path_leaks(
    tmp_path,
) -> None:
    market_path = _write_configured_snapshot(tmp_path)
    bad_fundamentals_path = tmp_path / "bad-fundamentals.json"
    bad_fundamentals_path.write_text("{not-json")
    missing_volatility_path = tmp_path / "missing-volatility.json"

    validations = [
        validation.to_dict()
        for validation in validate_configured_provider_imports(
            {
                "PORTFOLIO_MARKET_DATA_PROVIDER": "json_file",
                "PORTFOLIO_MARKET_DATA_JSON_PATH": market_path,
                "PORTFOLIO_FUNDAMENTALS_PROVIDER": "json_file",
                "PORTFOLIO_FUNDAMENTALS_JSON_PATH": str(bad_fundamentals_path),
                "PORTFOLIO_SENTIMENT_PROVIDER": "csv_file",
                "PORTFOLIO_SENTIMENT_JSON_PATH": "private-secret-sentiment.csv",
                "PORTFOLIO_VOLATILITY_PROVIDER": "json_file",
                "PORTFOLIO_VOLATILITY_JSON_PATH": str(missing_volatility_path),
                "PORTFOLIO_MACRO_PROVIDER": "json_file",
            }
        )
    ]
    by_provider = {item["provider_id"]: item for item in validations}

    assert by_provider["configured_market_data"]["status"] == "valid"
    assert by_provider["configured_market_data"]["payload_count"] == 1
    assert by_provider["configured_market_data"]["sample_identifiers"] == ["DEMODATA"]
    assert by_provider["configured_universe"]["status"] == "not_configured"
    assert by_provider["configured_fundamentals"]["status"] == "error"
    assert "not valid JSON" in by_provider["configured_fundamentals"]["message"]
    assert by_provider["configured_sentiment"]["status"] == "unsupported_provider"
    assert by_provider["configured_volatility"]["status"] == "error"
    assert by_provider["configured_macro"]["status"] == "missing_path"
    assert by_provider["configured_macro"]["missing_env"] == ["PORTFOLIO_MACRO_JSON_PATH"]

    combined = f"{validations}".lower()
    assert str(tmp_path).lower() not in combined
    assert "bad-fundamentals" not in combined
    assert "missing-volatility" not in combined
    assert "private-secret-sentiment" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_validate_data_provider_imports_tool_is_read_only_and_summarized(
    monkeypatch,
    tmp_path,
) -> None:
    bad_macro_path = tmp_path / "bad-macro.json"
    bad_macro_path.write_text("{bad")
    monkeypatch.setenv("PORTFOLIO_MACRO_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MACRO_JSON_PATH", str(bad_macro_path))

    result = validate_data_provider_imports()
    validations = {item["provider_id"]: item for item in result["validations"]}

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["summary"]["total"] == 6
    assert result["summary"]["needs_attention"] == 1
    assert validations["configured_macro"]["status"] == "error"
    assert "not valid JSON" in validations["configured_macro"]["message"]

    combined = f"{result}".lower()
    assert str(tmp_path).lower() not in combined
    assert "bad-macro" not in combined
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


def test_configured_json_universe_and_market_data_run_ranked_screener(
    monkeypatch,
    tmp_path,
) -> None:
    market_path = _write_configured_screener_snapshots(tmp_path)
    universe_path = _write_configured_universe(tmp_path)
    fundamentals_path = _write_configured_fundamentals(tmp_path)
    sentiment_path = _write_configured_sentiment(tmp_path)
    volatility_path = _write_configured_volatility(tmp_path)
    macro_path = _write_configured_macro(tmp_path)
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", market_path)
    monkeypatch.setenv("PORTFOLIO_UNIVERSE_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_UNIVERSE_JSON_PATH", universe_path)
    monkeypatch.setenv("PORTFOLIO_FUNDAMENTALS_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_FUNDAMENTALS_JSON_PATH", fundamentals_path)
    monkeypatch.setenv("PORTFOLIO_SENTIMENT_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_SENTIMENT_JSON_PATH", sentiment_path)
    monkeypatch.setenv("PORTFOLIO_VOLATILITY_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_VOLATILITY_JSON_PATH", volatility_path)
    monkeypatch.setenv("PORTFOLIO_MACRO_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MACRO_JSON_PATH", macro_path)

    universe = get_universe_members("configured_growth")
    result = run_screener("configured_growth", "momentum", 5)
    explanation = explain_factor_stack("DEMODATA", "breakout-continuation")

    assert universe["status"] == "success"
    assert universe["universe"]["provider_id"] == "configured_universe"
    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    run = result["screener_run"]

    assert run["source"] == "configured_json_file"
    assert run["run_summary"]["providers_used"]["market_data"] == "configured_market_data"
    assert run["run_summary"]["providers_used"]["universe"] == "configured_universe"
    assert run["run_summary"]["providers_used"]["fundamentals"] == "configured_fundamentals"
    assert run["run_summary"]["providers_used"]["sentiment"] == "configured_sentiment"
    assert run["run_summary"]["providers_used"]["volatility"] == "configured_volatility"
    assert run["run_summary"]["providers_used"]["macro"] == "configured_macro"
    assert run["run_summary"]["total_screened"] == 3
    assert run["run_summary"]["candidate_count"] == 2
    assert run["run_summary"]["rejected_count"] == 1
    assert run["rejected_symbols"] == ["THINLY"]
    assert run["candidates"][0]["symbol"] == "DEMODATA"
    assert run["candidates"][0]["rank"] == 1
    assert "momentum" in run["candidates"][0]["passed_screeners"]
    assert {component["name"] for component in run["candidates"][0]["score_components"]} >= {
        "technical",
        "fundamental",
        "sentiment",
        "volatility",
        "macro",
        "liquidity",
        "pattern",
    }
    assert "configured_fundamentals" not in run["candidates"][0]["missing_data"]
    assert "configured_sentiment" not in run["candidates"][0]["missing_data"]
    assert "configured_volatility" not in run["candidates"][0]["missing_data"]
    assert "configured_macro" not in run["candidates"][0]["missing_data"]
    assert run["candidates"][0]["next_allowed_actions"] == [
        "explain_evidence",
        "draft_paper_strategy",
    ]
    assert explanation["status"] == "success"
    assert explanation["factor_stack"]["symbol"] == "DEMODATA"
    assert explanation["factor_stack"]["sections"]["technical"]["evidence"]
    assert explanation["factor_stack"]["sections"]["fundamental"]["evidence"]
    assert explanation["factor_stack"]["sections"]["sentiment"]["evidence"]
    assert any(
        "India VIX" in item
        for item in explanation["factor_stack"]["sections"]["volatility"]["evidence"]
    )
    assert any(
        "Market regime" in item
        for item in explanation["factor_stack"]["sections"]["macro"]["evidence"]
    )
    assert (
        explanation["factor_stack"]["sections"]["market_regime"]["evidence"]
        == explanation["factor_stack"]["sections"]["macro"]["evidence"]
    )
    assert "configured_fundamentals" not in explanation["factor_stack"]["missing_data"]
    assert "configured_sentiment" not in explanation["factor_stack"]["missing_data"]
    assert "configured_volatility" not in explanation["factor_stack"]["missing_data"]
    assert "configured_macro" not in explanation["factor_stack"]["missing_data"]

    combined = f"{universe} {result} {explanation}".lower()
    assert str(market_path).lower() not in combined
    assert str(universe_path).lower() not in combined
    assert str(fundamentals_path).lower() not in combined
    assert str(sentiment_path).lower() not in combined
    assert str(volatility_path).lower() not in combined
    assert str(macro_path).lower() not in combined
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
