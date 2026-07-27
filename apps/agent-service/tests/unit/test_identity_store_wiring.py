from __future__ import annotations

from app import fast_api_app
from app.actor_context import ActorContext


def test_session_memory_store_resolves_postgres_actor_identity(monkeypatch) -> None:
    class _IdentityRecord:
        actor_identity_id = "11111111-1111-1111-1111-111111111111"

    class _IdentityStore:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def upsert_identity(self, **kwargs):
            self.calls.append(kwargs)
            return _IdentityRecord()

    identity_store = _IdentityStore()
    built_session_store = object()
    captured: dict[str, str] = {}

    monkeypatch.setenv("PORTFOLIO_STORAGE_BACKEND", "postgres")
    monkeypatch.setenv(
        "PORTFOLIO_DATABASE_URL",
        "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    )
    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_actor_identity_store",
        lambda *, database_url: identity_store,
    )

    def _fake_session_store_builder(*, tenant_id, actor_identity_id, database_url):
        captured["tenant_id"] = tenant_id
        captured["actor_identity_id"] = actor_identity_id
        captured["database_url"] = database_url
        return built_session_store

    monkeypatch.setattr(
        fast_api_app,
        "_build_postgres_session_memory_store",
        _fake_session_store_builder,
    )

    store = fast_api_app._session_memory_store_for_actor(
        ActorContext(
            tenant_id="tenant-a",
            user_id="oidc-sub-123",
            roles=frozenset({"analyst"}),
            request_id="req-1",
            issuer="https://issuer.example.com",
        )
    )

    assert store is built_session_store
    assert identity_store.calls == [
        {
            "issuer": "https://issuer.example.com",
            "subject": "oidc-sub-123",
        }
    ]
    assert captured == {
        "tenant_id": "tenant-a",
        "actor_identity_id": "11111111-1111-1111-1111-111111111111",
        "database_url": "postgresql+psycopg://portfolio:db-secret@postgres:5432/portfolio_agentic",
    }
