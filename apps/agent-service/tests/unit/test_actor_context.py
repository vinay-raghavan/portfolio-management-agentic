from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
from authlib.jose import JsonWebToken
from fastapi import HTTPException

from app.actor_context import (
    ActorContext,
    OidcProviderConfig,
    build_actor_context,
    build_actor_context_from_oidc_claims,
    decode_oidc_id_token,
    load_oidc_provider_config,
    validate_oidc_authorization_state,
)


def test_actor_context_uses_immutable_subject_and_roles() -> None:
    actor = build_actor_context(
        x_actor_sub="oidc-sub-123",
        x_tenant_id="tenant-a",
        x_actor_roles="viewer,approver",
        x_request_id="req-123",
    )

    assert actor == ActorContext(
        tenant_id="tenant-a",
        user_id="oidc-sub-123",
        roles=frozenset({"viewer", "approver"}),
        request_id="req-123",
    )
    assert actor.can_approve is True
    assert actor.audit_actor == "oidc-sub-123"


def test_actor_context_rejects_missing_subject_tenant_and_unknown_roles() -> None:
    with pytest.raises(HTTPException) as missing:
        build_actor_context(
            x_actor_sub="",
            x_tenant_id="tenant-a",
            x_actor_roles="approver",
            x_request_id="req-123",
        )
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as missing_tenant:
        build_actor_context(
            x_actor_sub="oidc-sub-123",
            x_tenant_id=" ",
            x_actor_roles="approver",
            x_request_id="req-123",
        )
    assert missing_tenant.value.status_code == 401
    assert missing_tenant.value.detail == "actor_tenant_required"

    with pytest.raises(HTTPException) as unknown_role:
        build_actor_context(
            x_actor_sub="oidc-sub-123",
            x_tenant_id="tenant-a",
            x_actor_roles="approver,trader",
            x_request_id="req-123",
        )
    assert unknown_role.value.status_code == 403


def test_oidc_config_loads_generic_provider_settings_without_secrets() -> None:
    config = load_oidc_provider_config(
        {
            "OIDC_AUTH_ENABLED": "true",
            "OIDC_ISSUER": "https://issuer.example.com",
            "OIDC_AUDIENCE": "portfolio-agent",
            "OIDC_AUTHORIZATION_ENDPOINT": "https://issuer.example.com/auth",
            "OIDC_TOKEN_ENDPOINT": "https://issuer.example.com/token",
            "OIDC_CLIENT_ID": "portfolio-console",
            "OIDC_REDIRECT_URI": "http://localhost:8000/v1/auth/oidc/callback",
            "OIDC_SCOPES": "openid profile email",
            "OIDC_TENANT_CLAIM": "tenant_id",
            "OIDC_ROLES_CLAIM": "roles",
            "OIDC_ALLOWED_ALGORITHMS": "RS256,ES256",
            "OIDC_CLOCK_SKEW_SECONDS": "30",
            "OIDC_JWKS_JSON": '{"keys":[{"kid":"public-key"}]}',
        }
    )

    assert config.enabled is True
    assert config.issuer == "https://issuer.example.com"
    assert config.audience == "portfolio-agent"
    assert config.authorization_endpoint == "https://issuer.example.com/auth"
    assert config.token_endpoint == "https://issuer.example.com/token"
    assert config.client_id == "portfolio-console"
    assert config.redirect_uri == "http://localhost:8000/v1/auth/oidc/callback"
    assert config.scopes == ("openid", "profile", "email")
    assert config.tenant_claim == "tenant_id"
    assert config.roles_claim == "roles"
    assert config.allowed_algorithms == ("RS256", "ES256")
    assert config.clock_skew_seconds == 30
    assert "secret" not in str(config).lower()
    assert "public-key" not in str(config)


