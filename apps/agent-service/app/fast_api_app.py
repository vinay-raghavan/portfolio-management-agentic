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
import logging
import os

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
    simulate_console_paper_fill,
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
    approved_by: str = Field(default="web-console-reviewer", min_length=1, max_length=80)
    approval_note: str = Field(default="", max_length=500)


class PaperFillRequest(BaseModel):
    fill_price: float | None = Field(default=None, gt=0)


def build_logger():
    if not os.getenv("GOOGLE_CLOUD_PROJECT"):
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
    otel_to_cloud=bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
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
    """Refresh one configured provider profile metadata record."""
    return refresh_console_provider_profile(provider_id)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
