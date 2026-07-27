from __future__ import annotations

from fastapi.testclient import TestClient

from app.fast_api_app import app


def test_console_workflows_expose_focused_policy_safe_pages() -> None:
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    payload = response.json()
    page_ids = {page["id"] for page in payload["pages"]}
    assert {
        "dashboard",
        "screener",
        "strategy-backtest",
        "paper-approvals",
        "reports",
        "settings",
    } <= page_ids
    assert payload["mode"] == "paper_only"
    assert payload["safety"]["live_trading"] == "blocked"
    assert payload["screener"]["run"]["status"] == "success"
    assert payload["screener"]["factor_stack"]["status"] == "success"
    assert payload["strategy_backtest"]["actions"]["draft_strategy"]["tier"] == "draft_only"
    assert payload["strategy_backtest"]["actions"]["create_backtest"]["tier"] == "draft_only"
    assert payload["paper_approvals"]["actions"]["approve_simulation"]["tier"] == "approval_required"
    assert payload["paper_approvals"]["actions"]["simulate_fill"]["tier"] == "approval_required"
    assert payload["reports"]["report"]["status"] == "success"
    assert payload["settings"]["providers"]["status"] == "success"
    assert "place_live_order" not in str(payload).lower()
    assert "never-return-this" not in str(payload).lower()
    assert "secret" not in str(payload).lower()


def test_console_workflows_expose_provider_import_validation_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    bad_sentiment_path = tmp_path / "bad-sentiment.json"
    bad_sentiment_path.write_text("{bad")
    monkeypatch.setenv("PORTFOLIO_SENTIMENT_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_SENTIMENT_JSON_PATH", str(bad_sentiment_path))
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    payload = response.json()
    validation = payload["settings"]["import_validation"]
    validations = {
        item["provider_id"]: item
        for item in validation["validations"]
    }

    assert validation["status"] == "success"
    assert validation["policy"]["tier"] == "read_only"
    assert validation["summary"]["needs_attention"] == 1
    assert validations["configured_sentiment"]["status"] == "error"
    assert "not valid JSON" in validations["configured_sentiment"]["message"]

    combined = f"{validation}".lower()
    assert str(tmp_path).lower() not in combined
    assert "bad-sentiment" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_console_workflows_track_provider_profiles_and_refresh_jobs_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    market_path = tmp_path / "private-market-provider.json"
    market_path.write_text("{bad")
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(tmp_path / "provider-config.db"))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(market_path))
    client = TestClient(app)

    refresh_response = client.post(
        "/console/workflows/provider-profiles/configured_market_data/refresh",
    )
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()

    assert refresh_payload["action"]["status"] == "needs_attention"
    assert refresh_payload["action"]["policy"]["tier"] == "draft_only"
    assert refresh_payload["action"]["job"]["validation_status"] == "error"
    assert (
        refresh_payload["state"]["settings"]["provider_import_jobs"]["import_jobs"][0][
            "provider_id"
        ]
        == "configured_market_data"
    )

    workflow_response = client.get("/console/workflows", params={"preset": "momentum"})
    assert workflow_response.status_code == 200
    settings = workflow_response.json()["settings"]
    profiles = {
        profile["provider_id"]: profile
        for profile in settings["provider_profiles"]["profiles"]
    }

    assert settings["provider_profiles"]["status"] == "success"
    assert profiles["configured_market_data"]["last_validation_status"] == "error"
    assert settings["provider_import_jobs"]["import_jobs"][0]["validation_status"] == "error"

    combined = (
        f"{refresh_payload['action']} "
        f"{settings['provider_profiles']} "
        f"{settings['provider_import_jobs']}"
    ).lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-provider" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_console_workflows_expose_provider_source_setup_gaps_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(tmp_path / "provider-config.db"))
    monkeypatch.setenv("PORTFOLIO_VOLATILITY_PROVIDER", "json_file")
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    settings = response.json()["settings"]
    profiles = {
        profile["provider_id"]: profile
        for profile in settings["provider_profiles"]["profiles"]
    }
    volatility = profiles["configured_volatility"]

    assert volatility["provider_mode"] == "json_file"
    assert volatility["required_env"] == [
        "PORTFOLIO_VOLATILITY_PROVIDER",
        "PORTFOLIO_VOLATILITY_JSON_PATH",
    ]
    assert volatility["missing_env"] == ["PORTFOLIO_VOLATILITY_JSON_PATH"]
    assert volatility["source_label"] == "env:PORTFOLIO_VOLATILITY_JSON_PATH"

    combined = f"{settings['provider_profiles']}".lower()
    assert str(tmp_path).lower() not in combined
    assert "provider-config.db" not in combined
    assert "api_key" not in combined
    assert "token" not in combined


def test_console_workflows_expose_provider_source_templates_without_path_leaks(
    tmp_path,
) -> None:
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    guidance = response.json()["settings"]["provider_source_templates"]
    templates = {
        template["provider_id"]: template
        for template in guidance["templates"]
    }

    assert guidance["status"] == "success"
    assert guidance["policy"]["tier"] == "read_only"
    assert guidance["summary"]["total"] == 6
    assert templates["configured_market_data"]["template_json"]["snapshots"][0][
        "symbol"
    ]
    assert templates["configured_macro"]["template_json"]["macro"][0]["metrics"]
    assert "json_file" in guidance["provider_mode_options"]

    combined = f"{guidance}".lower()
    assert str(tmp_path).lower() not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined


def test_console_workflows_expose_guided_provider_onboarding_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    market_path = tmp_path / "private-market-export.json"
    market_path.write_text(
        """
        {
          "snapshots": [
            {
              "symbol": "SAMPLE_EQTY",
              "as_of": "2026-06-22",
              "bars": [
                {
                  "date": "2026-06-22",
                  "open": 100,
                  "high": 104,
                  "low": 99,
                  "close": 103,
                  "volume": 123000
                }
              ],
              "metrics": {"rsi14": 59.4}
            }
          ]
        }
        """
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(tmp_path / "provider-config.db"))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(market_path))
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    guidance = response.json()["settings"]["provider_source_onboarding"]
    cards = {
        card["provider_id"]: card
        for card in guidance["onboarding_cards"]
    }
    market = cards["configured_market_data"]

    assert guidance["status"] == "success"
    assert guidance["policy"]["tier"] == "read_only"
    assert guidance["summary"]["configured"] == 1
    assert market["validation"]["status"] == "valid"
    assert market["refresh_readiness"]["status"] == "pending_refresh"
    assert market["setup_state"] == "ready_for_refresh"
    assert market["recommended_next_step"] == "refresh_provider_profile"
    assert "Run profile refresh" in market["operator_steps"]
    assert market["template"]["path_env"] == "PORTFOLIO_MARKET_DATA_JSON_PATH"
    assert market["safe_actions"][-1]["tool"] == "refresh_provider_import_profile"
    assert market["safe_actions"][-1]["enabled"] is True

    combined = f"{guidance}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-export" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined


def test_console_workflows_expose_provider_import_previews_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    market_path = tmp_path / "private-market-preview.json"
    market_path.write_text(
        """
        {
          "snapshots": [
            {
              "symbol": "SAMPLE_EQTY",
              "as_of": "2026-06-22",
              "bars": [
                {
                  "date": "2026-06-22",
                  "open": 100,
                  "high": 104,
                  "low": 99,
                  "close": 103,
                  "volume": 123000
                }
              ],
              "metrics": {"rsi14": 59.4, "api_token": "should_not_persist"},
              "notes": ["private-market-preview token leak candidate"]
            }
          ]
        }
        """
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(tmp_path / "provider-config.db"))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(tmp_path / "market-data.db"))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(market_path))
    client = TestClient(app)

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    previews = response.json()["settings"]["provider_import_previews"]
    by_provider = {
        preview["provider_id"]: preview
        for preview in previews["previews"]
    }
    market = by_provider["configured_market_data"]

    assert previews["status"] == "success"
    assert previews["policy"]["tier"] == "read_only"
    assert previews["summary"]["configured"] == 1
    assert previews["summary"]["would_write"] == 1
    assert previews["summary"]["normalized_count"] == 1
    assert market["target_store"] == "market_data_snapshots"
    assert market["normalized_count"] == 1
    assert market["would_write"] is True
    assert market["sample_identifiers"] == ["SAMPLE_EQTY"]

    combined = f"{previews}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-preview" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined


def test_console_workflows_expose_provider_import_reconciliation_without_path_leaks(
    monkeypatch,
    tmp_path,
) -> None:
    market_path = tmp_path / "private-market-reconciliation.json"
    market_path.write_text(
        """
        {
          "snapshots": [
            {
              "symbol": "SAMPLE_EQTY",
              "as_of": "2026-06-22",
              "bars": [
                {
                  "date": "2026-06-22",
                  "open": 100,
                  "high": 104,
                  "low": 99,
                  "close": 103,
                  "volume": 123000
                }
              ],
              "metrics": {"rsi14": 59.4, "api_token": "should_not_persist"},
              "notes": ["private-market-reconciliation token leak candidate"]
            }
          ]
        }
        """
    )
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", str(tmp_path / "provider-config.db"))
    monkeypatch.setenv("MARKET_DATA_DB_PATH", str(tmp_path / "market-data.db"))
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_PROVIDER", "json_file")
    monkeypatch.setenv("PORTFOLIO_MARKET_DATA_JSON_PATH", str(market_path))
    client = TestClient(app)

    refresh_response = client.post(
        "/console/workflows/provider-profiles/configured_market_data/refresh",
    )
    assert refresh_response.status_code == 200

    response = client.get("/console/workflows", params={"preset": "momentum"})

    assert response.status_code == 200
    reconciliation = response.json()["settings"]["provider_import_reconciliation"]
    by_provider = {
        item["provider_id"]: item
        for item in reconciliation["reconciliations"]
    }
    market = by_provider["configured_market_data"]

    assert reconciliation["status"] == "success"
    assert reconciliation["policy"]["tier"] == "read_only"
    assert reconciliation["summary"]["in_sync"] == 1
    assert market["reconciliation_status"] == "in_sync"
    assert market["preview"]["normalized_count"] == 1
    assert market["latest_job"]["imported_count"] == 1
    assert market["store"]["stored_count"] == 1

    combined = f"{reconciliation}".lower()
    assert str(tmp_path).lower() not in combined
    assert "private-market-reconciliation" not in combined
    assert "api_key" not in combined
    assert "token" not in combined
    assert "secret" not in combined


