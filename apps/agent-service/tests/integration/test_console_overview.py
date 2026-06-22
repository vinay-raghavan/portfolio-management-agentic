from __future__ import annotations

from fastapi.testclient import TestClient

from app.fast_api_app import app


def test_console_overview_exposes_safe_workflow_state() -> None:
    client = TestClient(app)

    response = client.get("/console/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "paper_only"
    assert payload["safety"]["live_trading"] == "blocked"
    assert payload["safety"]["broker_trading_tokens"] == "forbidden"
    assert payload["briefing"]["status"] == "success"
    assert payload["providers"]["status"] == "success"
    assert payload["screener"]["status"] == "success"
    assert payload["recommendation"]["status"] == "success"
    assert payload["report"]["status"] == "success"
    assert payload["paper_ledger"]["accounting"]["status"] == "success"
    assert "place_live_order" not in str(payload).lower()
    assert "never-return-this" not in str(payload).lower()
    assert "secret" not in str(payload).lower()