def test_oidc_claims_build_actor_context_from_sub_with_tenant_roles_and_nonce() -> None:
    actor = build_actor_context_from_oidc_claims(
        {
            "iss": "https://issuer.example.com",
            "aud": "portfolio-agent",
            "sub": "immutable-subject-123",
            "tenant_id": "tenant-a",
            "roles": ["viewer", "approver"],
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "nonce": "nonce-123",
        },
        config=OidcProviderConfig(
            enabled=True,
            issuer="https://issuer.example.com",
            audience="portfolio-agent",
            tenant_claim="tenant_id",
            roles_claim="roles",
        ),
        request_id="req-oidc",
        expected_nonce="nonce-123",
    )

    assert actor == ActorContext(
        tenant_id="tenant-a",
        user_id="immutable-subject-123",
        roles=frozenset({"viewer", "approver"}),
        request_id="req-oidc",
        issuer="https://issuer.example.com",
    )


@pytest.mark.parametrize(
    ("claim_overrides", "detail"),
    [
        ({"iss": "https://evil.example.com"}, "oidc_issuer_invalid"),
        ({"aud": "other-audience"}, "oidc_audience_invalid"),
        ({"exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp())}, "oidc_token_expired"),
        ({"sub": ""}, "oidc_subject_required"),
        ({"tenant_id": ""}, "actor_tenant_required"),
        ({"roles": ["trader"]}, "actor_role_unknown"),
        ({"nonce": "wrong"}, "oidc_nonce_invalid"),
    ],
)
def test_oidc_claims_fail_closed_for_invalid_identity_inputs(claim_overrides, detail) -> None:
    claims = {
        "iss": "https://issuer.example.com",
        "aud": "portfolio-agent",
        "sub": "immutable-subject-123",
        "tenant_id": "tenant-a",
        "roles": ["viewer"],
        "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        "nonce": "nonce-123",
    }
    claims.update(claim_overrides)

    with pytest.raises(HTTPException) as exc:
        build_actor_context_from_oidc_claims(
            claims,
            config=OidcProviderConfig(
                enabled=True,
                issuer="https://issuer.example.com",
                audience="portfolio-agent",
                tenant_claim="tenant_id",
                roles_claim="roles",
            ),
            request_id="req-oidc",
            expected_nonce="nonce-123",
        )

    assert exc.value.detail == detail


def test_oidc_state_validation_uses_exact_constant_time_match() -> None:
    validate_oidc_authorization_state(received_state="state-123", expected_state="state-123")

    with pytest.raises(HTTPException) as exc:
        validate_oidc_authorization_state(received_state="state-123", expected_state="state-456")

    assert exc.value.status_code == 401
    assert exc.value.detail == "oidc_state_invalid"


def test_oidc_id_token_decode_verifies_signature_and_standard_claims() -> None:
    token = JsonWebToken(["HS256"]).encode(
        {"alg": "HS256"},
        {
            "iss": "https://issuer.example.com",
            "aud": "portfolio-agent",
            "sub": "immutable-subject-123",
            "tenant_id": "tenant-a",
            "roles": ["viewer"],
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            "nonce": "nonce-123",
        },
        "test-signing-secret",
    )
    config = OidcProviderConfig(
        enabled=True,
        issuer="https://issuer.example.com",
        audience="portfolio-agent",
        tenant_claim="tenant_id",
        roles_claim="roles",
        allowed_algorithms=("HS256",),
        jwks_json=json.dumps({"kty": "oct", "k": "dGVzdC1zaWduaW5nLXNlY3JldA"}),
    )

    claims = decode_oidc_id_token(token.decode("utf-8"), config=config)

    assert claims["sub"] == "immutable-subject-123"

    header, payload, signature = token.decode("utf-8").split(".")
    decoded_payload = json.loads(_base64url_decode(payload))
    decoded_payload["sub"] = "attacker-subject"
    tampered_payload = _base64url_encode(json.dumps(decoded_payload).encode("utf-8"))

    with pytest.raises(HTTPException) as exc:
        decode_oidc_id_token(f"{header}.{tampered_payload}.{signature}", config=config)

    assert exc.value.status_code == 401
    assert exc.value.detail == "oidc_token_invalid"


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")
