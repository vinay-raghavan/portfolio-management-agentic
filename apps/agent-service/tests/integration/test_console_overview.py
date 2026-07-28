from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from authlib.jose import JsonWebToken
from fastapi.testclient import TestClient

import app.fast_api_app as fast_api_app
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


def test_model_tuning_status_reports_provider_neutral_plan_without_secrets(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b,gemma:7b,gemma4:12b")
    monkeypatch.setenv("MODEL_TUNING_DEV_SET", "agent-service-dev")
    monkeypatch.setenv("MODEL_TUNING_HOLDOUT_SET", "agent-service-sealed")
    monkeypatch.setenv("GOOGLE_API_KEY", "should-not-be-returned")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    client = TestClient(app)

    response = client.get("/v1/models/tuning/status")

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload)
    assert payload["status"] == "ready"
    assert payload["active_provider"] == "ollama"
    assert payload["active_model"] == "llama3.1:8b"
    assert payload["provider_neutral"] is True
    assert payload["primary_candidate_model"] == "llama3.1:8b"
    assert payload["candidate_models"] == ["llama3.1:8b", "gemma:7b", "gemma4:12b"]
    assert payload["initial_tuning_mode"] == "prompt_routing_retrieval"
    assert payload["fine_tuning"]["enabled"] is False
    assert payload["fine_tuning"]["min_labeled_examples"] == 200
    assert payload["fine_tuning"]["required_prompt_routing_retrieval_iterations"] == 3
    assert payload["promotion_gate"]["safety_pass_rate"] == 1.0
    assert payload["promotion_gate"]["core_task_success_rate"] == 0.95
    assert payload["promotion_gate"]["max_p50_token_ratio_to_baseline"] == 1.1
    assert payload["promotion_gate"]["max_p95_latency_ratio_to_baseline"] == 1.2
    assert "should-not-be-returned" not in serialized
    assert "anthropic-secret" not in serialized
    assert "GOOGLE_API_KEY" not in serialized
    assert "raw_prompt" not in serialized.lower()
    assert "raw_response" not in serialized.lower()


def test_model_route_kill_switch_keeps_status_observable_and_blocks_evaluation(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b,gemma4:12b")
    monkeypatch.setenv("MODEL_ROUTE_KILL_SWITCH", "true")
    monkeypatch.setenv("GOOGLE_API_KEY", "should-not-be-returned")
    client = TestClient(app)

    runtime_status = client.get("/v1/models/ollama/status")
    tuning_status = client.get("/v1/models/tuning/status")
    candidate = client.post(
        "/v1/models/tuning/evaluate-candidate",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidate": {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.97,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_900,
                "p95_latency_ms": 4_700,
                "judge_error_count": 0,
            },
        },
    )
    suite = client.post(
        "/v1/models/tuning/evaluate-suite",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidates": [
                {
                    "provider": "ollama",
                    "model": "llama3.1:8b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.97,
                    "mean_response_score": 4.6,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 10_900,
                    "p95_latency_ms": 4_700,
                    "judge_error_count": 0,
                },
                {
                    "provider": "ollama",
                    "model": "gemma4:12b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.96,
                    "mean_response_score": 4.4,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 10_800,
                    "p95_latency_ms": 4_600,
                    "judge_error_count": 0,
                },
            ],
            "sealed_holdout_passed": True,
            "required_candidate_models": ["llama3.1:8b"],
        },
    )

    assert runtime_status.status_code == 200
    runtime_payload = runtime_status.json()
    assert runtime_payload["status"] == "blocked"
    assert runtime_payload["model_route_kill_switch_active"] is True
    assert "model_route_kill_switch_active" in runtime_payload["blocking_reasons"]
    assert "should-not-be-returned" not in str(runtime_payload)

    assert tuning_status.status_code == 200
    tuning_payload = tuning_status.json()
    assert tuning_payload["status"] == "blocked"
    assert tuning_payload["model_route_kill_switch_active"] is True
    assert tuning_payload["blocking_reasons"] == ["model_route_kill_switch_active"]
    assert "should-not-be-returned" not in str(tuning_payload)

    assert candidate.status_code == 503
    assert candidate.json()["detail"] == "model_route_kill_switch_active"
    assert suite.status_code == 503
    assert suite.json()["detail"] == "model_route_kill_switch_active"


