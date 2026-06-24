import json

from portfolio_domain.market_data_store import SQLiteMarketDataStore
from portfolio_domain.provider_data_store import SQLiteProviderDataStore
from portfolio_mcp.tools import (
    EXPOSED_TOOL_NAMES,
    assert_exposed_tools_are_safe,
    create_pre_market_briefing,
    create_paper_trade_proposal,
    cite_strategy_evidence,
    draft_paper_strategy,
    explain_factor_stack,
    get_data_provider_health,
    get_market_data_snapshot,
    get_pattern_playbook,
    get_broker_trading_token,
    get_portfolio_summary,
    get_provider_refresh_readiness,
    get_research_digest,
    get_universe_members,
    list_data_providers,
    list_provider_import_previews,
    list_provider_source_templates,
    list_provider_source_onboarding,
    list_provider_import_jobs,
    list_provider_profiles,
    list_universes,
    place_live_order,
    run_screener,
    run_momentum_screener,
    search_pattern_library,
    get_signal_summary,
    get_watchlist_snapshot,
    validate_data_provider_imports,
    refresh_provider_import_profile,
    run_provider_refresh_schedule,
)


def test_exposed_tool_catalog_contains_no_forbidden_tools() -> None:
    assert_exposed_tools_are_safe()
    assert "place_live_order" not in EXPOSED_TOOL_NAMES
    assert "get_broker_trading_token" not in EXPOSED_TOOL_NAMES


def test_portfolio_summary_uses_demo_data_only() -> None:
    result = get_portfolio_summary()

    assert result["status"] == "success"
    assert result["portfolio"]["currency"] == "INR"
    assert result["portfolio"]["notes"][0].startswith("Synthetic demo portfolio")


def test_pre_market_briefing_workflow_uses_synthetic_read_only_sections() -> None:
    watchlist = get_watchlist_snapshot()
    signals = get_signal_summary()
    research = get_research_digest()
    briefing = create_pre_market_briefing()

    assert watchlist["status"] == "success"
    assert signals["status"] == "success"
    assert research["status"] == "success"
    assert briefing["status"] == "success"
    assert briefing["briefing"]["mode"] == "read_only"
    assert briefing["briefing"]["source"] == "synthetic_demo"
    assert briefing["briefing"]["portfolio"]["currency"] == "INR"
    assert briefing["briefing"]["watchlist"]["items"]
    assert briefing["briefing"]["signal_summary"]["regime"] == "constructive"
    assert briefing["briefing"]["research_digest"]["notes"]
    assert (
        briefing["briefing"]["risk_review"]["safety_switches"]["live_trading"]
        == "disabled"
    )
    assert all(
        "order" not in action.lower()
        for action in briefing["briefing"]["suggested_review_actions"]
    )


def test_screener_to_strategy_to_pending_paper_proposal() -> None:
    screener = run_momentum_screener(1)
    symbol = screener["candidates"][0]["symbol"]

    draft = draft_paper_strategy(symbol, "Top synthetic momentum candidate")
    proposal = create_paper_trade_proposal(draft["strategy"]["strategy_id"])

    assert draft["strategy"]["mode"] == "paper"
    assert draft["strategy"]["status"] == "draft"
    assert proposal["status"] == "pending_approval"
    assert proposal["proposal"]["mode"] == "paper"


def test_product_data_pattern_foundation_tools_are_read_only() -> None:
    universes = list_universes()
    screener = run_screener("fixture_nifty50", "momentum", 3)
    patterns = search_pattern_library("momentum", "", 2)
    playbook = get_pattern_playbook(patterns["patterns"][0]["pattern_id"])
    evidence = cite_strategy_evidence("TATAMOTORS", "breakout-continuation")
    factor_stack = explain_factor_stack("TATAMOTORS", "breakout-continuation")

    assert universes["policy"]["tier"] == "read_only"
    assert screener["policy"]["tier"] == "read_only"
    assert playbook["policy"]["tier"] == "read_only"
    assert evidence["evidence_pack"]["paper_only_status"] == "analysis_only"
    assert factor_stack["factor_stack"]["paper_only_status"] == "analysis_only"


def test_provider_adapter_tools_are_read_only_and_fixture_backed() -> None:
    providers = list_data_providers()
    health = get_data_provider_health()
    import_validation = validate_data_provider_imports()
    profiles = list_provider_profiles()
    jobs = list_provider_import_jobs(5)
    snapshot = get_market_data_snapshot("TATAMOTORS")
    universe = get_universe_members("fixture_nifty50")

    assert providers["policy"]["tier"] == "read_only"
    assert health["policy"]["tier"] == "read_only"
    assert import_validation["policy"]["tier"] == "read_only"
    assert profiles["policy"]["tier"] == "read_only"
    assert jobs["policy"]["tier"] == "read_only"
    assert import_validation["summary"]["total"] == 6
    assert snapshot["snapshot"]["source"] == "offline_fixture"
    assert universe["universe"]["provider_id"] == "fixture_universe"


