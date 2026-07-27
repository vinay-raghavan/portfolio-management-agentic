# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import os
import secrets
import sys
from base64 import urlsafe_b64encode
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import urlopen
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.actor_context import (
    ActorContext,
    actor_context_dependency,
    build_actor_context,
)
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback
from app.console import (
    approve_console_paper_order,
    build_console_overview,
    build_console_workflows,
    create_console_backtest,
    create_console_paper_order,
    draft_console_strategy,
    refresh_console_provider_profile,
    run_console_provider_refresh_schedule,
    simulate_console_paper_fill,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
domain_path = str(REPO_ROOT / "packages/domain")
if domain_path not in sys.path:
    sys.path.insert(0, domain_path)
model_provider_path = str(REPO_ROOT / "packages/model-provider")
if model_provider_path not in sys.path:
    sys.path.insert(0, model_provider_path)

from portfolio_domain import (  # noqa: E402
    BUILTIN_RESEARCH_SOURCES,
    PATTERN_CARDS,
    BrokerAccountSnapshot,
    DatabaseBackend,
    DeterministicPaperExecutionWorker,
    FileBackedResearchStore,
    FyersConnection,
    FyersOAuthSession,
    InMemoryFyersPkceVerifierCache,
    PaperBatchRequest,
    PaperExecutionDecision,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionQueueProcessor,
    PaperExecutionWorkerRequest,
    PaperExecutionWorkItem,
    PostgresActorIdentityStore,
    PostgresFyersIntegrationStore,
    PostgresPaperExecutionStore,
    PostgresResearchStore,
    PostgresSessionMemoryStore,
    ProviderRefreshJob,
    ProviderSnapshotEnvelope,
    RedisFyersPkceVerifierCache,
    SessionMemoryPolicy,
    SessionMemoryRecord,
    SessionMemoryValidationError,
    actor_hash,
    evaluate_credential_vault_readiness,
    evaluate_database_runtime_readiness,
    get_fyers_readonly_connector,
    hash_oauth_state,
    issue_paper_execution_grant,
    load_credential_vault_profile,
    load_database_runtime_profile,
    normalize_research_query,
    sanitize_session_memory_payload,
)
from portfolio_model_provider import (  # noqa: E402
    ModelCandidateEvaluation,
    ModelProvider,
    ModelUsageEvent,
    OllamaModelMetadata,
    PostgresModelUsageStore,
    build_model_capability_report,
    build_model_tuning_plan,
    evaluate_model_candidate_for_tuning,
    evaluate_model_candidate_suite_for_tuning,
    evaluate_model_usage_event,
    load_model_runtime_profile,
    parse_ollama_tags_response,
    summarize_model_usage_events,
)

setup_telemetry()


class LocalLogger:
    def log_struct(self, payload: dict, severity: str = "INFO") -> None:
        logging.log(getattr(logging, severity, logging.INFO), "%s", payload)


class StrategyDraftRequest(BaseModel):
    symbol: str = Field(default="TATAMOTORS", min_length=1, max_length=32)
    rationale: str = Field(min_length=1, max_length=500)


class BacktestRequestPayload(BaseModel):
    symbol: str = Field(default="TATAMOTORS", min_length=1, max_length=32)
    setup: str = Field(default="breakout-continuation", min_length=1, max_length=80)
    start_date: str = Field(default="2026-01-02", min_length=10, max_length=10)
    end_date: str = Field(default="2026-06-22", min_length=10, max_length=10)


class PaperOrderRequest(BaseModel):
    strategy_id: str = Field(min_length=1, max_length=120)
    symbol: str = Field(default="TATAMOTORS", min_length=1, max_length=32)
    side: str = Field(default="buy", min_length=3, max_length=4)
    quantity: int = Field(default=2, ge=1, le=1000)
    order_type: str = Field(default="market", min_length=5, max_length=6)
    requested_price: float | None = Field(default=None, gt=0)


class PaperOrderApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_note: str = Field(default="", max_length=500)


class ModelUsageEventRequest(BaseModel):
    provider: ModelProvider
    model: str = Field(min_length=1, max_length=120)
    route: str = Field(min_length=1, max_length=120)
    prompt_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    queue_wait_ms: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    retries: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=120)

    model_config = ConfigDict(extra="forbid")


class ModelCandidateEvaluationRequest(BaseModel):
    provider: ModelProvider
    model: str = Field(min_length=1, max_length=120)
    safety_pass_rate: float = Field(ge=0, le=1)
    core_task_success_rate: float = Field(ge=0, le=1)
    mean_response_score: float = Field(ge=0, le=5)
    applicable_trajectory_score: float = Field(ge=0, le=1)
    p50_total_tokens: int = Field(ge=0)
    p95_latency_ms: int = Field(ge=0)
    judge_error_count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")

    def to_domain(self) -> ModelCandidateEvaluation:
        return ModelCandidateEvaluation(
            model=self.model,
            provider=self.provider,
            safety_pass_rate=self.safety_pass_rate,
            core_task_success_rate=self.core_task_success_rate,
            mean_response_score=self.mean_response_score,
            applicable_trajectory_score=self.applicable_trajectory_score,
            p50_total_tokens=self.p50_total_tokens,
            p95_latency_ms=self.p95_latency_ms,
            judge_error_count=self.judge_error_count,
        )


class ModelCandidatePromotionRequest(BaseModel):
    baseline: ModelCandidateEvaluationRequest
    candidate: ModelCandidateEvaluationRequest

    model_config = ConfigDict(extra="forbid")


class ModelCandidateSuitePromotionRequest(BaseModel):
    baseline: ModelCandidateEvaluationRequest
    candidates: list[ModelCandidateEvaluationRequest] = Field(min_length=1, max_length=20)
    sealed_holdout_passed: bool
    min_candidate_count: int = Field(default=1, ge=1, le=20)
    required_candidate_models: list[str] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")


class FyersOAuthCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str = Field(min_length=16, max_length=256)
    auth_code: str = Field(min_length=1, max_length=512)


class FyersRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_type: str = Field(default="account_snapshot", min_length=1, max_length=80)
    symbols: list[str] = Field(default_factory=lambda: ["INFY"])


class ResearchSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    normalized_symbol: str | None = Field(default=None, min_length=1, max_length=80)
    limit: int = Field(default=5, ge=1, le=20)


class ResearchRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_query_or_symbol: str = Field(min_length=1, max_length=500)


class SessionSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2_000)
    object_refs: list[dict[str, object]] = Field(default_factory=list)


class PaperFillRequest(BaseModel):
    fill_price: float | None = Field(default=None, gt=0)


class PaperPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str | None = Field(default=None, min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    status: str = Field(default="disabled", min_length=1, max_length=16)
    permitted_strategies: list[str] = Field(default_factory=list)
    permitted_symbols: list[str] = Field(default_factory=list)
    permitted_sides: list[str] = Field(default_factory=list)
    permitted_order_types: list[str] = Field(default_factory=list)
    max_orders: int | None = Field(default=None, gt=0)
    max_quantity_per_order: int | None = Field(default=None, gt=0)
    max_notional_per_order: float | None = Field(default=None, gt=0)
    max_gross_notional: float | None = Field(default=None, gt=0)
    max_net_notional: float | None = Field(default=None, gt=0)
    max_loss_limit: float | None = Field(default=None, gt=0)
    max_drawdown_limit: float | None = Field(default=None, gt=0)
    slippage_bps: int | None = Field(default=None, gt=0)
    quote_freshness_seconds: int | None = Field(default=None, gt=0)
    market_hours_only: bool = True
    self_approval_permitted: bool = False
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PaperBatchApiOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=32)
    side: str = Field(min_length=3, max_length=4)
    quantity: int = Field(ge=1, le=1_000_000)
    order_type: str = Field(min_length=5, max_length=6)
    limit_price: float | None = Field(default=None, gt=0)


class PaperBatchApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_request_id: str | None = Field(default=None, min_length=1, max_length=120)
    strategy_key: str = Field(min_length=1, max_length=120)
    orders: list[PaperBatchApiOrder] = Field(min_length=1, max_length=50)
    context_refs: list[dict[str, object]] = Field(default_factory=list)
    risk_summary: dict[str, object] = Field(default_factory=dict)


class PaperBatchApprovalApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1, max_length=120)
    expires_at: datetime


class PaperBatchRevokeApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_id: str = Field(min_length=1, max_length=120)


class PaperExecuteApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_id: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=1, max_length=160)
    quote_price: float = Field(gt=0)
    quote_as_of: datetime
    now: datetime | None = None
    available_cash: float | None = Field(default=None, ge=0)
    current_gross_notional: float = Field(default=0, ge=0)
    current_net_notional: float = 0
    kill_switch_active: bool = False


_PAPER_POLICIES: dict[tuple[str, str], PaperExecutionPolicyCeiling] = {}
_PAPER_BATCHES: dict[tuple[str, str], PaperBatchRequest] = {}
_PAPER_GRANTS: dict[tuple[str, str], PaperExecutionGrant] = {}
_PAPER_IDEMPOTENCY_KEYS: dict[str, set[str]] = {}
_FYERS_CONNECTIONS: dict[tuple[str, str], FyersConnection] = {}
_FYERS_OAUTH_STATES: dict[tuple[str, str], FyersOAuthSession] = {}
_FYERS_PKCE_VERIFIER_CACHE = InMemoryFyersPkceVerifierCache()
_FYERS_REDIS_PKCE_VERIFIER_CACHES: dict[str, RedisFyersPkceVerifierCache] = {}
_SESSION_MEMORY: dict[tuple[str, str, str], SessionMemoryRecord] = {}


def cloud_telemetry_enabled() -> bool:
    enabled = os.getenv("ENABLE_CLOUD_TELEMETRY", "").strip().lower()
    return enabled in {"1", "true", "yes", "y", "on"} and bool(
        os.getenv("GOOGLE_CLOUD_PROJECT")
    )


def env_flag_enabled(*names: str) -> bool:
    truthy_values = {"1", "true", "yes", "y", "on"}
    return any(os.getenv(name, "").strip().lower() in truthy_values for name in names)


def _model_route_kill_switch_active() -> bool:
    return env_flag_enabled(
        "MODEL_ROUTE_KILL_SWITCH",
        "PORTFOLIO_MODEL_ROUTE_KILL_SWITCH",
    )


def _reject_if_model_route_kill_switch_active() -> None:
    if _model_route_kill_switch_active():
        raise HTTPException(status_code=503, detail="model_route_kill_switch_active")


def _research_refresh_kill_switch_active() -> bool:
    return env_flag_enabled(
        "RESEARCH_REFRESH_KILL_SWITCH",
        "PORTFOLIO_RESEARCH_REFRESH_KILL_SWITCH",
    )


def _reject_if_research_refresh_kill_switch_active() -> None:
    if _research_refresh_kill_switch_active():
        raise HTTPException(status_code=503, detail="research_refresh_kill_switch_active")


def build_logger():
    if not cloud_telemetry_enabled():
        return LocalLogger()
    try:
        logging_client = google_cloud_logging.Client()
        return logging_client.logger(__name__)
    except Exception:
        logging.exception("Falling back to local logger.")
        return LocalLogger()


logger = build_logger()
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",")
    if os.getenv("ALLOW_ORIGINS")
    else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=cloud_telemetry_enabled(),
)
app.title = "agent-service"
app.description = "API for interacting with the Agent agent-service"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


def _configured_available_model_ids() -> set[str] | None:
    raw_value = os.getenv("OLLAMA_AVAILABLE_MODELS")
    if not raw_value:
        return None
    return {
        model.strip()
        for model in raw_value.split(",")
        if model.strip()
    }


def _configured_available_model_digests() -> dict[str, str] | None:
    raw_value = os.getenv("OLLAMA_AVAILABLE_MODEL_DIGESTS")
    if not raw_value:
        return None
    digests: dict[str, str] = {}
    for item in raw_value.split(","):
        model, separator, digest = item.partition("=")
        if separator and model.strip() and digest.strip():
            digests[model.strip()] = digest.strip()
    return digests or None


def _positive_float(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _probe_ollama_inventory(
    base_url: str | None,
) -> dict[str, OllamaModelMetadata] | None:
    if not base_url:
        return None
    timeout = _positive_float(os.getenv("OLLAMA_STATUS_TIMEOUT_SECONDS"), 1.5)
    try:
        tags_url = urljoin(base_url.rstrip("/") + "/", "api/tags")
        with urlopen(tags_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, Mapping):
        return None
    return parse_ollama_tags_response(payload)


def _ollama_inventory(
    profile_provider: ModelProvider,
    base_url: str | None,
) -> tuple[str, set[str] | None, dict[str, str] | None, list[dict[str, object]]]:
    configured_ids = _configured_available_model_ids()
    configured_digests = _configured_available_model_digests()
    if configured_ids is not None or configured_digests is not None:
        return (
            "env",
            configured_ids
            if configured_ids is not None
            else set(configured_digests or {}),
            configured_digests,
            [],
        )
    if profile_provider != ModelProvider.OLLAMA:
        return ("not_applicable", None, None, [])
    inventory = _probe_ollama_inventory(base_url)
    if inventory is None:
        return ("unavailable", None, None, [])
    return (
        "ollama_api",
        set(inventory),
        {name: item.digest for name, item in inventory.items() if item.digest},
        [item.to_dict() for item in inventory.values()],
    )


@app.get("/v1/research/sources")
def get_research_sources(
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """List admin-registered allowlisted research sources without URLs."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    return {
        "status": "success",
        "source_policy": "admin_allowlist_only",
        "sources": [source.to_dict() for source in BUILTIN_RESEARCH_SOURCES],
    }


@app.post("/v1/research/search")
def post_research_search(
    request: ResearchSearchRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Search curated research through fixture or tenant-scoped Postgres stores."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    try:
        query = normalize_research_query(request.query)
        normalized_symbol = (
            normalize_research_query(request.normalized_symbol)
            if request.normalized_symbol
            else None
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="research_query_invalid") from exc

    store = _research_store(actor)
    try:
        if isinstance(store, PostgresResearchStore):
            hits = store.search(
                query,
                normalized_symbol=normalized_symbol,
                limit=request.limit,
            )
            retrieval = {
                "mode": "postgres_runtime",
                "backend": "postgres_full_text",
                "vector_retrieval": "disabled",
                "source_policy": "admin_allowlist_only",
            }
        else:
            hits = store.search(query, limit=request.limit)
            retrieval = {
                "mode": "file_backed_fixture",
                "backend": "lexical",
                "vector_retrieval": "disabled",
                "source_policy": "admin_allowlist_only",
            }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="research_store_unavailable") from exc

    return {
        "status": "success",
        "query": query,
        "normalized_symbol": normalized_symbol,
        "retrieval": retrieval,
        "hits": [hit.to_dict() for hit in hits],
    }


@app.post("/v1/research/refresh/{source_id}")
def post_research_refresh(
    source_id: str,
    request: ResearchRefreshRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Queue a refresh intent by registered source id and normalized query only."""
    _require_any_role(actor, {"analyst", "admin"})
    _reject_if_research_refresh_kill_switch_active()
    source = _research_source_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="research_source_not_registered")
    try:
        normalized_query_or_symbol = normalize_research_query(
            request.normalized_query_or_symbol
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="research_query_invalid") from exc
    job_id = "research-refresh-" + sha256(
        (
            f"{actor.tenant_id}:{actor.audit_actor}:"
            f"{source.source_id}:{normalized_query_or_symbol}"
        ).encode()
    ).hexdigest()[:16]
    return {
        "status": "queued",
        "job_id": job_id,
        "source": source.to_dict(),
        "normalized_query_or_symbol": normalized_query_or_symbol,
        "mode": "admin_allowlist_only",
        "refresh_policy": source.refresh_policy,
        "requested_by": actor.audit_actor,
    }


@app.get("/v1/models/ollama/status")
def get_ollama_model_status() -> dict:
    """Return redacted model runtime readiness and route-budget status."""
    profile = load_model_runtime_profile(os.environ)
    kill_switch_active = _model_route_kill_switch_active()
    inventory_source, available_model_ids, available_model_digests, inventory = (
        _ollama_inventory(
            profile.provider,
            profile.base_url,
        )
    )
    report = build_model_capability_report(
        profile,
        available_model_ids=available_model_ids,
        available_model_digests=available_model_digests,
        env=os.environ,
    )
    blocking_reasons = list(report.blocking_reasons)
    if kill_switch_active and "model_route_kill_switch_active" not in blocking_reasons:
        blocking_reasons.append("model_route_kill_switch_active")
    startup_allowed = report.startup_allowed and not kill_switch_active
    return {
        "status": "ready" if startup_allowed else "blocked",
        "provider": profile.provider.value,
        "local": profile.local,
        "model": profile.model,
        "base_url": profile.base_url,
        "model_digest_pinned": bool(profile.model_digest),
        "context_window_tokens": profile.context_window_tokens,
        "max_request_input_tokens": profile.max_request_input_tokens,
        "queue": {
            "max_active_requests": profile.queue_max_active_requests,
            "max_depth": profile.queue_max_depth,
        },
        "route_budgets": {
            route: {
                "configured_input_tokens": budget.configured_input_tokens,
                "effective_input_tokens": budget.effective_input_tokens,
                "output_tokens": budget.output_tokens,
                "tool_call_budget": budget.tool_call_budget,
            }
            for route, budget in sorted(profile.route_budgets.items())
        },
        "required_capabilities": report.required_capabilities,
        "startup_allowed": startup_allowed,
        "blocking_reasons": blocking_reasons,
        "model_route_kill_switch_active": kill_switch_active,
        "model_available": report.model_available,
        "model_digest_verified": report.model_digest_verified,
        "model_inventory_source": inventory_source,
        "model_inventory": inventory,
        "applies_to_active_provider": profile.provider == ModelProvider.OLLAMA,
    }


@app.get("/v1/models/tuning/status")
def get_model_tuning_status() -> dict:
    """Return provider-neutral model tuning plan and promotion gates."""
    profile = load_model_runtime_profile(os.environ)
    plan = build_model_tuning_plan(os.environ)
    kill_switch_active = _model_route_kill_switch_active()
    return {
        "status": "blocked" if kill_switch_active else "ready",
        "active_provider": profile.provider.value,
        "active_model": profile.model,
        "provider_neutral": True,
        "model_route_kill_switch_active": kill_switch_active,
        "blocking_reasons": (
            ["model_route_kill_switch_active"] if kill_switch_active else []
        ),
        "primary_candidate_model": plan.primary_candidate_model,
        "candidate_models": list(plan.candidate_models),
        "dev_set": plan.dev_set,
        "holdout_set": plan.holdout_set,
        "initial_tuning_mode": plan.initial_tuning_mode,
        "fine_tuning": {
            "enabled": plan.fine_tuning_enabled,
            "min_labeled_examples": plan.fine_tuning_min_labeled_examples,
            "required_prompt_routing_retrieval_iterations": (
                plan.required_prompt_routing_retrieval_iterations
            ),
        },
        "promotion_gate": {
            "safety_pass_rate": 1.0,
            "core_task_success_rate": 0.95,
            "mean_response_score": 4.0,
            "applicable_trajectory_score": 1.0,
            "judge_error_count": 0,
            "max_p50_token_ratio_to_baseline": 1.10,
            "max_p95_latency_ratio_to_baseline": 1.20,
        },
    }


@app.post("/v1/models/tuning/evaluate-candidate")
def evaluate_model_tuning_candidate(payload: dict) -> dict:
    """Evaluate aggregate model metrics against provider-neutral promotion gates."""
    _reject_sensitive_model_tuning_payload(payload)
    _reject_if_model_route_kill_switch_active()
    try:
        request = ModelCandidatePromotionRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="model_candidate_evaluation_invalid",
        ) from exc

    plan = build_model_tuning_plan(os.environ)
    if request.candidate.model not in plan.candidate_models:
        raise HTTPException(status_code=400, detail="model_candidate_not_allowed")

    decision = evaluate_model_candidate_for_tuning(
        request.candidate.to_domain(),
        baseline=request.baseline.to_domain(),
    )
    return {
        "status": "evaluated",
        "provider_neutral": True,
        "candidate_allowed": True,
        "primary_candidate_model": plan.primary_candidate_model,
        "candidate_models": list(plan.candidate_models),
        "dev_set": plan.dev_set,
        "holdout_set": plan.holdout_set,
        "initial_tuning_mode": plan.initial_tuning_mode,
        "fine_tuning": {
            "enabled": plan.fine_tuning_enabled,
            "min_labeled_examples": plan.fine_tuning_min_labeled_examples,
            "required_prompt_routing_retrieval_iterations": (
                plan.required_prompt_routing_retrieval_iterations
            ),
        },
        "promotion_gate": {
            "safety_pass_rate": 1.0,
            "core_task_success_rate": 0.95,
            "mean_response_score": 4.0,
            "applicable_trajectory_score": 1.0,
            "judge_error_count": 0,
            "max_p50_token_ratio_to_baseline": 1.10,
            "max_p95_latency_ratio_to_baseline": 1.20,
        },
        "decision": decision.to_dict(),
    }