def test_console_workflow_action_lifecycle_stays_paper_only() -> None:
    client = TestClient(app)

    draft_response = client.post(
        "/console/workflows/strategy-drafts",
        json={
            "symbol": "TATAMOTORS",
            "rationale": "Breakout continuation remains backed by fixture evidence.",
        },
    )
    assert draft_response.status_code == 200
    draft_payload = draft_response.json()
    assert draft_payload["action"]["status"] == "success"
    assert draft_payload["action"]["policy"]["tier"] == "draft_only"
    strategy_id = draft_payload["action"]["strategy"]["strategy_id"]

    backtest_response = client.post(
        "/console/workflows/backtests",
        json={
            "symbol": "TATAMOTORS",
            "setup": "breakout-continuation",
            "start_date": "2026-01-02",
            "end_date": "2026-06-22",
        },
    )
    assert backtest_response.status_code == 200
    backtest_payload = backtest_response.json()
    assert backtest_payload["action"]["status"] == "success"
    assert backtest_payload["action"]["policy"]["tier"] == "draft_only"
    assert backtest_payload["action"]["backtest_request"]["mode"] == "paper"

    order_response = client.post(
        "/console/workflows/paper-orders",
        json={
            "strategy_id": strategy_id,
            "symbol": "TATAMOTORS",
            "side": "buy",
            "quantity": 2,
            "order_type": "market",
        },
    )
    assert order_response.status_code == 200
    order_payload = order_response.json()
    assert order_payload["action"]["status"] == "pending_approval"
    assert order_payload["action"]["policy"]["tier"] == "draft_only"
    assert order_payload["action"]["readiness_preflight"]["status"] == (
        "ready_for_approval"
    )
    assert order_payload["action"]["paper_order"]["readiness_preflight"][
        "submitted_strategy_gate"
    ]["status"] == "pass"
    readiness = order_payload["state"]["reports"]["report"]["report"]["sections"][
        "paper_order_readiness"
    ]
    assert readiness["latest_preflight"]["status"] == "ready_for_approval"
    assert readiness["latest_preflight"]["submitted_strategy_gate"]["status"] == "pass"
    assert readiness["latest_preflight"]["paper_only_policy"]["live_trading"] == (
        "disabled"
    )
    order_id = order_payload["action"]["paper_order"]["order_id"]

    approval_response = client.post(
        f"/console/workflows/paper-orders/{order_id}/approval",
        headers={
            "X-Actor-Sub": "oidc-console-approver",
            "X-Tenant-Id": "tenant-console-test",
            "X-Actor-Roles": "viewer,approver",
            "X-Request-Id": "req-console-approval",
        },
        json={"approval_note": "Approve simulated fill for workflow test."},
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.json()
    assert approval_payload["action"]["status"] == "approved"
    assert approval_payload["action"]["policy"]["tier"] == "approval_required"
    assert approval_payload["action"]["approval_request"]["status"] == "approved"
    assert approval_payload["action"]["audit_event"]["actor"] == "oidc-console-approver"
    assert (
        approval_payload["action"]["audit_event"]["redacted_payload"]["approved_by"]
        == "oidc-console-approver"
    )

    fill_response = client.post(
        f"/console/workflows/paper-orders/{order_id}/fill",
        json={"fill_price": 982.5},
    )
    assert fill_response.status_code == 200
    fill_payload = fill_response.json()
    assert fill_payload["action"]["status"] == "filled"
    assert fill_payload["action"]["policy"]["tier"] == "approval_required"
    assert fill_payload["action"]["paper_fill"]["mode"] == "paper"
    assert fill_payload["state"]["paper_approvals"]["accounting"]["accounting"][
        "simulated_fills"
    ] >= 1
    assert "place_live_order" not in str(fill_payload).lower()
    assert "never-return-this" not in str(fill_payload).lower()


def test_console_approval_rejects_body_approver_spoofing() -> None:
    client = TestClient(app)
    strategy_response = client.post(
        "/console/workflows/strategy-drafts",
        json={
            "symbol": "TATAMOTORS",
            "rationale": "Identity spoof regression coverage.",
        },
    )
    strategy_id = strategy_response.json()["action"]["strategy"]["strategy_id"]
    order_response = client.post(
        "/console/workflows/paper-orders",
        json={
            "strategy_id": strategy_id,
            "symbol": "TATAMOTORS",
            "side": "buy",
            "quantity": 7,
            "order_type": "market",
        },
    )
    order_id = order_response.json()["action"]["paper_order"]["order_id"]

    response = client.post(
        f"/console/workflows/paper-orders/{order_id}/approval",
        headers={
            "X-Actor-Sub": "verified-human-approver",
            "X-Tenant-Id": "tenant-console-test",
            "X-Actor-Roles": "approver",
            "X-Request-Id": "req-spoof-attempt",
        },
        json={
            "approved_by": "model-or-attacker",
            "approval_note": "Try to spoof the human approver.",
        },
    )

    assert response.status_code == 422


def test_console_approval_requires_approver_actor_role() -> None:
    client = TestClient(app)
    response = client.post(
        "/console/workflows/paper-orders/unknown/approval",
        headers={
            "X-Actor-Sub": "analyst-only",
            "X-Tenant-Id": "tenant-console-test",
            "X-Actor-Roles": "analyst",
            "X-Request-Id": "req-no-approval-role",
        },
        json={"approval_note": "Should not reach ledger lookup."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "approver_role_required"
