from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.fast_api_app import app

NOW = datetime(2026, 7, 27, 9, 15, tzinfo=UTC)
TENANT_ID = "tenant-api"


def _headers(subject: str, roles: str) -> dict[str, str]:
    return {
        "X-Actor-Sub": subject,
        "X-Tenant-Id": TENANT_ID,
        "X-Actor-Roles": roles,
        "X-Request-Id": f"req-{subject}",
    }


def _policy_payload(policy_id: str) -> dict:
    return {
        "policy_id": policy_id,
        "name": "Paper execution API ceiling",
        "status": "enabled",
        "permitted_strategies": ["breakout-continuation"],
        "permitted_symbols": ["TATAMOTORS"],
        "permitted_sides": ["buy"],
        "permitted_order_types": ["market"],
        "max_orders": 1,
        "max_quantity_per_order": 5,
        "max_notional_per_order": 20_000,
        "max_gross_notional": 40_000,
        "max_net_notional": 40_000,
        "max_loss_limit": 2_500,
        "max_drawdown_limit": 3_000,
        "slippage_bps": 25,
        "quote_freshness_seconds": 30,
        "market_hours_only": True,
        "self_approval_permitted": False,
        "valid_from": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "valid_until": datetime(2027, 1, 1, tzinfo=UTC).isoformat(),
    }


def _batch_payload(batch_id: str) -> dict:
    return {
        "batch_request_id": batch_id,
        "strategy_key": "breakout-continuation",
        "orders": [
            {
                "symbol": "TATAMOTORS",
                "side": "buy",
                "quantity": 5,
                "order_type": "market",
            }
        ],
        "context_refs": [{"type": "research_document", "id": "doc-1"}],
        "risk_summary": {"paper_only": True, "live_trading": "forbidden"},
    }


def _grant_expiry() -> str:
    return datetime(2026, 7, 28, tzinfo=UTC).isoformat()


def test_paper_policy_api_requires_authenticated_admin_actor() -> None:
    client = TestClient(app)

    missing = client.post("/v1/paper/policies", json={"name": "Incomplete"})
    viewer = client.post(
        "/v1/paper/policies",
        headers=_headers("viewer-1", "viewer"),
        json={"name": "Incomplete"},
    )

    assert missing.status_code == 401
    assert viewer.status_code == 403


def test_paper_batch_approval_uses_actor_context_not_body_approver_identity() -> None:
    client = TestClient(app)
    policy_id = "policy-api-identity"
    batch_id = "batch-api-identity"

    policy_response = client.post(
        "/v1/paper/policies",
        headers=_headers("admin-1", "admin"),
        json=_policy_payload(policy_id),
    )
    batch_response = client.post(
        "/v1/paper/batches",
        headers=_headers("analyst-1", "analyst"),
        json=_batch_payload(batch_id),
    )
    spoof_response = client.post(
        f"/v1/paper/batches/{batch_id}/approve",
        headers=_headers("approver-1", "approver"),
        json={
            "policy_id": policy_id,
            "expires_at": _grant_expiry(),
            "approved_by": "model-claimed-human",
        },
    )
    approval_response = client.post(
        f"/v1/paper/batches/{batch_id}/approve",
        headers=_headers("approver-1", "approver"),
        json={
            "policy_id": policy_id,
            "expires_at": _grant_expiry(),
        },
    )

    assert policy_response.status_code == 200
    assert batch_response.status_code == 200
    assert spoof_response.status_code == 422
    assert approval_response.status_code == 200
    grant = approval_response.json()["grant"]
    assert grant["approved_by_actor_id"] == "approver-1"
    assert grant["approved_by_actor_id"] != "analyst-1"
    assert grant["scope"]["symbols"] == ["TATAMOTORS"]
    assert "approved_by" not in approval_response.request.content.decode()
    assert "access_token" not in str(grant).lower()
    assert "fyers" not in str(grant).lower()


def test_paper_execution_api_accepts_fresh_granted_order_as_paper_only() -> None:
    client = TestClient(app)
    policy_id = "policy-api-execute"
    batch_id = "batch-api-execute"

    client.post(
        "/v1/paper/policies",
        headers=_headers("admin-1", "admin"),
        json=_policy_payload(policy_id),
    )
    client.post(
        "/v1/paper/batches",
        headers=_headers("analyst-1", "analyst"),
        json=_batch_payload(batch_id),
    )
    approval_response = client.post(
        f"/v1/paper/batches/{batch_id}/approve",
        headers=_headers("approver-1", "approver"),
        json={
            "policy_id": policy_id,
            "expires_at": _grant_expiry(),
        },
    )
    grant_id = approval_response.json()["grant"]["grant_id"]
    order_id = quote(f"{batch_id}:0", safe="")

    execute_response = client.post(
        f"/v1/paper/orders/{order_id}/execute",
        headers=_headers("analyst-1", "analyst"),
        json={
            "grant_id": grant_id,
            "idempotency_key": "idem-api-ok",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
            "current_gross_notional": 5_000,
            "current_net_notional": 5_000,
        },
    )

    assert execute_response.status_code == 200
    decision = execute_response.json()["decision"]
    assert decision["status"] == "accepted"
    assert decision["fill"]["mode"] == "paper"
    assert decision["fill"]["idempotency_key"] == "idem-api-ok"
    assert decision["audit_event"]["event_type"] == "paper_execution_accepted"
    assert "live" not in str(decision["fill"]).lower()
    assert "fyers" not in str(execute_response.json()).lower()
    assert "token" not in str(execute_response.json()).lower()


def test_paper_execution_api_revokes_grant_and_rejects_later_execution() -> None:
    client = TestClient(app)
    policy_id = "policy-api-revoke"
    batch_id = "batch-api-revoke"

    client.post(
        "/v1/paper/policies",
        headers=_headers("admin-1", "admin"),
        json=_policy_payload(policy_id),
    )
    client.post(
        "/v1/paper/batches",
        headers=_headers("analyst-1", "analyst"),
        json=_batch_payload(batch_id),
    )
    approval_response = client.post(
        f"/v1/paper/batches/{batch_id}/approve",
        headers=_headers("approver-1", "approver"),
        json={
            "policy_id": policy_id,
            "expires_at": _grant_expiry(),
        },
    )
    grant_id = approval_response.json()["grant"]["grant_id"]
    revoke_response = client.post(
        f"/v1/paper/batches/{batch_id}/revoke",
        headers=_headers("approver-1", "approver"),
        json={"grant_id": grant_id},
    )
    order_id = quote(f"{batch_id}:0", safe="")
    execute_response = client.post(
        f"/v1/paper/orders/{order_id}/execute",
        headers=_headers("analyst-1", "analyst"),
        json={
            "grant_id": grant_id,
            "idempotency_key": "idem-api-revoked",
            "quote_price": 980,
            "quote_as_of": NOW.isoformat(),
            "now": NOW.isoformat(),
        },
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json()["grant"]["status"] == "revoked"
    assert execute_response.status_code == 409
    assert execute_response.json()["decision"]["status"] == "rejected"
    assert "grant_revoked" in execute_response.json()["decision"]["reasons"]
