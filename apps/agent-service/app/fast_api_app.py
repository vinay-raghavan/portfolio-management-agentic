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
import sys
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel, ConfigDict, Field

from app.actor_context import ActorContext, actor_context_dependency
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
    DatabaseBackend,
    DeterministicPaperExecutionWorker,
    PaperBatchRequest,
    PaperExecutionDecision,
    PaperExecutionGrant,
    PaperExecutionOrder,
    PaperExecutionPolicyCeiling,
    PaperExecutionWorkerRequest,
    PostgresPaperExecutionStore,
    evaluate_database_runtime_readiness,
    issue_paper_execution_grant,
    load_database_runtime_profile,
)
from portfolio_model_provider import (  # noqa: E402
    ModelProvider,
    OllamaModelMetadata,
    build_model_capability_report,
    load_model_runtime_profile,
    parse_ollama_tags_response,
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


def cloud_telemetry_enabled() -> bool:
    enabled = os.getenv("ENABLE_CLOUD_TELEMETRY", "").strip().lower()
    return enabled in {"1", "true", "yes", "y", "on"} and bool(
        os.getenv("GOOGLE_CLOUD_PROJECT")
    )


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


@app.get("/v1/models/ollama/status")
def get_ollama_model_status() -> dict:
    """Return redacted model runtime readiness and route-budget status."""
    profile = load_model_runtime_profile(os.environ)
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
    return {
        "status": "ready" if report.startup_allowed else "blocked",
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
        "startup_allowed": report.startup_allowed,
        "blocking_reasons": report.blocking_reasons,
        "model_available": report.model_available,
        "model_digest_verified": report.model_digest_verified,
        "model_inventory_source": inventory_source,
        "model_inventory": inventory,
        "applies_to_active_provider": profile.provider == ModelProvider.OLLAMA,
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


def _require_any_role(actor: ActorContext, allowed_roles: set[str]) -> None:
    if not actor.roles & allowed_roles:
        raise HTTPException(status_code=403, detail="role_required")


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
        return store.upsert_policy_ceiling(policy)
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
        return store.create_batch_request(batch)
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
            approved_by_actor_id=actor.audit_actor,
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
    used_keys = _used_paper_idempotency_keys(actor, request.idempotency_key)
    current_exposure = _paper_execution_current_exposure(actor, grant, request)
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
            kill_switch_active=request.kill_switch_active,
            exposure_after=_paper_execution_exposure_after(
                current_exposure=current_exposure,
                order=order,
                quote_price=request.quote_price,
            ),
        )
    )
    _remember_paper_idempotency_key(actor, request.idempotency_key)
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
