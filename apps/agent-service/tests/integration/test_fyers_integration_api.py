from __future__ import annotations

from fastapi.testclient import TestClient

import app.fast_api_app as fast_api_app

app = fast_api_app.app
TENANT_ID = "tenant-fyers-api"


def _headers(subject: str = "analyst-1", roles: str = "analyst") -> dict[str, str]:
    return {
        "X-Actor-Sub": subject,
        "X-Tenant-Id": TENANT_ID,
        "X-Actor-Roles": roles,
        "X-Request-Id": f"req-{subject}",
    }


def test_fyers_public_contracts_are_typed_and_not_model_visible() -> None:
    from portfolio_domain import FyersConnection, ProviderRefreshJob
    from portfolio_mcp.tools import EXPOSED_TOOL_NAMES

    connection = FyersConnection.disconnected(
        tenant_id=TENANT_ID,
        user_id="user-1",
        connection_id="fyers-connection-1",
    )
    refresh_job = ProviderRefreshJob.created(
        tenant_id=TENANT_ID,
        requested_by_actor_id="user-1",
        refresh_type="account_snapshot",
    )

    assert connection.provider == "fyers"
    assert connection.status == "disconnected"
    assert refresh_job.provider == "fyers"
    assert refresh_job.status == "queued"
    assert "oauth/start" not in EXPOSED_TOOL_NAMES
    assert "oauth/callback" not in EXPOSED_TOOL_NAMES
    assert "disconnect" not in EXPOSED_TOOL_NAMES
    assert "refresh_fyers" not in EXPOSED_TOOL_NAMES


def test_fyers_oauth_start_requires_actor_and_returns_state_without_secrets() -> None:
    client = TestClient(app)

    missing_actor = client.post("/v1/integrations/fyers/oauth/start", json={})
    response = client.post(
        "/v1/integrations/fyers/oauth/start",
        headers=_headers("viewer-1", "viewer"),
        json={},
    )

    assert missing_actor.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    assert payload["status"] == "authorization_required"
    assert payload["connection"]["provider"] == "fyers"
    assert payload["connection"]["tenant_id"] == TENANT_ID
    assert payload["connection"]["status"] == "reconnect_required"
    assert payload["oauth"]["state"]
    assert payload["oauth"]["code_challenge"]
    assert payload["oauth"]["authorize_url"].startswith("https://")
    assert payload["oauth"]["daily_auth_required"] is True
    assert "code_verifier" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized


def test_fyers_oauth_callback_rejects_unknown_state_and_secret_fields() -> None:
    client = TestClient(app)

    unknown = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("viewer-1", "viewer"),
        json={"state": "unknown-state-value", "auth_code": "auth-code-from-browser"},
    )
    contaminated = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("viewer-1", "viewer"),
        json={
            "state": "unknown-state-value",
            "auth_code": "auth-code-from-browser",
            "access_token": "must-not-be-accepted",
        },
    )

    assert unknown.status_code == 409
    assert unknown.json()["detail"] == "fyers_oauth_state_unknown_or_expired"
    assert contaminated.status_code == 422


def test_fyers_oauth_state_is_actor_connection_scoped() -> None:
    client = TestClient(app)

    start = client.post(
        "/v1/integrations/fyers/oauth/start",
        headers=_headers("analyst-state-owner", "analyst"),
        json={},
    )
    state = start.json()["oauth"]["state"]
    wrong_actor = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("analyst-state-attacker", "analyst"),
        json={"state": state, "auth_code": "browser-auth-code"},
    )
    owner = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("analyst-state-owner", "analyst"),
        json={"state": state, "auth_code": "browser-auth-code"},
    )

    assert wrong_actor.status_code == 409
    assert owner.status_code == 200
    assert owner.json()["connection"]["status"] == "reconnect_required"


def test_fyers_oauth_status_disconnect_and_refresh_are_human_api_only_and_redacted() -> None:
    client = TestClient(app)

    start = client.post(
        "/v1/integrations/fyers/oauth/start",
        headers=_headers("analyst-1", "analyst"),
        json={},
    )
    state = start.json()["oauth"]["state"]
    callback = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("analyst-1", "analyst"),
        json={"state": state, "auth_code": "browser-auth-code"},
    )
    status = client.get(
        "/v1/integrations/fyers/oauth/status",
        headers=_headers("analyst-1", "analyst"),
    )
    refresh = client.post(
        "/v1/integrations/fyers/refresh",
        headers=_headers("analyst-1", "analyst"),
        json={"refresh_type": "account_snapshot", "symbols": ["INFY", "^NSEI"]},
    )
    refresh_alias = client.post(
        "/v1/integrations/fyers/oauth/refresh",
        headers=_headers("analyst-1", "analyst"),
        json={"refresh_type": "quote", "symbols": ["INFY"]},
    )
    disconnect = client.post(
        "/v1/integrations/fyers/oauth/disconnect",
        headers=_headers("analyst-1", "analyst"),
        json={},
    )

    assert callback.status_code == 200
    assert callback.json()["status"] == "reconnect_required"
    assert callback.json()["connection"]["credential_status"] == "token_exchange_not_configured"
    assert status.status_code == 200
    assert status.json()["connection"]["status"] == "reconnect_required"
    assert refresh.status_code == 200
    assert refresh.json()["status"] == "success"
    assert refresh.json()["job"]["status"] == "completed"
    assert refresh.json()["mode"] == "read_only"
    assert refresh.json()["account_snapshot"]["provider"] == "fyers"
    assert refresh.json()["account_snapshot"]["positions"][1]["signed_quantity"] == -1
    assert refresh.json()["snapshots"][0]["snapshot_type"] == "quote"
    assert refresh.json()["snapshots"][0]["payload"]["symbol"] == "NSE:INFY-EQ"
    assert refresh_alias.status_code == 200
    assert refresh_alias.json()["snapshots"][0]["snapshot_type"] == "quote"
    assert disconnect.status_code == 200
    assert disconnect.json()["connection"]["status"] == "disconnected"

    serialized = f"{callback.json()} {status.json()} {refresh.json()} {disconnect.json()}".lower()
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized
    assert "place_order" not in serialized
    assert "paper_ledger" not in serialized