@app.post("/v1/models/tuning/evaluate-suite")
def evaluate_model_tuning_candidate_suite(payload: dict) -> dict:
    """Evaluate a provider-neutral model candidate suite against release gates."""
    _reject_sensitive_model_tuning_payload(payload)
    _reject_if_model_route_kill_switch_active()
    try:
        request = ModelCandidateSuitePromotionRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="model_candidate_suite_evaluation_invalid",
        ) from exc

    plan = build_model_tuning_plan(os.environ)
    allowed_models = set(plan.candidate_models)
    if any(candidate.model not in allowed_models for candidate in request.candidates):
        raise HTTPException(status_code=400, detail="model_candidate_not_allowed")

    decision = evaluate_model_candidate_suite_for_tuning(
        [candidate.to_domain() for candidate in request.candidates],
        baseline=request.baseline.to_domain(),
        sealed_holdout_passed=request.sealed_holdout_passed,
        min_candidate_count=request.min_candidate_count,
        required_candidate_models=tuple(request.required_candidate_models),
    )
    return {
        "status": "evaluated",
        "provider_neutral": True,
        "candidate_allowed": True,
        "primary_candidate_model": plan.primary_candidate_model,
        "candidate_models": list(plan.candidate_models),
        "dev_set": plan.dev_set,
        "holdout_set": plan.holdout_set,
        "initial_tuning_mode": plan.initial_tuning_mode,
        "fine_tuning": {
            "enabled": plan.fine_tuning_enabled,
            "min_labeled_examples": plan.fine_tuning_min_labeled_examples,
            "required_prompt_routing_retrieval_iterations": (
                plan.required_prompt_routing_retrieval_iterations
            ),
        },
        "promotion_gate": {
            "safety_pass_rate": 1.0,
            "core_task_success_rate": 0.95,
            "mean_response_score": 4.0,
            "applicable_trajectory_score": 1.0,
            "judge_error_count": 0,
            "max_p50_token_ratio_to_baseline": 1.10,
            "max_p95_latency_ratio_to_baseline": 1.20,
        },
        "decision": decision.to_dict(),
    }


def optional_actor_context_dependency(
    x_actor_sub: str | None = Header(default=None, alias="X-Actor-Sub"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_actor_roles: str | None = Header(default=None, alias="X-Actor-Roles"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> ActorContext | None:
    if not any((x_actor_sub, x_tenant_id, x_actor_roles, x_request_id)):
        return None
    return build_actor_context(
        x_actor_sub=x_actor_sub,
        x_tenant_id=x_tenant_id,
        x_actor_roles=x_actor_roles,
        x_request_id=x_request_id,
    )


@app.post("/v1/models/usage/events")
def record_model_usage_event(
    request: ModelUsageEventRequest,
    actor: Annotated[
        ActorContext | None,
        Depends(optional_actor_context_dependency),
    ],
) -> dict:
    """Record redacted model usage metrics and evaluate route budgets."""
    payload = request.model_dump()
    _reject_sensitive_model_usage_payload(payload)
    profile = load_model_runtime_profile(os.environ)
    event = ModelUsageEvent(
        provider=request.provider,
        model=request.model,
        route=request.route,
        prompt_tokens=request.prompt_tokens,
        output_tokens=request.output_tokens,
        tool_calls=request.tool_calls,
        queue_wait_ms=request.queue_wait_ms,
        latency_ms=request.latency_ms,
        retries=request.retries,
        request_id=request.request_id,
    )
    decision = evaluate_model_usage_event(profile, event)
    store = _model_usage_store(actor)
    if store is not None:
        store.record(event, decision)
        stored_event_count = len(store.list_recent(limit=_model_usage_event_limit(profile)))
    else:
        events = _model_usage_events()
        events.append(event)
        max_events = _model_usage_event_limit(profile)
        if len(events) > max_events:
            del events[: len(events) - max_events]
        stored_event_count = len(events)
    return {
        "status": "recorded",
        "budget_decision": decision.to_dict(),
        "stored_event_count": stored_event_count,
    }


@app.get("/v1/models/usage/summary")
def get_model_usage_summary(
    actor: Annotated[
        ActorContext | None,
        Depends(optional_actor_context_dependency),
    ],
) -> dict:
    """Return aggregate model usage metrics without prompts or responses."""
    profile = load_model_runtime_profile(os.environ)
    store = _model_usage_store(actor)
    events = (
        store.list_recent(limit=_model_usage_event_limit(profile))
        if store is not None
        else tuple(_model_usage_events())
    )
    summary = summarize_model_usage_events(profile, events)
    budget_violations: dict[str, int] = {}
    for event in events:
        decision = evaluate_model_usage_event(profile, event)
        if not decision.allowed:
            budget_violations[event.route] = budget_violations.get(event.route, 0) + 1
    return {
        "status": "ready",
        "summary": summary.to_dict(),
        "budget_violations": budget_violations,
        "stored_event_count": len(events),
    }


@app.put("/v1/sessions/{session_id}/summary")
def upsert_session_summary(
    session_id: str,
    request: SessionSummaryRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Persist compact session memory with tenant/user isolation and TTLs."""
    try:
        record = _store_session_summary(
            actor,
            session_id=session_id,
            summary=request.summary,
            object_refs=request.object_refs,
        )
    except (SessionMemoryValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="session_memory_invalid") from exc
    return {
        "status": "saved",
        "memory": _session_memory_response(record),
    }


@app.get("/v1/sessions/{session_id}/summary")
def get_session_summary(
    session_id: str,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Return compact, unexpired session memory for the authenticated actor."""
    record = _get_session_summary(actor, session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="session_memory_not_found")
    return {
        "status": "ready",
        "memory": _session_memory_response(record),
    }


@app.delete("/v1/sessions/{session_id}/summary")
def delete_session_summary(
    session_id: str,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Immediately delete compact session memory for the authenticated actor."""
    _delete_session_summary(actor, session_id=session_id)
    return {
        "status": "deleted",
        "session_id": session_id,
    }


@app.get("/v1/storage/status")
def get_storage_status(require_production_like: bool = False) -> dict:
    """Return redacted storage runtime and migration-readiness status."""
    profile = load_database_runtime_profile(os.environ)
    readiness = evaluate_database_runtime_readiness(
        profile,
        require_production_like=require_production_like,
    )
    return {
        "status": "ready" if readiness.ready else "blocked",
        "profile": profile.to_dict(),
        "readiness": readiness.to_dict(),
    }


@app.get("/v1/credentials/vault/status")
def get_credential_vault_status(
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Return redacted credential-vault readiness for protected integrations."""
    _require_any_role(actor, {"admin"})
    profile = load_credential_vault_profile(os.environ)
    readiness = evaluate_credential_vault_readiness(profile)
    return {
        "status": "ready" if readiness.ready else "blocked",
        "profile": profile.to_dict(),
        "readiness": readiness.to_dict(),
    }


@app.post("/v1/integrations/fyers/oauth/start")
def post_fyers_oauth_start(
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Start a protected FYERS data-only OAuth flow without exposing secrets."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    connection = _get_or_create_fyers_connection(actor)
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = _pkce_challenge(code_verifier)
    session = FyersOAuthSession.create(
        tenant_id=actor.tenant_id,
        connection_id=connection.connection_id,
        state=state,
        code_challenge=code_challenge,
    )
    connection = connection.oauth_started(expires_at=session.expires_at)
    _store_fyers_connection(actor, connection)
    _store_fyers_oauth_session(actor, session)
    _store_fyers_pkce_verifier(session=session, code_verifier=code_verifier)
    return {
        "status": "authorization_required",
        "connection": connection.to_dict(),
        "oauth": {
            "authorize_url": _fyers_authorize_url(
                state=state,
                code_challenge=code_challenge,
            ),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "expires_at": session.expires_at.isoformat(),
            "daily_auth_required": True,
        },
        "mode": "human_api_only",
    }


@app.post("/v1/integrations/fyers/oauth/callback")
def post_fyers_oauth_callback(
    request: FyersOAuthCallbackRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Record a FYERS OAuth callback without accepting provider tokens."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    session = _pop_fyers_oauth_session(actor, request.state)
    if session is None:
        raise HTTPException(status_code=409, detail="fyers_oauth_state_unknown_or_expired")
    if _pop_fyers_pkce_verifier(actor=actor, session=session) is None:
        raise HTTPException(
            status_code=409,
            detail="fyers_oauth_verifier_unknown_or_expired",
        )
    connection = _get_or_create_fyers_connection(actor).callback_recorded()
    _store_fyers_connection(actor, connection)
    credential_vault = _credential_vault_readiness_payload()
    return {
        "status": "reconnect_required",
        "connection": connection.to_dict(),
        "credential_vault": credential_vault,
        "next_step": "configure_credential_vault_token_exchange",
        "mode": "human_api_only",
    }


@app.get("/v1/integrations/fyers/oauth/status")
def get_fyers_oauth_status(
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Return redacted FYERS connection status for the authenticated actor."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    connection = _get_or_create_fyers_connection(actor)
    return {
        "status": "success",
        "connection": connection.to_dict(),
        "health": get_fyers_readonly_connector().connection_health().to_dict(),
        "mode": "human_api_only",
    }


@app.post("/v1/integrations/fyers/oauth/disconnect")
def post_fyers_oauth_disconnect(
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Disconnect FYERS read-only connection state without broker mutation."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    connection = _get_or_create_fyers_connection(actor).disconnected_copy()
    _store_fyers_connection(actor, connection)
    _clear_fyers_oauth_sessions(actor)
    return {
        "status": "success",
        "connection": connection.to_dict(),
        "mode": "human_api_only",
    }


@app.post("/v1/integrations/fyers/refresh")
@app.post("/v1/integrations/fyers/oauth/refresh")
def post_fyers_refresh(
    request: FyersRefreshRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Run a protected read-only FYERS fixture refresh without live broker calls."""
    _require_any_role(actor, {"viewer", "analyst", "admin"})
    _reject_sensitive_fyers_payload(request.model_dump())
    if _fyers_connector_kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail="fyers_connector_kill_switch_active",
        )
    connector = get_fyers_readonly_connector()
    job = ProviderRefreshJob.created(
        tenant_id=actor.tenant_id,
        requested_by_actor_id=actor.audit_actor,
        refresh_type=request.refresh_type,
    )
    snapshots: list[dict[str, object]] = []
    snapshot_envelopes: list[ProviderSnapshotEnvelope] = []
    errors: list[str] = []
    for symbol in request.symbols[:20]:
        try:
            envelope = connector.get_quote_envelope(symbol)
            snapshot_envelopes.append(envelope)
            snapshots.append(envelope.to_dict())
        except ValueError as exc:
            errors.append(str(exc))
    account_snapshot = connector.get_account_snapshot()
    job = job.completed(
        snapshot_count=len(snapshots) + 1,
        errors=tuple(errors),
    )
    connection = _get_or_create_fyers_connection(actor)
    _store_fyers_refresh_result(
        actor=actor,
        job=job,
        connection=connection,
        snapshots=tuple(snapshot_envelopes),
        account_snapshot=account_snapshot,
    )
    return {
        "status": "success",
        "job": job.to_dict(),
        "connection": connection.to_dict(),
        "snapshots": snapshots,
        "account_snapshot": account_snapshot.to_dict(),
        "mode": "read_only",
        "source_policy": "fyers_readonly_fixture_no_fallback",
    }


def _require_any_role(actor: ActorContext, allowed_roles: set[str]) -> None:
    if not actor.roles & allowed_roles:
        raise HTTPException(status_code=403, detail="role_required")


def _credential_vault_readiness_payload() -> dict:
    readiness = evaluate_credential_vault_readiness(
        load_credential_vault_profile(os.environ),
    )
    return readiness.to_dict()


def _fyers_connector_kill_switch_active() -> bool:
    return env_flag_enabled(
        "FYERS_CONNECTOR_KILL_SWITCH",
        "PORTFOLIO_FYERS_CONNECTOR_KILL_SWITCH",
    )


def _reject_sensitive_paper_payload(payload: object) -> None:
    lowered = str(payload).lower()
    forbidden = (
        "access_token",
        "refresh_token",
        "api_key",
        "authorization:",
        "bearer ",
        "password",
        "secret",
        "fyers",
        "trading_token",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise HTTPException(status_code=400, detail="paper_payload_contains_sensitive_data")


def _reject_sensitive_model_usage_payload(payload: object) -> None:
    lowered = str(payload).lower()
    forbidden = (
        "raw_prompt",
        "raw_response",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization:",
        "bearer ",
        "password",
        "secret",
        "trading_token",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise HTTPException(status_code=400, detail="model_usage_contains_sensitive_data")


def _reject_sensitive_model_tuning_payload(payload: object) -> None:
    lowered = str(payload).lower()
    forbidden = (
        "raw_prompt",
        "raw_response",
        "messages",
        "transcript",
        "access_token",
        "refresh_token",
        "api_key",
        "authorization:",
        "bearer ",
        "password",
        "secret",
        "trading_token",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise HTTPException(status_code=400, detail="model_tuning_contains_sensitive_data")


def _reject_sensitive_fyers_payload(payload: object) -> None:
    lowered = str(payload).lower()
    forbidden = (
        "access_token",
        "refresh_token",
        "client_secret",
        "api_key",
        "authorization:",
        "bearer ",
        "password",
        "secret",
        "trading_token",
        "place_order",
        "modify_order",
        "cancel_order",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise HTTPException(status_code=400, detail="fyers_payload_contains_sensitive_data")


def _fyers_connection_key(actor: ActorContext) -> tuple[str, str]:
    return (actor.tenant_id, actor.audit_actor)


def _fyers_user_hash(actor: ActorContext) -> str:
    return actor_hash(tenant_id=actor.tenant_id, user_id=actor.audit_actor)


def _research_source_by_id(source_id: str):
    return next(
        (source for source in BUILTIN_RESEARCH_SOURCES if source.source_id == source_id),
        None,
    )


def _research_store(actor: ActorContext) -> FileBackedResearchStore | PostgresResearchStore:
    backend = os.getenv("PORTFOLIO_RESEARCH_STORE_BACKEND", "fixture").strip().lower()
    if backend == "postgres":
        database_url = os.getenv("PORTFOLIO_DATABASE_URL", "").strip()
        if not database_url:
            raise HTTPException(status_code=503, detail="research_postgres_not_configured")
        return _build_postgres_research_store(
            tenant_id=actor.tenant_id,
            database_url=database_url,
        )
    return FileBackedResearchStore.from_pattern_cards(PATTERN_CARDS)


def _build_postgres_research_store(
    *,
    tenant_id: str,
    database_url: str,
) -> PostgresResearchStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(connection_url, row_factory=dict_row)
        connection.execute("SET app.tenant_id = %s", (tenant_id,))
        return connection

    return PostgresResearchStore(
        tenant_id=tenant_id,
        connection_factory=connection_factory,
    )


def _fyers_integration_store(
    actor: ActorContext,
) -> PostgresFyersIntegrationStore | None:
    profile = load_database_runtime_profile(os.environ)
    if profile.backend != DatabaseBackend.POSTGRES:
        return None
    if not profile.database_url:
        raise HTTPException(status_code=503, detail="fyers_postgres_not_configured")
    return _build_postgres_fyers_integration_store(
        tenant_id=actor.tenant_id,
        database_url=profile.database_url,
    )


def _build_postgres_fyers_integration_store(
    *,
    tenant_id: str,
    database_url: str,
) -> PostgresFyersIntegrationStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(connection_url, row_factory=dict_row)
        connection.execute("SET app.tenant_id = %s", (tenant_id,))
        return connection

    return PostgresFyersIntegrationStore(
        tenant_id=tenant_id,
        connection_factory=connection_factory,
    )


def _fyers_pkce_verifier_cache():
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return _FYERS_PKCE_VERIFIER_CACHE
    cache = _FYERS_REDIS_PKCE_VERIFIER_CACHES.get(redis_url)
    if cache is None:
        from redis import Redis

        cache = RedisFyersPkceVerifierCache(redis_client=Redis.from_url(redis_url))
        _FYERS_REDIS_PKCE_VERIFIER_CACHES[redis_url] = cache
    return cache


def _store_fyers_pkce_verifier(
    *,
    session: FyersOAuthSession,
    code_verifier: str,
) -> None:
    _fyers_pkce_verifier_cache().store(
        session=session,
        code_verifier=code_verifier,
    )


def _pop_fyers_pkce_verifier(
    *,
    actor: ActorContext,
    session: FyersOAuthSession,
) -> str | None:
    return _fyers_pkce_verifier_cache().pop(
        tenant_id=actor.tenant_id,
        connection_id=session.connection_id,
        state_hash=session.state_hash,
    )


def _clear_fyers_pkce_verifiers(
    actor: ActorContext,
    *,
    connection_id: str,
) -> None:
    _fyers_pkce_verifier_cache().clear_connection(
        tenant_id=actor.tenant_id,
        connection_id=connection_id,
    )


def _get_or_create_fyers_connection(actor: ActorContext) -> FyersConnection:
    store = _fyers_integration_store(actor)
    if store is not None:
        connection = store.get_connection(user_id_hash=_fyers_user_hash(actor))
        if connection is not None:
            return connection
        connection = FyersConnection.disconnected(
            tenant_id=actor.tenant_id,
            user_id=actor.audit_actor,
            connection_id=str(uuid4()),
        )
        return store.upsert_connection(connection)

    key = _fyers_connection_key(actor)
    connection = _FYERS_CONNECTIONS.get(key)
    if connection is not None:
        return connection
    connection = FyersConnection.disconnected(
        tenant_id=actor.tenant_id,
        user_id=actor.audit_actor,
        connection_id=str(uuid4()),
    )
    _FYERS_CONNECTIONS[key] = connection
    return connection


def _store_fyers_connection(
    actor: ActorContext,
    connection: FyersConnection,
) -> FyersConnection:
    store = _fyers_integration_store(actor)
    if store is not None:
        return store.upsert_connection(connection)
    _FYERS_CONNECTIONS[_fyers_connection_key(actor)] = connection
    return connection


def _store_fyers_oauth_session(
    actor: ActorContext,
    session: FyersOAuthSession,
) -> FyersOAuthSession:
    store = _fyers_integration_store(actor)
    if store is not None:
        return store.upsert_oauth_session(session)
    _FYERS_OAUTH_STATES[(actor.tenant_id, session.state_hash)] = session
    return session


def _pop_fyers_oauth_session(
    actor: ActorContext,
    state: str,
) -> FyersOAuthSession | None:
    connection = _get_or_create_fyers_connection(actor)
    store = _fyers_integration_store(actor)
    if store is not None:
        session = store.pop_oauth_session(
            state_hash=hash_oauth_state(state),
            connection_id=connection.connection_id,
        )
        if session is None or not session.active():
            return None
        return session

    key = (actor.tenant_id, hash_oauth_state(state))
    session = _FYERS_OAUTH_STATES.get(key)
    if (
        session is None
        or not session.active()
        or session.connection_id != connection.connection_id
    ):
        return None
    del _FYERS_OAUTH_STATES[key]
    return session


def _clear_fyers_oauth_sessions(actor: ActorContext) -> None:
    connection = _get_or_create_fyers_connection(actor)
    _clear_fyers_pkce_verifiers(actor, connection_id=connection.connection_id)
    store = _fyers_integration_store(actor)
    if store is not None:
        store.clear_oauth_sessions(connection_id=connection.connection_id)
        return
    for key in tuple(_FYERS_OAUTH_STATES):
        session = _FYERS_OAUTH_STATES[key]
        if (
            session.tenant_id == actor.tenant_id
            and session.connection_id == connection.connection_id
        ):
            del _FYERS_OAUTH_STATES[key]


def _store_fyers_refresh_result(
    *,
    actor: ActorContext,
    job: ProviderRefreshJob,
    connection: FyersConnection,
    snapshots: tuple[ProviderSnapshotEnvelope, ...],
    account_snapshot: BrokerAccountSnapshot,
) -> None:
    store = _fyers_integration_store(actor)
    if store is None:
        return
    store.record_refresh_result(
        job=job,
        connection_id=connection.connection_id,
        snapshots=snapshots,
        account_snapshot=account_snapshot,
    )


def _pkce_challenge(code_verifier: str) -> str:
    digest = sha256(code_verifier.encode("utf-8")).digest()
    return urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _fyers_authorize_url(*, state: str, code_challenge: str) -> str:
    base_url = os.getenv(
        "FYERS_AUTHORIZE_URL",
        "https://api-t1.fyers.in/api/v3/generate-authcode",
    )
    params = {
        "client_id": os.getenv("FYERS_CLIENT_ID", "configure-fyers-data-app"),
        "redirect_uri": os.getenv(
            "FYERS_REDIRECT_URI",
            "http://localhost:8000/v1/integrations/fyers/oauth/callback",
        ),
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{base_url}?{urlencode(params)}"


def _model_usage_events() -> list[ModelUsageEvent]:
    events = getattr(app.state, "model_usage_events", None)
    if not isinstance(events, list):
        events = []
        app.state.model_usage_events = events
    return events


def _model_usage_event_limit(profile) -> int:
    return max(profile.queue_max_depth * 10, 100)


def _model_usage_store(actor: ActorContext | None = None) -> PostgresModelUsageStore | None:
    profile = load_database_runtime_profile(os.environ)
    if profile.backend != DatabaseBackend.POSTGRES:
        return None
    if not profile.database_url:
        raise HTTPException(status_code=503, detail="model_usage_postgres_not_configured")
    if actor is None:
        raise HTTPException(status_code=401, detail="actor_context_required")
    return _build_postgres_model_usage_store(
        tenant_id=actor.tenant_id,
        database_url=profile.database_url,
    )


def _build_postgres_model_usage_store(
    *,
    tenant_id: str,
    database_url: str,
) -> PostgresModelUsageStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg

        connection = psycopg.connect(connection_url)
        connection.execute("SET app.tenant_id = %s", (tenant_id,))
        return connection

    return PostgresModelUsageStore(
        tenant_id=tenant_id,
        connection_factory=connection_factory,
    )


def _session_key(actor: ActorContext, session_id: str) -> tuple[str, str, str]:
    return (actor.tenant_id, actor.user_id, session_id)


def _session_memory_store_for_actor(
    actor: ActorContext,
) -> PostgresSessionMemoryStore | None:
    profile = load_database_runtime_profile(os.environ)
    if profile.backend != DatabaseBackend.POSTGRES:
        return None
    if not profile.database_url:
        raise HTTPException(status_code=503, detail="session_memory_postgres_not_configured")
    return _build_postgres_session_memory_store(
        tenant_id=actor.tenant_id,
        actor_identity_id=_postgres_actor_identity_id(
            actor,
            database_url=profile.database_url,
        ),
        database_url=profile.database_url,
    )


def _postgres_actor_identity_id(actor: ActorContext, *, database_url: str) -> str:
    store = _build_postgres_actor_identity_store(database_url=database_url)
    return store.upsert_identity(
        issuer=actor.issuer,
        subject=actor.user_id,
    ).actor_identity_id


def _build_postgres_actor_identity_store(
    *,
    database_url: str,
) -> PostgresActorIdentityStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(connection_url, row_factory=dict_row)

    return PostgresActorIdentityStore(connection_factory=connection_factory)


def _build_postgres_session_memory_store(
    *,
    tenant_id: str,
    actor_identity_id: str,
    database_url: str,
) -> PostgresSessionMemoryStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg
        from psycopg.rows import dict_row

        connection = psycopg.connect(connection_url, row_factory=dict_row)
        connection.execute("SET app.tenant_id = %s", (tenant_id,))
        return connection

    return PostgresSessionMemoryStore(
        tenant_id=tenant_id,
        actor_identity_id=actor_identity_id,
        connection_factory=connection_factory,
    )


def _store_session_summary(
    actor: ActorContext,
    *,
    session_id: str,
    summary: str,
    object_refs: list[dict[str, object]],
) -> SessionMemoryRecord:
    store = _session_memory_store_for_actor(actor)
    if store is not None:
        return store.upsert_summary(
            session_id=session_id,
            request_id=actor.request_id,
            summary=summary,
            object_refs=object_refs,
        )

    policy = SessionMemoryPolicy.default()
    payload = sanitize_session_memory_payload(
        summary=summary,
        object_refs=object_refs,
        policy=policy,
    )
    current_time = datetime.now(UTC)
    existing = _SESSION_MEMORY.get(_session_key(actor, session_id))
    record = SessionMemoryRecord(
        session_id=session_id,
        tenant_id=actor.tenant_id,
        actor_identity_id=actor.user_id,
        request_id=actor.request_id,
        summary=payload.summary,
        object_refs=payload.object_refs,
        idle_expires_at=current_time + policy.idle_ttl,
        absolute_expires_at=current_time + policy.absolute_ttl,
        deleted_at=None,
        created_at=existing.created_at if existing is not None else current_time,
        updated_at=current_time,
    )
    _SESSION_MEMORY[_session_key(actor, session_id)] = record
    return record


def _get_session_summary(
    actor: ActorContext,
    *,
    session_id: str,
) -> SessionMemoryRecord | None:
    store = _session_memory_store_for_actor(actor)
    if store is not None:
        return store.get(session_id)

    record = _SESSION_MEMORY.get(_session_key(actor, session_id))
    if record is None:
        return None
    current_time = datetime.now(UTC)
    if (
        record.deleted_at is not None
        or record.idle_expires_at <= current_time
        or record.absolute_expires_at <= current_time
    ):
        return None
    return record


def _delete_session_summary(
    actor: ActorContext,
    *,
    session_id: str,
) -> None:
    store = _session_memory_store_for_actor(actor)
    if store is not None:
        store.delete(session_id)
        return
    _SESSION_MEMORY.pop(_session_key(actor, session_id), None)


def _session_memory_response(record: SessionMemoryRecord) -> dict:
    return {
        "session_id": record.session_id,
        "request_id": record.request_id,
        "summary": record.summary,
        "object_refs": [dict(ref) for ref in record.object_refs],
        "idle_expires_at": record.idle_expires_at.isoformat(),
        "absolute_expires_at": record.absolute_expires_at.isoformat(),
        "deleted_at": record.deleted_at.isoformat() if record.deleted_at else None,
    }


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _policy_key(actor: ActorContext, policy_id: str) -> tuple[str, str]:
    return (actor.tenant_id, policy_id)


def _batch_key(actor: ActorContext, batch_id: str) -> tuple[str, str]:
    return (actor.tenant_id, batch_id)


def _grant_key(actor: ActorContext, grant_id: str) -> tuple[str, str]:
    return (actor.tenant_id, grant_id)


def _paper_execution_store_for_actor(
    actor: ActorContext,
) -> PostgresPaperExecutionStore | None:
    profile = load_database_runtime_profile(os.environ)
    if profile.backend != DatabaseBackend.POSTGRES:
        return None
    if not profile.database_url:
        raise HTTPException(status_code=503, detail="paper_postgres_not_configured")
    return _build_postgres_paper_execution_store(
        tenant_id=actor.tenant_id,
        database_url=profile.database_url,
    )


def _paper_storage_actor_reference(actor: ActorContext) -> str:
    profile = load_database_runtime_profile(os.environ)
    if profile.backend != DatabaseBackend.POSTGRES:
        return actor.audit_actor
    if not profile.database_url:
        raise HTTPException(status_code=503, detail="paper_postgres_not_configured")
    return _postgres_actor_identity_id(actor, database_url=profile.database_url)


def _build_postgres_paper_execution_store(
    *,
    tenant_id: str,
    database_url: str,
) -> PostgresPaperExecutionStore:
    connection_url = _psycopg_database_url(database_url)

    def connection_factory():
        import psycopg

        return psycopg.connect(connection_url)

    return PostgresPaperExecutionStore(
        tenant_id=tenant_id,
        connection_factory=connection_factory,
    )


def _psycopg_database_url(database_url: str) -> str:
    stripped = database_url.strip()
    if stripped.startswith("postgresql+psycopg://"):
        return "postgresql://" + stripped.removeprefix("postgresql+psycopg://")
    return stripped


def _store_paper_policy(
    actor: ActorContext,
    policy: PaperExecutionPolicyCeiling,
) -> PaperExecutionPolicyCeiling:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.upsert_policy_ceiling(
            replace(policy, created_by_actor_id=_paper_storage_actor_reference(actor))
        )
    _PAPER_POLICIES[_policy_key(actor, policy.policy_id)] = policy
    return policy


def _get_paper_policy(
    actor: ActorContext,
    policy_id: str,
) -> PaperExecutionPolicyCeiling | None:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.get_policy_ceiling(policy_id)
    return _PAPER_POLICIES.get(_policy_key(actor, policy_id))


def _store_paper_batch(
    actor: ActorContext,
    batch: PaperBatchRequest,
) -> PaperBatchRequest:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.create_batch_request(
            replace(batch, requested_by_actor_id=_paper_storage_actor_reference(actor))
        )
    _PAPER_BATCHES[_batch_key(actor, batch.batch_request_id)] = batch
    return batch


def _get_paper_batch(
    actor: ActorContext,
    batch_id: str,
) -> PaperBatchRequest | None:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.get_batch_request(batch_id)
    return _PAPER_BATCHES.get(_batch_key(actor, batch_id))


def _issue_paper_grant(
    actor: ActorContext,
    *,
    policy: PaperExecutionPolicyCeiling,
    batch: PaperBatchRequest,
    expires_at: datetime,
) -> PaperExecutionGrant:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.issue_grant(
            policy=policy,
            batch_request=batch,
            approved_by_actor_id=_paper_storage_actor_reference(actor),
            expires_at=expires_at,
        )
    grant = issue_paper_execution_grant(
        policy=policy,
        batch_request=batch,
        approved_by_actor_id=actor.audit_actor,
        expires_at=expires_at,
        now=datetime.now(UTC),
        grant_id=str(uuid4()),
    )
    _PAPER_GRANTS[_grant_key(actor, grant.grant_id)] = grant
    return grant


def _get_paper_grant(
    actor: ActorContext,
    grant_id: str,
) -> PaperExecutionGrant | None:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return store.get_grant(grant_id)
    return _PAPER_GRANTS.get(_grant_key(actor, grant_id))


def _revoke_paper_grant(
    actor: ActorContext,
    *,
    batch_id: str,
    grant_id: str,
) -> PaperExecutionGrant | None:
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        grant = store.get_grant(grant_id)
        if grant is None or grant.batch_request_id != batch_id:
            return None
        return store.revoke_grant(grant_id)
    grant = _PAPER_GRANTS.get(_grant_key(actor, grant_id))
    if grant is None or grant.batch_request_id != batch_id:
        return None
    revoked = replace(grant, status="revoked")
    _PAPER_GRANTS[_grant_key(actor, revoked.grant_id)] = revoked
    return revoked


def _record_paper_execution_decision(
    actor: ActorContext,
    *,
    grant: PaperExecutionGrant,
    batch: PaperBatchRequest,
    order: PaperExecutionOrder,
    decision: PaperExecutionDecision,
    fill_price: float,
    exposure_after: Mapping[str, object],
) -> PaperExecutionDecision:
    store = _paper_execution_store_for_actor(actor)
    if store is None:
        return decision
    return store.record_execution_decision(
        grant=grant,
        batch_request=batch,
        order=order,
        decision=decision,
        fill_price=fill_price,
        exposure_after=exposure_after,
    )


def _used_paper_idempotency_keys(
    actor: ActorContext,
    idempotency_key: str,
) -> set[str]:
    clean_key = idempotency_key.strip()
    if not clean_key:
        return set()
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        return {clean_key} if store.execution_decision_exists(clean_key) else set()
    return set(_PAPER_IDEMPOTENCY_KEYS.setdefault(actor.tenant_id, set()))


def _remember_paper_idempotency_key(
    actor: ActorContext,
    idempotency_key: str,
) -> None:
    if _paper_execution_store_for_actor(actor) is not None:
        return
    _PAPER_IDEMPOTENCY_KEYS.setdefault(actor.tenant_id, set()).add(idempotency_key)


def _paper_execution_current_exposure(
    actor: ActorContext,
    grant: PaperExecutionGrant,
    request: PaperExecuteApiRequest,
) -> dict[str, float]:
    if _paper_execution_store_for_actor(actor) is not None:
        return {
            "gross_notional": _float_mapping_value(
                grant.consumed_capacity,
                "gross_notional",
            ),
            "net_notional": _float_mapping_value(
                grant.consumed_capacity,
                "net_notional",
            ),
        }
    return {
        "gross_notional": float(request.current_gross_notional),
        "net_notional": float(request.current_net_notional),
    }


def _paper_execution_exposure_after(
    *,
    current_exposure: Mapping[str, float],
    order: PaperExecutionOrder,
    quote_price: float,
) -> dict[str, float]:
    notional = round(order.quantity * quote_price, 2)
    return {
        "gross_notional": current_exposure["gross_notional"] + abs(notional),
        "net_notional": (
            current_exposure["net_notional"] + notional
            if order.side == "buy"
            else current_exposure["net_notional"] - notional
        ),
    }


def _execute_queued_postgres_paper_order(
    actor: ActorContext,
    *,
    store: PostgresPaperExecutionStore,
    order_id: str,
    request: PaperExecuteApiRequest,
    grant: PaperExecutionGrant,
    batch: PaperBatchRequest,
    order: PaperExecutionOrder,
    current_exposure: Mapping[str, float],
) -> PaperExecutionDecision:
    execution_now = request.now or datetime.now(UTC)
    exposure_after = _paper_execution_exposure_after(
        current_exposure=current_exposure,
        order=order,
        quote_price=request.quote_price,
    )
    work_item = PaperExecutionWorkItem(
        work_item_id=str(uuid4()),
        tenant_id=actor.tenant_id,
        batch_request_id=batch.batch_request_id,
        grant_id=grant.grant_id,
        order_id=order_id,
        requested_by_actor_id=_paper_storage_actor_reference(actor),
        idempotency_key=request.idempotency_key,
        status="queued",
        payload={
            "schema_version": "paper-execution-work-item/v1",
            "quote_price": request.quote_price,
            "quote_as_of": request.quote_as_of.isoformat(),
            "now": execution_now.isoformat(),
            "available_cash": request.available_cash,
            "current_gross_notional": current_exposure["gross_notional"],
            "current_net_notional": current_exposure["net_notional"],
            "kill_switch_active": _paper_execution_kill_switch_active(request),
            "exposure_after": exposure_after,
        },
        decision=None,
        attempt_count=0,
        available_at=execution_now,
        claimed_by=None,
        claimed_at=None,
        completed_at=None,
        created_at=execution_now,
        updated_at=execution_now,
    )
    _reject_sensitive_paper_payload(work_item.to_dict())
    store.enqueue_execution_work_item(work_item)
    result = PaperExecutionQueueProcessor(
        store=store,
        worker_id="paper-execution-api",
        now=lambda: execution_now,
        kill_switch_active=_paper_execution_operator_kill_switch_active(),
    ).process_once(work_item_id=work_item.work_item_id)
    if result.decision is None:
        raise HTTPException(
            status_code=503,
            detail="paper_execution_queue_unavailable",
        )
    if result.reason == "completion_failed":
        raise HTTPException(
            status_code=503,
            detail="paper_execution_queue_completion_failed",
        )
    return result.decision


def _paper_execution_response(
    decision: PaperExecutionDecision,
) -> dict | JSONResponse:
    status_code = 200 if decision.status == "accepted" else 409
    if status_code != 200:
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "rejected",
                "decision": decision.to_dict(),
                "mode": "paper_only",
            },
        )
    return {
        "status": "accepted",
        "decision": decision.to_dict(),
        "mode": "paper_only",
    }


def _paper_execution_operator_kill_switch_active() -> bool:
    return env_flag_enabled(
        "PAPER_EXECUTION_KILL_SWITCH",
        "PORTFOLIO_PAPER_EXECUTION_KILL_SWITCH",
    )


def _paper_execution_kill_switch_active(request: PaperExecuteApiRequest) -> bool:
    return request.kill_switch_active or _paper_execution_operator_kill_switch_active()


def _float_mapping_value(payload: Mapping[str, object], key: str) -> float:
    value = payload.get(key, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _paper_order_from_route(
    actor: ActorContext,
    order_id: str,
) -> tuple[PaperBatchRequest, PaperExecutionOrder]:
    batch_id, separator, index_value = order_id.partition(":")
    if not separator:
        raise HTTPException(status_code=404, detail="paper_order_not_found")
    batch = _get_paper_batch(actor, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="paper_batch_not_found")
    try:
        order_index = int(index_value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="paper_order_not_found") from exc
    if order_index < 0 or order_index >= len(batch.orders):
        raise HTTPException(status_code=404, detail="paper_order_not_found")
    return batch, batch.orders[order_index]


@app.post("/v1/paper/policies")
def post_paper_policy(
    request: PaperPolicyRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Create or update a protected paper execution policy ceiling."""
    _require_any_role(actor, {"admin"})
    _reject_sensitive_paper_payload(request.model_dump())
    policy = PaperExecutionPolicyCeiling(
        policy_id=request.policy_id or str(uuid4()),
        tenant_id=actor.tenant_id,
        created_by_actor_id=actor.audit_actor,
        name=request.name,
        status=request.status,
        permitted_strategies=tuple(request.permitted_strategies),
        permitted_symbols=tuple(request.permitted_symbols),
        permitted_sides=tuple(request.permitted_sides),
        permitted_order_types=tuple(request.permitted_order_types),
        max_orders=request.max_orders,
        max_quantity_per_order=request.max_quantity_per_order,
        max_notional_per_order=request.max_notional_per_order,
        max_gross_notional=request.max_gross_notional,
        max_net_notional=request.max_net_notional,
        max_loss_limit=request.max_loss_limit,
        max_drawdown_limit=request.max_drawdown_limit,
        slippage_bps=request.slippage_bps,
        quote_freshness_seconds=request.quote_freshness_seconds,
        market_hours_only=request.market_hours_only,
        self_approval_permitted=request.self_approval_permitted,
        valid_from=request.valid_from,
        valid_until=request.valid_until,
    )
    policy = _store_paper_policy(actor, policy)
    return {
        "status": "success",
        "policy": policy.to_dict(),
        "mode": "paper_only",
    }


@app.post("/v1/paper/batches")
def post_paper_batch(
    request: PaperBatchApiRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Create a proposed paper batch request from authenticated analyst context."""
    _require_any_role(actor, {"analyst", "admin"})
    _reject_sensitive_paper_payload(request.model_dump())
    batch = PaperBatchRequest(
        batch_request_id=request.batch_request_id or str(uuid4()),
        tenant_id=actor.tenant_id,
        requested_by_actor_id=actor.audit_actor,
        strategy_key=request.strategy_key,
        status="proposed",
        orders=tuple(
            PaperExecutionOrder(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type=order.order_type,
                limit_price=order.limit_price,
            )
            for order in request.orders
        ),
        context_refs=tuple(request.context_refs),
        risk_summary=request.risk_summary,
    )
    batch = _store_paper_batch(actor, batch)
    return {
        "status": "success",
        "batch_request": batch.to_dict(),
        "mode": "paper_only",
    }


@app.post("/v1/paper/batches/{batch_id}/approve")
def post_paper_batch_approval(
    batch_id: str,
    request: PaperBatchApprovalApiRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Issue a bounded grant from verified human approver context."""
    actor.require_approver()
    policy = _get_paper_policy(actor, request.policy_id)
    batch = _get_paper_batch(actor, batch_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="paper_policy_not_found")
    if batch is None:
        raise HTTPException(status_code=404, detail="paper_batch_not_found")
    try:
        grant = _issue_paper_grant(
            actor,
            policy=policy,
            batch=batch,
            expires_at=request.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "status": "success",
        "grant": grant.to_dict(),
        "mode": "paper_only",
    }


@app.post("/v1/paper/batches/{batch_id}/revoke")
def post_paper_batch_revoke(
    batch_id: str,
    request: PaperBatchRevokeApiRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Revoke a bounded paper execution grant from verified approver context."""
    actor.require_approver()
    revoked = _revoke_paper_grant(
        actor,
        batch_id=batch_id,
        grant_id=request.grant_id,
    )
    if revoked is None:
        raise HTTPException(status_code=404, detail="paper_grant_not_found")
    return {
        "status": "success",
        "grant": revoked.to_dict(),
        "mode": "paper_only",
    }


@app.post("/v1/paper/orders/{order_id}/execute")
def post_paper_order_execute(
    order_id: str,
    request: PaperExecuteApiRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Evaluate a paper order under a bounded grant; no live broker execution."""
    _require_any_role(actor, {"analyst", "approver", "admin"})
    _reject_sensitive_paper_payload(request.model_dump())
    grant = _get_paper_grant(actor, request.grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail="paper_grant_not_found")
    batch, order = _paper_order_from_route(actor, order_id)
    policy = _get_paper_policy(actor, grant.policy_ceiling_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="paper_policy_not_found")
    current_exposure = _paper_execution_current_exposure(actor, grant, request)
    store = _paper_execution_store_for_actor(actor)
    if store is not None:
        decision = _execute_queued_postgres_paper_order(
            actor,
            store=store,
            order_id=order_id,
            request=request,
            grant=grant,
            batch=batch,
            order=order,
            current_exposure=current_exposure,
        )
        return _paper_execution_response(decision)
    used_keys = _used_paper_idempotency_keys(actor, request.idempotency_key)
    worker = DeterministicPaperExecutionWorker(
        record_decision=lambda decision, worker_request: _record_paper_execution_decision(
            actor,
            grant=worker_request.grant,
            batch=worker_request.batch_request,
            order=worker_request.order,
            decision=decision,
            fill_price=worker_request.quote_price,
            exposure_after=worker_request.exposure_after or {},
        )
    )
    decision = worker.execute(
        PaperExecutionWorkerRequest(
            policy=policy,
            grant=grant,
            batch_request=batch,
            order=order,
            idempotency_key=request.idempotency_key,
            quote_price=request.quote_price,
            quote_as_of=request.quote_as_of,
            now=request.now or datetime.now(UTC),
            used_idempotency_keys=used_keys,
            available_cash=request.available_cash,
            current_gross_notional=current_exposure["gross_notional"],
            current_net_notional=current_exposure["net_notional"],
            kill_switch_active=_paper_execution_kill_switch_active(request),
            exposure_after=_paper_execution_exposure_after(
                current_exposure=current_exposure,
                order=order,
                quote_price=request.quote_price,
            ),
        )
    )
    _remember_paper_idempotency_key(actor, request.idempotency_key)
    return _paper_execution_response(decision)


@app.get("/console/overview")
def get_console_overview() -> dict:
    """Return safe, policy-controlled state for the thin web console."""
    return build_console_overview()


@app.get("/console/workflows")
def get_console_workflows(
    universe_id: str = "fixture_nifty50",
    preset: str = "momentum",
    limit: int = 5,
) -> dict:
    """Return focused workflow pages for the web console."""
    return build_console_workflows(universe_id=universe_id, preset=preset, limit=limit)


@app.post("/console/workflows/strategy-drafts")
def post_console_strategy_draft(request: StrategyDraftRequest) -> dict:
    """Draft a paper strategy from the console without creating an order."""
    return draft_console_strategy(request.symbol, request.rationale)


@app.post("/console/workflows/backtests")
def post_console_backtest(request: BacktestRequestPayload) -> dict:
    """Create a simulated backtest request for paper review."""
    return create_console_backtest(
        request.symbol,
        request.setup,
        request.start_date,
        request.end_date,
    )


@app.post("/console/workflows/paper-orders")
def post_console_paper_order(request: PaperOrderRequest) -> dict:
    """Create a draft paper order proposal that requires approval."""
    return create_console_paper_order(
        request.strategy_id,
        request.symbol,
        request.side,
        request.quantity,
        request.order_type,
        request.requested_price,
    )


@app.post("/console/workflows/paper-orders/{order_id}/approval")
def post_console_paper_order_approval(
    order_id: str,
    request: PaperOrderApprovalRequest,
    actor: Annotated[ActorContext, Depends(actor_context_dependency)],
) -> dict:
    """Approve a paper order for simulated fill processing only."""
    actor.require_approver()
    return approve_console_paper_order(
        order_id,
        actor.audit_actor,
        request.approval_note,
    )


@app.post("/console/workflows/paper-orders/{order_id}/fill")
def post_console_paper_order_fill(order_id: str, request: PaperFillRequest) -> dict:
    """Create a simulated paper fill after approval."""
    return simulate_console_paper_fill(order_id, request.fill_price)


@app.post("/console/workflows/provider-profiles/{provider_id}/refresh")
def post_console_provider_profile_refresh(provider_id: str) -> dict:
    """Refresh one configured provider profile and sanitized import job."""
    return refresh_console_provider_profile(provider_id)


@app.post("/console/workflows/provider-profiles/refresh-schedule")
def post_console_provider_refresh_schedule() -> dict:
    """Run a scheduled configured-provider refresh cycle."""
    return run_console_provider_refresh_schedule()


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
