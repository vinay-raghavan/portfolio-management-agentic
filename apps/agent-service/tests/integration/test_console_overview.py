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
    monkeypatch.setenv("OLLAMA_AVAILABLE_MODEL_DIGESTS", "llama3.1:8b=sha256:local-test")
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
    assert payload["model_digest_verified"] is True
    assert payload["model_inventory_source"] == "env"
    assert payload["model_inventory"] == []
    assert payload["blocking_reasons"] == []
    assert payload["route_budgets"]["research"]["effective_input_tokens"] == 6553
    assert "should-not-be-returned" not in serialized
    assert "GOOGLE_API_KEY" not in serialized


def test_storage_status_reports_redacted_production_like_readiness(monkeypatch) -> None:
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setenv("REDIS_URL", "redis://:redis-secret@redis:6379/0")
    monkeypatch.setenv("PAPER_LEDGER_DB_PATH", "/data/paper-ledger.db")
    monkeypatch.setenv("MARKET_DATA_DB_PATH", "/data/market-data.db")
    monkeypatch.setenv("PROVIDER_CONFIG_DB_PATH", "/data/provider-config.db")
    client = TestClient(app)

    response = client.get("/v1/storage/status")

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload)
    assert payload["status"] == "ready"
    assert payload["profile"]["backend"] == "postgres"
    assert payload["profile"]["production_like"] is True
    assert payload["profile"]["migrations_required"] is True
    assert payload["profile"]["database_url"] == (
        "postgresql+psycopg://portfolio:***@postgres:5432/portfolio_agentic"
    )
    assert payload["profile"]["redis_url"] == "redis://:***@redis:6379/0"
    assert payload["readiness"]["ready"] is True
    assert payload["readiness"]["blocking_reasons"] == []
    assert "db-secret" not in serialized
    assert "redis-secret" not in serialized


def test_storage_status_blocks_sqlite_when_production_like_required(monkeypatch) -> None:
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "sqlite")
    monkeypatch.delenv("PORTFOLIO_DATABASE_URL", raising=False)
    client = TestClient(app)

    response = client.get("/v1/storage/status?require_production_like=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["profile"]["backend"] == "sqlite"
    assert payload["readiness"]["blocking_reasons"] == [
        "postgres_required_for_production_like_testing"
    ]
