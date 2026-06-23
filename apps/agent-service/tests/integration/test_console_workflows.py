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
    order_id = order_payload["action"]["paper_order"]["order_id"]

    approval_response = client.post(
        f"/console/workflows/paper-orders/{order_id}/approval",
        json={
            "approved_by": "console-test-reviewer",
            "approval_note": "Approve simulated fill for workflow test.",
        },
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.json()
    assert approval_payload["action"]["status"] == "approved"
    assert approval_payload["action"]["policy"]["tier"] == "approval_required"
    assert approval_payload["action"]["approval_request"]["status"] == "approved"

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