def test_provider_source_templates_are_read_only_and_sanitized() -> None:
    result = list_provider_source_templates()
    templates = {
        template["provider_id"]: template
        for template in result["templates"]
    }

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["summary"]["total"] == 6
    assert set(templates) == {
        "configured_market_data",
        "configured_universe",
        "configured_fundamentals",
        "configured_sentiment",
        "configured_volatility",
        "configured_macro",
    }
    assert templates["configured_market_data"]["template_json"]["snapshots"][0][
        "bars"
    ][0]["date"]
    assert templates["configured_universe"]["template_json"]["universes"][0][
        "symbols"
    ]
    assert "snapshots" in templates["configured_market_data"]["accepted_wrappers"]
    assert "json_file" in result["provider_mode_options"]

    combined = f"{result}".lower()
    assert "place_live_order" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "/users/" not in combined


def test_provider_source_onboarding_links_guidance_and_refresh_path_safely() -> None:
    result = list_provider_source_onboarding()
    cards = {
        card["provider_id"]: card
        for card in result["onboarding_cards"]
    }
    market = cards["configured_market_data"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["summary"]["total"] == 6
    assert result["summary"]["needs_setup"] == 0
    assert set(cards) == {
        "configured_market_data",
        "configured_universe",
        "configured_fundamentals",
        "configured_sentiment",
        "configured_volatility",
        "configured_macro",
    }
    assert market["validation"]["status"] == "not_configured"
    assert market["refresh_readiness"]["status"] == "not_configured"
    assert market["setup_state"] == "optional_fixture_mode"
    assert market["recommended_next_step"] == "configure_provider_env"
    assert market["template"]["accepted_wrappers"][0] == "list"
    assert market["template"]["template_json"]["snapshots"][0]["bars"][0]["date"]
    assert [
        action["tool"]
        for action in market["safe_actions"]
    ] == [
        "list_provider_source_templates",
        "validate_data_provider_imports",
        "refresh_provider_import_profile",
    ]
    assert {action["tier"] for action in market["safe_actions"]} <= {
        "read_only",
        "draft_only",
    }

    combined = f"{result}".lower()
    assert "place_live_order" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined
    assert "/users/" not in combined


def test_provider_import_previews_dry_run_without_writing_or_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    metadata_db = tmp_path / "provider-config.db"
    market_db = tmp_path / "market-data.db"
    private_path = tmp_path / "private-market-export.json"
    private_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "symbol": "SAMPLE_EQTY",
                        "source": str(private_path),
                        "as_of": "2026-06-22",
                        "bars": [
                            {
                                "date": "2026-06-22",
                                "open": 100.0,
                                "high": 104.0,
                                "low": 99.0,
                                "close": 103.0,
                                "volume": 123000,
                            }
                        ],
                        "metrics": {
                            "atr_pct": 2.5,
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-market-export token leak candidate"],
                    }
                ]
            }
        )
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(market_db))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(private_path))

    result = list_provider_import_previews()
    previews = {
        preview["provider_id"]: preview
        for preview in result["previews"]
    }
    market = previews["configured_market_data"]

    assert result["status"] == "success"
    assert result["policy"]["tier"] == "read_only"
    assert result["summary"]["total"] == 6
    assert result["summary"]["configured"] == 1
    assert result["summary"]["would_write"] == 1
    assert result["summary"]["normalized_count"] == 1
    assert market["status"] == "ready"
    assert market["validation_status"] == "valid"
    assert market["target_store"] == "market_data_snapshots"
    assert market["would_write"] is True
    assert market["normalized_count"] == 1
    assert market["skipped_count"] == 0
    assert market["sample_identifiers"] == ["SAMPLE_EQTY"]
    assert market["safe_actions"][0]["tool"] == "refresh_provider_import_profile"
    assert market["safe_actions"][0]["enabled"] is True
    assert not metadata_db.exists()
    assert not market_db.exists()

    combined = f"{result}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-export" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined


def test_provider_import_refresh_is_draft_only_and_path_safe(
    monkeypatch, tmp_path
) -> None:
    metadata_db = tmp_path / "provider-config.db"
    private_path = tmp_path / "private-provider-export.json"
    private_path.write_text("{bad")
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("PORTFOLIO_MACRO_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MACRO_JSON_PATH", str(private_path))

    result = refresh_provider_import_profile("configured_macro")
    jobs = list_provider_import_jobs(5)

    assert result["status"] == "needs_attention"
    assert result["policy"]["tier"] == "draft_only"
    assert result["job"]["validation_status"] == "error"
    assert jobs["import_jobs"][0]["provider_id"] == "configured_macro"

    combined = f"{result} {jobs}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-provider-export" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_provider_import_refresh_imports_valid_market_data_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    metadata_db = tmp_path / "provider-config.db"
    market_db = tmp_path / "market-data.db"
    private_path = tmp_path / "private-market-provider.json"
    private_path.write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(private_path),
                        "as_of": "2026-06-22",
                        "bars": [
                            {
                                "date": "2026-06-22",
                                "open": 101.0,
                                "high": 104.0,
                                "low": 99.0,
                                "close": 103.0,
                                "volume": 123000,
                            }
                        ],
                        "metrics": {
                            "atr_pct": 2.5,
                            "median_turnover_cr": 8.1,
                            "roc20_pct": 7.2,
                            "rsi14": 59.4,
                            "api_token": "should_not_persist",
                        },
                        "notes": ["private-market-provider token leak candidate"],
                    }
                ]
            }
        )
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(market_db))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(private_path))

    result = refresh_provider_import_profile("configured_market_data")
    stored = SQLiteMarketDataStore(market_db).get_market_snapshot(
        "DEMODATA",
        provider_id="configured_market_data",
    )

    assert result["status"] == "completed"
    assert result["policy"]["tier"] == "draft_only"
    assert result["job"]["progress_state"] == "imported"
    assert result["job"]["imported_count"] == 1
    assert result["job"]["target_store"] == "market_data_snapshots"
    assert stored.provider_id == "configured_market_data"
    assert stored.symbol == "DEMODATA"

    combined = f"{result} {stored.to_dict()}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-provider" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_provider_import_refresh_imports_valid_macro_context_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    metadata_db = tmp_path / "provider-config.db"
    market_db = tmp_path / "market-data.db"
    private_path = tmp_path / "private-macro-provider.json"
    private_path.write_text(
        json.dumps(
            {
                "macro": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(private_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "market_regime_score": 0.72,
                            "event_risk_score": 0.22,
                            "private_key_hint": "should_not_persist",
                        },
                        "notes": ["private-macro-provider token leak candidate"],
                    }
                ]
            }
        )
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(market_db))
    monkeypatch.setenv("PORTFOLIO_MACRO_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MACRO_JSON_PATH", str(private_path))

    result = refresh_provider_import_profile("configured_macro")
    stored = SQLiteProviderDataStore(market_db).get_macro_snapshot(
        "DEMODATA",
        provider_id="configured_macro",
    )

    assert result["status"] == "completed"
    assert result["policy"]["tier"] == "draft_only"
    assert result["job"]["progress_state"] == "imported"
    assert result["job"]["imported_count"] == 1
    assert result["job"]["target_store"] == "provider_factor_snapshots"
    assert stored.provider_id == "configured_macro"
    assert stored.symbol == "DEMODATA"
    assert stored.metrics["market_regime_score"] == 0.72

    combined = f"{result} {stored.to_dict()}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-macro-provider" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "private_key" not in combined


def test_provider_refresh_schedule_tool_reports_readiness_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    metadata_db = tmp_path / "provider-config.db"
    market_db = tmp_path / "market-data.db"
    private_path = tmp_path / "private-schedule-macro.json"
    private_path.write_text(
        json.dumps(
            {
                "macro": [
                    {
                        "symbol": "DEMODATA",
                        "source": str(private_path),
                        "as_of": "2026-06-22",
                        "metrics": {
                            "market_regime_score": 0.72,
                            "private_key_hint": "should_not_persist",
                        },
                        "notes": ["private-schedule-macro token leak candidate"],
                    }
                ]
            }
        )
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(metadata_db))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(market_db))
    monkeypatch.setenv("PORTFOLIO_MACRO_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MACRO_JSON_PATH", str(private_path))

    before = get_provider_refresh_readiness()
    result = run_provider_refresh_schedule()
    after = get_provider_refresh_readiness()

    assert before["policy"]["tier"] == "read_only"
    assert result["policy"]["tier"] == "draft_only"
    assert result["status"] == "completed"
    assert result["schedule"]["summary"]["jobs_recorded"] == 1
    assert result["schedule"]["readiness"][-1]["provider_id"] == "configured_macro"
    assert result["schedule"]["readiness"][-1]["readiness_status"] == "ready"
    assert after["summary"]["ready"] == 1

    combined = f"{before} {result} {after}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-schedule-macro" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "private_key" not in combined


def test_forbidden_compatibility_traps_are_blocked_and_redacted() -> None:
    live_order = place_live_order("INFY", 1, "buy")
    token = get_broker_trading_token("fyers")

    assert live_order["status"] == "blocked"
    assert token["status"] == "blocked"
    assert token["details"]["broker_token"] == "[REDACTED]"
