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


def test_ollama_model_status_reports_profile_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.containers.internal:11434")
    monkeypatch.setenv("OLLAMA_MODEL_DIGEST", "sha256:local-test")
    monkeypatch.setenv("OLLAMA_AVAILABLE_MODELS", "llama3.1:8b")
    monkeypatch.setenv("MODEL_CONTEXT_WINDOW_TOKENS", "8192")
    monkeypatch.setenv("MODEL_SUPPORTS_TOOL_USE", "true")
    monkeypatch.setenv("MODEL_SUPPORTS_STRUCTURED_OUTPUTS", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "should-not-be-returned")
    client = TestClient(app)

    response = client.get("/v1/models/ollama/status")

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload)
    assert payload["status"] == "ready"
    assert payload["provider"] == "ollama"
    assert payload["model"] == "llama3.1:8b"
    assert payload["model_digest_pinned"] is True
    assert payload["startup_allowed"] is True
    assert payload["blocking_reasons"] == []
    assert payload["route_budgets"]["research"]["effective_input_tokens"] == 6553
    assert "should-not-be-returned" not in serialized
    assert "GOOGLE_API_KEY" not in serialized