def test_model_tuning_evaluates_allowed_llama_candidate_without_payloads(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b,gemma4:12b")
    monkeypatch.setenv("GOOGLE_API_KEY", "should-not-be-returned")
    client = TestClient(app)

    response = client.post(
        "/v1/models/tuning/evaluate-candidate",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidate": {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.97,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_900,
                "p95_latency_ms": 4_700,
                "judge_error_count": 0,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert payload["status"] == "evaluated"
    assert payload["provider_neutral"] is True
    assert payload["candidate_allowed"] is True
    assert payload["decision"]["promotable"] is True
    assert payload["decision"]["model"] == "llama3.1:8b"
    assert payload["decision"]["provider"] == "ollama"
    assert payload["decision"]["metrics"]["token_ratio_to_baseline"] == 1.09
    assert "should-not-be-returned" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "secret" not in serialized


def test_model_tuning_evaluation_fails_closed_for_weak_candidate(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b")
    client = TestClient(app)

    response = client.post(
        "/v1/models/tuning/evaluate-candidate",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidate": {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "safety_pass_rate": 0.99,
                "core_task_success_rate": 0.94,
                "mean_response_score": 3.9,
                "applicable_trajectory_score": 0.98,
                "p50_total_tokens": 11_500,
                "p95_latency_ms": 4_900,
                "judge_error_count": 1,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"]["promotable"] is False
    assert payload["decision"]["blocking_reasons"] == [
        "safety_pass_rate_below_100_percent",
        "core_task_success_below_95_percent",
        "mean_response_score_below_4",
        "applicable_trajectory_below_1",
        "judge_errors_present",
        "p50_tokens_exceed_110_percent_baseline",
        "p95_latency_exceed_120_percent_baseline",
    ]


def test_model_tuning_evaluation_rejects_unlisted_candidate(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b")
    client = TestClient(app)

    response = client.post(
        "/v1/models/tuning/evaluate-candidate",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidate": {
                "provider": "ollama",
                "model": "not-allowlisted:8b",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.97,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_900,
                "p95_latency_ms": 4_700,
                "judge_error_count": 0,
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model_candidate_not_allowed"


def test_model_tuning_evaluation_rejects_raw_prompt_or_secret_payload(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b")
    client = TestClient(app)

    response = client.post(
        "/v1/models/tuning/evaluate-candidate",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.5,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_000,
                "p95_latency_ms": 4_000,
                "judge_error_count": 0,
            },
            "candidate": {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.97,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 10_900,
                "p95_latency_ms": 4_700,
                "judge_error_count": 0,
                "raw_prompt": "do not store this secret prompt",
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "model_tuning_contains_sensitive_data"


def test_model_tuning_evaluates_provider_neutral_candidate_suite(monkeypatch) -> None:
    monkeypatch.setenv(
        "MODEL_TUNING_CANDIDATES",
        "llama3.1:8b,gemma4:12b,hosted-mini",
    )
    client = TestClient(app)

    response = client.post(
        "/v1/models/tuning/evaluate-suite",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 4_000,
                "p95_latency_ms": 5_000,
                "judge_error_count": 0,
            },
            "candidates": [
                {
                    "provider": "ollama",
                    "model": "gemma4:12b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.96,
                    "mean_response_score": 4.2,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 4_250,
                    "p95_latency_ms": 5_200,
                    "judge_error_count": 0,
                },
                {
                    "provider": "ollama",
                    "model": "llama3.1:8b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.96,
                    "mean_response_score": 4.5,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 4_100,
                    "p95_latency_ms": 5_200,
                    "judge_error_count": 0,
                },
                {
                    "provider": "openai_compatible",
                    "model": "hosted-mini",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.97,
                    "mean_response_score": 4.9,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 4_600,
                    "p95_latency_ms": 5_300,
                    "judge_error_count": 0,
                },
            ],
            "sealed_holdout_passed": True,
            "min_candidate_count": 3,
            "required_candidate_models": ["llama3.1:8b", "gemma4:12b"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert payload["status"] == "evaluated"
    assert payload["provider_neutral"] is True
    assert payload["decision"]["promotable"] is True
    assert payload["decision"]["selected"] == {
        "model": "llama3.1:8b",
        "provider": "ollama",
    }
    assert payload["decision"]["candidate_count"] == 3
    assert payload["decision"]["promotable_candidate_count"] == 2
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "secret" not in serialized


def test_model_tuning_suite_rejects_unlisted_or_sensitive_candidate(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_TUNING_CANDIDATES", "llama3.1:8b")
    client = TestClient(app)

    unlisted = client.post(
        "/v1/models/tuning/evaluate-suite",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 4_000,
                "p95_latency_ms": 5_000,
                "judge_error_count": 0,
            },
            "candidates": [
                {
                    "provider": "ollama",
                    "model": "not-allowlisted:8b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.96,
                    "mean_response_score": 4.5,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 4_100,
                    "p95_latency_ms": 5_200,
                    "judge_error_count": 0,
                },
            ],
            "sealed_holdout_passed": True,
        },
    )
    sensitive = client.post(
        "/v1/models/tuning/evaluate-suite",
        json={
            "baseline": {
                "provider": "gemini",
                "model": "incumbent",
                "safety_pass_rate": 1.0,
                "core_task_success_rate": 0.96,
                "mean_response_score": 4.6,
                "applicable_trajectory_score": 1.0,
                "p50_total_tokens": 4_000,
                "p95_latency_ms": 5_000,
                "judge_error_count": 0,
            },
            "candidates": [
                {
                    "provider": "ollama",
                    "model": "llama3.1:8b",
                    "safety_pass_rate": 1.0,
                    "core_task_success_rate": 0.96,
                    "mean_response_score": 4.5,
                    "applicable_trajectory_score": 1.0,
                    "p50_total_tokens": 4_100,
                    "p95_latency_ms": 5_200,
                    "judge_error_count": 0,
                    "raw_response": "secret transcript",
                },
            ],
            "sealed_holdout_passed": True,
        },
    )

    assert unlisted.status_code == 400
    assert unlisted.json()["detail"] == "model_candidate_not_allowed"
    assert sensitive.status_code == 400
    assert sensitive.json()["detail"] == "model_tuning_contains_sensitive_data"


def test_model_usage_telemetry_records_budgeted_metrics_without_payloads(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("MODEL_CONTEXT_WINDOW_TOKENS", "8192")
    client = TestClient(app)
    app.state.model_usage_events = []

    first = client.post(
        "/v1/models/usage/events",
        json={
            "provider": "ollama",
            "model": "llama3.1:8b",
            "route": "technical_analysis",
            "prompt_tokens": 3200,
            "output_tokens": 700,
            "tool_calls": 4,
            "queue_wait_ms": 120,
            "latency_ms": 2400,
            "retries": 1,
            "request_id": "req-usage-1",
        },
    )
    second = client.post(
        "/v1/models/usage/events",
        json={
            "provider": "ollama",
            "model": "llama3.1:8b",
            "route": "technical_analysis",
            "prompt_tokens": 7000,
            "output_tokens": 1700,
            "tool_calls": 6,
            "queue_wait_ms": 40,
            "latency_ms": 4000,
            "retries": 0,
            "request_id": "req-usage-2",
        },
    )
    summary = client.get("/v1/models/usage/summary")

    assert first.status_code == 200
    assert first.json()["budget_decision"]["allowed"] is True
    assert second.status_code == 200
    assert second.json()["budget_decision"]["allowed"] is False
    assert "prompt_input_budget_exceeded" in second.json()["budget_decision"]["violations"]
    assert "output_budget_exceeded" in second.json()["budget_decision"]["violations"]
    assert "tool_call_budget_exceeded" in second.json()["budget_decision"]["violations"]

    assert summary.status_code == 200
    payload = summary.json()
    serialized = str(payload).lower()
    assert payload["summary"]["event_count"] == 2
    assert payload["summary"]["routes"] == {"technical_analysis": 2}
    assert payload["summary"]["prompt_tokens"] == 10200
    assert payload["summary"]["output_tokens"] == 2400
    assert payload["budget_violations"] == {"technical_analysis": 1}
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized
    assert "secret" not in serialized


def test_model_usage_telemetry_uses_postgres_store_when_configured(monkeypatch) -> None:
    class _FakeStore:
        def __init__(self) -> None:
            self.recorded = []

        def record(self, event, decision) -> None:
            self.recorded.append((event, decision))

        def list_recent(self, *, limit: int = 500):
            return tuple(event for event, _decision in self.recorded)

    fake_store = _FakeStore()

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr("app.fast_api_app._model_usage_store", lambda actor=None: fake_store)
    app.state.model_usage_events = []
    client = TestClient(app)

    recorded = client.post(
        "/v1/models/usage/events",
        headers={
            "X-Actor-Sub": "model-telemetry-worker",
            "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
            "X-Actor-Roles": "admin",
            "X-Request-Id": "req-http-postgres-usage",
        },
        json={
            "provider": "ollama",
            "model": "llama3.1:8b",
            "route": "research",
            "prompt_tokens": 1200,
            "output_tokens": 300,
            "tool_calls": 3,
            "queue_wait_ms": 50,
            "latency_ms": 1400,
            "retries": 0,
            "request_id": "req-postgres-usage",
        },
    )
    summary = client.get(
        "/v1/models/usage/summary",
        headers={
            "X-Actor-Sub": "model-telemetry-worker",
            "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
            "X-Actor-Roles": "admin",
            "X-Request-Id": "req-http-postgres-summary",
        },
    )

    assert recorded.status_code == 200
    assert recorded.json()["stored_event_count"] == 1
    assert summary.status_code == 200
    payload = summary.json()
    serialized = str(payload).lower()
    assert payload["summary"]["event_count"] == 1
    assert payload["summary"]["routes"] == {"research": 1}
    assert app.state.model_usage_events == []
    assert "db-secret" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized


def test_model_usage_telemetry_requires_actor_context_for_postgres(monkeypatch) -> None:
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    client = TestClient(app)

    response = client.get("/v1/models/usage/summary")

    assert response.status_code == 401
    assert response.json()["detail"] == "actor_context_required"
    assert "db-secret" not in str(response.json())


def test_model_usage_telemetry_rejects_payload_content_fields(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_MODEL", "llama3.1:8b")
    client = TestClient(app)

    response = client.post(
        "/v1/models/usage/events",
        json={
            "provider": "ollama",
            "model": "llama3.1:8b",
            "route": "research",
            "prompt_tokens": 10,
            "output_tokens": 5,
            "tool_calls": 1,
            "queue_wait_ms": 0,
            "latency_ms": 20,
            "retries": 0,
            "request_id": "req-secret",
            "raw_prompt": "provider secret should not be accepted",
        },
    )

    assert response.status_code == 422


def test_session_summary_api_requires_actor_context() -> None:
    client = TestClient(app)

    response = client.get("/v1/sessions/session-1/summary")

    assert response.status_code == 401
    assert response.json()["detail"] == "actor_subject_required"


def test_session_summary_api_can_derive_actor_from_oidc_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("OIDC_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_AUDIENCE", "portfolio-agent")
    monkeypatch.setenv("OIDC_TENANT_CLAIM", "tenant_id")
    monkeypatch.setenv("OIDC_ROLES_CLAIM", "roles")
    monkeypatch.setenv("OIDC_ALLOWED_ALGORITHMS", "HS256")
    monkeypatch.setenv(
        "OIDC_JWKS_JSON",
        json.dumps({"kty": "oct", "k": "dGVzdC1zaWduaW5nLXNlY3JldA"}),
    )
    token = JsonWebToken(["HS256"]).encode(
        {"alg": "HS256"},
        {
            "iss": "https://issuer.example.com",
            "aud": "portfolio-agent",
            "sub": "immutable-subject-123",
            "tenant_id": "tenant-oidc",
            "roles": ["analyst"],
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "nonce": "nonce-123",
        },
        "test-signing-secret",
    )
    client = TestClient(app)

    missing_token = client.get(
        "/v1/sessions/session-oidc/summary",
        headers={"X-Request-Id": "req-oidc", "X-OIDC-Nonce": "nonce-123"},
    )
    authorized = client.get(
        "/v1/sessions/session-oidc/summary",
        headers={
            "Authorization": f"Bearer {token.decode('utf-8')}",
            "X-Request-Id": "req-oidc",
            "X-OIDC-Nonce": "nonce-123",
        },
    )

    assert missing_token.status_code == 401
    assert missing_token.json()["detail"] == "oidc_bearer_token_required"
    assert authorized.status_code == 404
    assert authorized.json()["detail"] == "session_memory_not_found"


def test_oidc_authorization_code_pkce_start_and_callback(monkeypatch) -> None:
    monkeypatch.setenv("OIDC_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_AUDIENCE", "portfolio-agent")
    monkeypatch.setenv("OIDC_AUTHORIZATION_ENDPOINT", "https://issuer.example.com/auth")
    monkeypatch.setenv("OIDC_TOKEN_ENDPOINT", "https://issuer.example.com/token")
    monkeypatch.setenv("OIDC_CLIENT_ID", "portfolio-console")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:8000/v1/auth/oidc/callback")
    monkeypatch.setenv("OIDC_TENANT_CLAIM", "tenant_id")
    monkeypatch.setenv("OIDC_ROLES_CLAIM", "roles")
    monkeypatch.setenv("OIDC_ALLOWED_ALGORITHMS", "HS256")
    monkeypatch.setenv(
        "OIDC_JWKS_JSON",
        json.dumps({"kty": "oct", "k": "dGVzdC1zaWduaW5nLXNlY3JldA"}),
    )
    fast_api_app._OIDC_AUTH_STATES.clear()
    captured_exchange: dict[str, str] = {}
    captured_nonce: dict[str, str] = {}

    def _fake_exchange(*, config, code: str, code_verifier: str) -> dict[str, str]:
        captured_exchange.update(
            {
                "token_endpoint": config.token_endpoint,
                "code": code,
                "code_verifier": code_verifier,
            }
        )
        token = JsonWebToken(["HS256"]).encode(
            {"alg": "HS256"},
            {
                "iss": "https://issuer.example.com",
                "aud": "portfolio-agent",
                "sub": "immutable-subject-123",
                "tenant_id": "tenant-oidc",
                "roles": ["analyst"],
                "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
                "nonce": captured_nonce["value"],
            },
            "test-signing-secret",
        )
        return {"id_token": token.decode("utf-8")}

    monkeypatch.setattr(
        fast_api_app,
        "_exchange_oidc_authorization_code",
        _fake_exchange,
    )
    client = TestClient(app)

    start = client.post("/v1/auth/oidc/start")
    start_payload = start.json()
    query = parse_qs(urlparse(start_payload["authorization_url"]).query)
    state = query["state"][0]
    captured_nonce["value"] = str(
        fast_api_app._OIDC_AUTH_STATES[start_payload["state_hash"]]["nonce"]
    )

    callback = client.post(
        "/v1/auth/oidc/callback",
        json={"state": state, "code": "browser-auth-code"},
    )

    assert start.status_code == 200
    assert start_payload["status"] == "authorization_required"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["portfolio-console"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["nonce"]
    assert "code_verifier" not in str(start_payload).lower()
    assert callback.status_code == 200
    assert callback.json()["status"] == "authenticated"
    assert callback.json()["actor"] == {
        "tenant_id": "tenant-oidc",
        "user_id": "immutable-subject-123",
        "roles": ["analyst"],
        "issuer": "https://issuer.example.com",
    }
    assert captured_exchange["token_endpoint"] == "https://issuer.example.com/token"
    assert captured_exchange["code"] == "browser-auth-code"
    assert len(captured_exchange["code_verifier"]) >= 43
    assert "id_token" not in str(callback.json()).lower()
    assert not fast_api_app._OIDC_AUTH_STATES


def test_oidc_authorization_callback_rejects_unknown_state(monkeypatch) -> None:
    monkeypatch.setenv("OIDC_AUTH_ENABLED", "true")
    monkeypatch.setenv("OIDC_ISSUER", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_AUDIENCE", "portfolio-agent")
    monkeypatch.setenv("OIDC_AUTHORIZATION_ENDPOINT", "https://issuer.example.com/auth")
    monkeypatch.setenv("OIDC_TOKEN_ENDPOINT", "https://issuer.example.com/token")
    monkeypatch.setenv("OIDC_CLIENT_ID", "portfolio-console")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:8000/v1/auth/oidc/callback")
    monkeypatch.setenv("OIDC_JWKS_JSON", json.dumps({"kty": "oct", "k": "unused"}))
    fast_api_app._OIDC_AUTH_STATES.clear()
    client = TestClient(app)

    response = client.post(
        "/v1/auth/oidc/callback",
        json={"state": "unknown-state", "code": "browser-auth-code"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "oidc_state_unknown_or_expired"


def test_session_summary_api_uses_postgres_store_when_configured(monkeypatch) -> None:
    now = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)

    class _Record:
        session_id = "session-1"
        request_id = "req-session"
        summary = "User asked for a paper-only risk review."
        object_refs = ({"type": "paper_order", "id": "order-123"},)
        idle_expires_at = now + timedelta(hours=2)
        absolute_expires_at = now + timedelta(hours=24)
        deleted_at = None

    class _FakeStore:
        def __init__(self) -> None:
            self.deleted: list[str] = []

        def upsert_summary(self, **_kwargs):
            return _Record()

        def get(self, session_id: str):
            assert session_id == "session-1"
            return _Record()

        def delete(self, session_id: str) -> None:
            self.deleted.append(session_id)

    fake_store = _FakeStore()
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        "app.fast_api_app._session_memory_store_for_actor",
        lambda actor=None: fake_store,
    )
    client = TestClient(app)
    headers = {
        "X-Actor-Sub": "22222222-2222-2222-2222-222222222222",
        "X-Tenant-Id": "11111111-1111-1111-1111-111111111111",
        "X-Actor-Roles": "analyst",
        "X-Request-Id": "req-session",
    }

    saved = client.put(
        "/v1/sessions/session-1/summary",
        headers=headers,
        json={
            "summary": "User asked for a paper-only risk review.",
            "object_refs": [{"type": "paper_order", "id": "order-123"}],
        },
    )
    loaded = client.get("/v1/sessions/session-1/summary", headers=headers)
    deleted = client.delete("/v1/sessions/session-1/summary", headers=headers)

    assert saved.status_code == 200
    assert saved.json()["status"] == "saved"
    assert saved.json()["memory"]["summary"] == "User asked for a paper-only risk review."
    assert "db-secret" not in str(saved.json())
    assert loaded.status_code == 200
    assert loaded.json()["status"] == "ready"
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted", "session_id": "session-1"}
    assert fake_store.deleted == ["session-1"]


def test_session_summary_api_rejects_raw_or_secret_memory(monkeypatch) -> None:
    monkeypatch.delenv("PORTFOLIO_STORAGE_BACKEND", raising=False)
    client = TestClient(app)

    response = client.put(
        "/v1/sessions/session-raw/summary",
        headers={
            "X-Actor-Sub": "user-1",
            "X-Tenant-Id": "tenant-1",
            "X-Actor-Roles": "analyst",
            "X-Request-Id": "req-session-raw",
        },
        json={
            "summary": "Raw account payload: {'holdings': [{'isin': 'secret'}]}",
            "object_refs": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "session_memory_invalid"


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
