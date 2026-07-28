from __future__ import annotations

from fastapi.testclient import TestClient

from app.fast_api_app import app

TENANT_ID = "tenant-research-api"


def _headers(subject: str = "researcher-1", roles: str = "analyst") -> dict[str, str]:
    return {
        "X-Actor-Sub": subject,
        "X-Tenant-Id": TENANT_ID,
        "X-Actor-Roles": roles,
    }


def test_research_sources_list_only_registered_allowlisted_sources() -> None:
    client = TestClient(app)

    response = client.get("/v1/research/sources", headers=_headers(roles="viewer"))

    assert response.status_code == 200
    payload = response.json()
    serialized = str(payload).lower()
    source_ids = {source["source_id"] for source in payload["sources"]}
    assert payload["status"] == "success"
    assert {"sebi-publications", "nse-announcements", "bse-announcements"}.issubset(
        source_ids
    )
    assert all(source["allowlisted"] is True for source in payload["sources"])
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert "token" not in serialized


def test_research_search_uses_curated_fixture_store_and_rejects_urls() -> None:
    client = TestClient(app)

    search = client.post(
        "/v1/research/search",
        headers=_headers(),
        json={"query": "volatility sizing", "limit": 2},
    )
    url_search = client.post(
        "/v1/research/search",
        headers=_headers(),
        json={"query": "https://example.com/research", "limit": 2},
    )

    assert search.status_code == 200
    payload = search.json()
    serialized = str(payload).lower()
    assert payload["status"] == "success"
    assert payload["retrieval"] == {
        "mode": "file_backed_fixture",
        "backend": "lexical",
        "vector_retrieval": "disabled",
        "source_policy": "admin_allowlist_only",
    }
    assert len(payload["hits"]) <= 2
    assert payload["hits"]
    assert payload["hits"][0]["checksum"].startswith("sha256:")
    assert "embedding" not in serialized
    assert "secret" not in serialized
    assert url_search.status_code == 400
    assert url_search.json()["detail"] == "research_query_invalid"


def test_research_refresh_accepts_only_registered_source_id_and_normalized_query() -> None:
    client = TestClient(app)

    accepted = client.post(
        "/v1/research/refresh/nse-announcements",
        headers=_headers(),
        json={"normalized_query_or_symbol": "NSE:INFY-EQ"},
    )
    unknown = client.post(
        "/v1/research/refresh/not-registered",
        headers=_headers(),
        json={"normalized_query_or_symbol": "NSE:INFY-EQ"},
    )
    arbitrary_url = client.post(
        "/v1/research/refresh/nse-announcements",
        headers=_headers(),
        json={"normalized_query_or_symbol": "https://example.com/research"},
    )

    assert accepted.status_code == 200
    payload = accepted.json()
    serialized = str(payload).lower()
    assert payload["status"] == "queued"
    assert payload["source"]["source_id"] == "nse-announcements"
    assert payload["normalized_query_or_symbol"] == "NSE:INFY-EQ"
    assert payload["mode"] == "admin_allowlist_only"
    assert "https://" not in serialized
    assert "token" not in serialized
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "research_source_not_registered"
    assert arbitrary_url.status_code == 400
    assert arbitrary_url.json()["detail"] == "research_query_invalid"


def test_research_refresh_kill_switch_blocks_queue_intents_without_blocking_reads(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RESEARCH_REFRESH_KILL_SWITCH", "true")
    client = TestClient(app)

    sources = client.get("/v1/research/sources", headers=_headers(roles="viewer"))
    search = client.post(
        "/v1/research/search",
        headers=_headers(),
        json={"query": "volatility sizing", "limit": 2},
    )
    refresh = client.post(
        "/v1/research/refresh/nse-announcements",
        headers=_headers(),
        json={"normalized_query_or_symbol": "NSE:INFY-EQ"},
    )

    assert sources.status_code == 200
    assert search.status_code == 200
    assert refresh.status_code == 503
    assert refresh.json()["detail"] == "research_refresh_kill_switch_active"
    serialized = str(refresh.json()).lower()
    assert "nse-announcements" not in serialized
    assert "nse:infy-eq" not in serialized
