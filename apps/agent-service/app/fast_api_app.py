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
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import urlopen

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging
from pydantic import BaseModel, Field

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
model_provider_path = str(REPO_ROOT / "packages/model-provider")
if model_provider_path not in sys.path:
    sys.path.insert(0, model_provider_path)

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
    approved_by: str = Field(
        default="web-console-reviewer", min_length=1, max_length=80
    )
    approval_note: str = Field(default="", max_length=500)


class PaperFillRequest(BaseModel):
    fill_price: float | None = Field(default=None, gt=0)


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
) -> dict:
    """Approve a paper order for simulated fill processing only."""
    return approve_console_paper_order(
        order_id,
        request.approved_by,
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
