from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi.testclient import TestClient

import app.fast_api_app as fast_api_app

app = fast_api_app.app

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


class _FakePostgresPaperStore:
    def __init__(self) -> None:
        self.policies = {}
        self.batches = {}
        self.grants = {}
        self.recorded_decisions = []
        self.idempotency_checks = []
        self.conflict_on_record = False

    def upsert_policy_ceiling(self, policy):
        self.policies[policy.policy_id] = policy
        return policy

    def get_policy_ceiling(self, policy_id: str):
        return self.policies.get(policy_id)

    def create_batch_request(self, batch_request):
        self.batches[batch_request.batch_request_id] = batch_request
        return batch_request

    def get_batch_request(self, batch_request_id: str):
        return self.batches.get(batch_request_id)

    def issue_grant(
        self,
        *,
        policy,
        batch_request,
        approved_by_actor_id: str,
        expires_at: datetime,
    ):
        grant = fast_api_app.issue_paper_execution_grant(
            policy=policy,
            batch_request=batch_request,
            approved_by_actor_id=approved_by_actor_id,
            expires_at=expires_at,
            now=NOW,
            grant_id="77777777-7777-7777-7777-777777777777",
        )
        self.grants[grant.grant_id] = grant
        return grant

    def get_grant(self, grant_id: str):
        return self.grants.get(grant_id)

    def revoke_grant(self, grant_id: str):
        grant = self.grants.get(grant_id)
        if grant is None or grant.status != "active":
            return None
        revoked = replace(grant, status="revoked")
        self.grants[grant_id] = revoked
        return revoked

    def execution_decision_exists(self, idempotency_key: str) -> bool:
        self.idempotency_checks.append(idempotency_key)
        return any(
            item["decision"]["audit_event"]["idempotency_key"] == idempotency_key
            for item in self.recorded_decisions
        )

    def record_execution_decision(
        self,
        *,
        grant,
        batch_request,
        order,
        decision,
        fill_price: float,
        exposure_after,
    ):
        if self.conflict_on_record:
            return fast_api_app.PaperExecutionDecision(
                status="rejected",
                reasons=("duplicate_idempotency_key",),
                fill=None,
                audit_event={
                    **decision.audit_event,
                    "event_type": "paper_execution_rejected",
                    "reasons": ("duplicate_idempotency_key",),
                },
            )
        self.recorded_decisions.append(
            {
                "grant_id": grant.grant_id,
                "batch_request_id": batch_request.batch_request_id,
                "symbol": order.symbol,
                "decision": decision.to_dict(),
                "fill_price": fill_price,
                "exposure_after": dict(exposure_after),
            }
        )
        return decision


def test_paper_api_uses_postgres_store_when_storage_backend_is_postgres(
    monkeypatch,
) -> None:
    fake_store = _FakePostgresPaperStore()
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_paper_execution_store",
        lambda *, tenant_id, database_url: fake_store,
    )
    client = TestClient(app)
    policy_id = "88888888-8888-8888-8888-888888888888"
    batch_id = "99999999-9999-9999-9999-999999999999"

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
    approval_response = client.post(
        f"/v1/paper/batches/{batch_id}/approve",
        headers=_headers("approver-1", "approver"),
        json={
            "policy_id": policy_id,
            "expires_at": _grant_expiry(),
        },
    )
    grant_id = approval_response.json()["grant"]["grant_id"]
    execute_response = client.post(
        f"/v1/paper/orders/{quote(f'{batch_id}:0', safe='')}/execute",
        headers=_headers("analyst-1", "analyst"),
        json={
            "grant_id": grant_id,
            "idempotency_key": "idem-api-postgres",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
        },
    )

    assert policy_response.status_code == 200
    assert batch_response.status_code == 200
    assert approval_response.status_code == 200
    assert execute_response.status_code == 200
    assert fake_store.policies[policy_id].created_by_actor_id == "admin-1"
    assert fake_store.batches[batch_id].requested_by_actor_id == "analyst-1"
    assert fake_store.grants[grant_id].approved_by_actor_id == "approver-1"
    assert fake_store.recorded_decisions[0]["decision"]["status"] == "accepted"
    combined_payload = str(
        [
            policy_response.json(),
            batch_response.json(),
            approval_response.json(),
            execute_response.json(),
        ]
    ).lower()
    assert "postgresql+psycopg" not in combined_payload
    assert "db-secret" not in combined_payload
    assert "fyers" not in combined_payload


def test_paper_api_uses_postgres_ledger_for_duplicate_idempotency_keys(
    monkeypatch,
) -> None:
    fake_store = _FakePostgresPaperStore()
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_paper_execution_store",
        lambda *, tenant_id, database_url: fake_store,
    )
    client = TestClient(app)
    policy_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    batch_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    idempotency_key = "idem-api-postgres-durable"
    fast_api_app._PAPER_IDEMPOTENCY_KEYS.get(TENANT_ID, set()).discard(idempotency_key)

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
    order_url = f"/v1/paper/orders/{quote(f'{batch_id}:0', safe='')}/execute"
    payload = {
        "grant_id": grant_id,
        "idempotency_key": idempotency_key,
        "quote_price": 980,
        "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
        "now": NOW.isoformat(),
        "available_cash": 100_000,
    }

    first_response = client.post(
        order_url,
        headers=_headers("analyst-1", "analyst"),
        json=payload,
    )
    second_response = client.post(
        order_url,
        headers=_headers("analyst-1", "analyst"),
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert second_response.json()["decision"]["status"] == "rejected"
    assert "duplicate_idempotency_key" in second_response.json()["decision"]["reasons"]
    assert fake_store.idempotency_checks == [idempotency_key, idempotency_key]
    assert len(fake_store.recorded_decisions) == 1
    assert idempotency_key not in fast_api_app._PAPER_IDEMPOTENCY_KEYS.get(
        TENANT_ID,
        set(),
    )
    assert "db-secret" not in str(second_response.json()).lower()


def test_paper_api_returns_rejection_when_postgres_ledger_insert_conflicts(
    monkeypatch,
) -> None:
    fake_store = _FakePostgresPaperStore()
    fake_store.conflict_on_record = True
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_paper_execution_store",
        lambda *, tenant_id, database_url: fake_store,
    )
    client = TestClient(app)
    policy_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    batch_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"

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

    execute_response = client.post(
        f"/v1/paper/orders/{quote(f'{batch_id}:0', safe='')}/execute",
        headers=_headers("analyst-1", "analyst"),
        json={
            "grant_id": grant_id,
            "idempotency_key": "idem-api-conflict",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
        },
    )

    assert execute_response.status_code == 409
    assert execute_response.json()["status"] == "rejected"
    assert execute_response.json()["decision"]["status"] == "rejected"
    assert "duplicate_idempotency_key" in execute_response.json()["decision"]["reasons"]
    assert fake_store.recorded_decisions == []
    assert "db-secret" not in str(execute_response.json()).lower()


def test_paper_api_uses_persisted_grant_capacity_in_postgres_mode(
    monkeypatch,
) -> None:
    fake_store = _FakePostgresPaperStore()
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_paper_execution_store",
        lambda *, tenant_id, database_url: fake_store,
    )
    client = TestClient(app)
    policy_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    batch_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"

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
    fake_store.grants[grant_id] = replace(
        fake_store.grants[grant_id],
        consumed_capacity={
            "order_count": 0,
            "gross_notional": 39_000.0,
            "net_notional": 39_000.0,
        },
    )

    execute_response = client.post(
        f"/v1/paper/orders/{quote(f'{batch_id}:0', safe='')}/execute",
        headers=_headers("analyst-1", "analyst"),
        json={
            "grant_id": grant_id,
            "idempotency_key": "idem-api-persisted-capacity",
            "quote_price": 980,
            "quote_as_of": (NOW - timedelta(seconds=10)).isoformat(),
            "now": NOW.isoformat(),
            "available_cash": 100_000,
            "current_gross_notional": 0,
            "current_net_notional": 0,
        },
    )

    assert execute_response.status_code == 409
    assert execute_response.json()["decision"]["status"] == "rejected"
    assert "gross_notional_limit_exceeded" in execute_response.json()["decision"][
        "reasons"
    ]
    assert fake_store.recorded_decisions == []
    assert "db-secret" not in str(execute_response.json()).lower()