def test_fyers_api_uses_postgres_store_when_configured(monkeypatch) -> None:
    class _FakeFyersStore:
        def __init__(self) -> None:
            self.connections: dict[str, object] = {}
            self.sessions: dict[str, object] = {}
            self.upserted_connection_count = 0
            self.upserted_session_count = 0
            self.cleared_connection_ids: list[str] = []
            self.recorded_refreshes: list[dict[str, object]] = []

        def get_connection(self, *, user_id_hash: str) -> object | None:
            return self.connections.get(user_id_hash)

        def upsert_connection(self, connection):
            self.connections[connection.user_id_hash] = connection
            self.upserted_connection_count += 1
            return connection

        def upsert_oauth_session(self, session):
            self.sessions[session.state_hash] = session
            self.upserted_session_count += 1
            return session

        def pop_oauth_session(
            self,
            *,
            state_hash: str,
            connection_id: str,
        ) -> object | None:
            session = self.sessions.get(state_hash)
            if session is None or session.connection_id != connection_id:
                return None
            return self.sessions.pop(state_hash)

        def clear_oauth_sessions(self, *, connection_id: str) -> None:
            self.cleared_connection_ids.append(connection_id)
            for state_hash, session in tuple(self.sessions.items()):
                if session.connection_id == connection_id:
                    del self.sessions[state_hash]

        def record_refresh_result(
            self,
            *,
            job,
            connection_id: str,
            snapshots,
            account_snapshot,
        ) -> None:
            self.recorded_refreshes.append(
                {
                    "job": job,
                    "connection_id": connection_id,
                    "snapshots": tuple(snapshots),
                    "account_snapshot": account_snapshot,
                }
            )

    fake_store = _FakeFyersStore()
    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv("PORTFOLIO_DATABASE_URL", "postgresql://redacted/db")
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_fyers_integration_store",
        lambda *, tenant_id, database_url: fake_store,
    )
    fast_api_app._FYERS_CONNECTIONS.clear()
    fast_api_app._FYERS_OAUTH_STATES.clear()
    client = TestClient(app)

    start = client.post(
        "/v1/integrations/fyers/oauth/start",
        headers=_headers("postgres-fyers-actor", "analyst"),
        json={},
    )
    state = start.json()["oauth"]["state"]
    callback = client.post(
        "/v1/integrations/fyers/oauth/callback",
        headers=_headers("postgres-fyers-actor", "analyst"),
        json={"state": state, "auth_code": "browser-auth-code"},
    )
    refresh = client.post(
        "/v1/integrations/fyers/refresh",
        headers=_headers("postgres-fyers-actor", "analyst"),
        json={"refresh_type": "account_snapshot", "symbols": ["INFY"]},
    )
    disconnect = client.post(
        "/v1/integrations/fyers/oauth/disconnect",
        headers=_headers("postgres-fyers-actor", "analyst"),
        json={},
    )

    assert start.status_code == 200
    assert callback.status_code == 200
    assert refresh.status_code == 200
    assert disconnect.status_code == 200
    assert fake_store.upserted_connection_count >= 3
    assert fake_store.upserted_session_count == 1
    assert len(fake_store.recorded_refreshes) == 1
    assert fake_store.recorded_refreshes[0]["connection_id"] == start.json()["connection"][
        "connection_id"
    ]
    assert fake_store.recorded_refreshes[0]["job"].status == "completed"
    assert fake_store.recorded_refreshes[0]["snapshots"][0].snapshot_type == "quote"
    assert fake_store.recorded_refreshes[0]["account_snapshot"].positions[1].signed_quantity == -1
    assert fake_store.sessions == {}
    assert fake_store.cleared_connection_ids == [start.json()["connection"]["connection_id"]]
    assert fast_api_app._FYERS_CONNECTIONS == {}
    assert fast_api_app._FYERS_OAUTH_STATES == {}
    serialized = (
        f"{fake_store.connections} {fake_store.recorded_refreshes} "
        f"{start.json()} {callback.json()} {refresh.json()} {disconnect.json()}"
    ).lower()
    assert "code_verifier" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized
