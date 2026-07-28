from __future__ import annotations

import json
import os
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from authlib.jose import JoseError, JsonWebToken
from fastapi import Header, HTTPException

VALID_ROLES = frozenset({"viewer", "analyst", "approver", "admin"})


@dataclass(frozen=True)
class ActorContext:
    """Server-created request actor derived from a verified identity boundary."""

    tenant_id: str
    user_id: str
    roles: frozenset[str]
    request_id: str
    issuer: str = "trusted-header"

    @property
    def can_approve(self) -> bool:
        return bool(self.roles & {"approver", "admin"})

    @property
    def audit_actor(self) -> str:
        return self.user_id

    def require_approver(self) -> None:
        if not self.can_approve:
            raise HTTPException(status_code=403, detail="approver_role_required")


@dataclass(frozen=True)
class OidcProviderConfig:
    enabled: bool = False
    issuer: str = ""
    audience: str = ""
    tenant_claim: str = "tenant_id"
    roles_claim: str = "roles"
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    client_id: str = ""
    redirect_uri: str = ""
    scopes: tuple[str, ...] = ("openid", "profile", "email")
    allowed_algorithms: tuple[str, ...] = ("RS256", "ES256")
    clock_skew_seconds: int = 60
    jwks_json: str | None = field(default=None, repr=False)


def load_oidc_provider_config(env: Mapping[str, str] | None = None) -> OidcProviderConfig:
    active_env = env or os.environ
    return OidcProviderConfig(
        enabled=_truthy(active_env.get("OIDC_AUTH_ENABLED")),
        issuer=(active_env.get("OIDC_ISSUER") or "").strip(),
        audience=(active_env.get("OIDC_AUDIENCE") or "").strip(),
        tenant_claim=(active_env.get("OIDC_TENANT_CLAIM") or "tenant_id").strip(),
        roles_claim=(active_env.get("OIDC_ROLES_CLAIM") or "roles").strip(),
        authorization_endpoint=(
            active_env.get("OIDC_AUTHORIZATION_ENDPOINT") or ""
        ).strip(),
        token_endpoint=(active_env.get("OIDC_TOKEN_ENDPOINT") or "").strip(),
        client_id=(active_env.get("OIDC_CLIENT_ID") or "").strip(),
        redirect_uri=(active_env.get("OIDC_REDIRECT_URI") or "").strip(),
        scopes=tuple(
            scope.strip()
            for scope in (active_env.get("OIDC_SCOPES") or "openid profile email").split()
            if scope.strip()
        )
        or ("openid",),
        allowed_algorithms=tuple(
            algorithm.strip()
            for algorithm in (active_env.get("OIDC_ALLOWED_ALGORITHMS") or "RS256,ES256").split(",")
            if algorithm.strip()
        )
        or ("RS256", "ES256"),
        clock_skew_seconds=max(int(active_env.get("OIDC_CLOCK_SKEW_SECONDS") or "60"), 0),
        jwks_json=(active_env.get("OIDC_JWKS_JSON") or "").strip() or None,
    )


def decode_oidc_id_token(
    token: str,
    *,
    config: OidcProviderConfig,
) -> dict[str, Any]:
    """Verify an OIDC JWT signature and standard issuer/audience/expiry claims."""
    if not config.issuer:
        raise HTTPException(status_code=503, detail="oidc_issuer_not_configured")
    if not config.audience:
        raise HTTPException(status_code=503, detail="oidc_audience_not_configured")
    if not config.jwks_json:
        raise HTTPException(status_code=503, detail="oidc_jwks_not_configured")
    try:
        key = json.loads(config.jwks_json)
        claims = JsonWebToken(list(config.allowed_algorithms)).decode(
            token,
            key,
            claims_options={
                "iss": {"essential": True, "value": config.issuer},
                "aud": {"essential": True, "value": config.audience},
                "sub": {"essential": True},
                "exp": {"essential": True},
            },
        )
        claims.validate(leeway=config.clock_skew_seconds)
    except (JoseError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="oidc_token_invalid") from exc
    return dict(claims)


def validate_oidc_authorization_state(
    *,
    received_state: str,
    expected_state: str,
) -> None:
    if not received_state or not expected_state or not secrets.compare_digest(
        received_state,
        expected_state,
    ):
        raise HTTPException(status_code=401, detail="oidc_state_invalid")


def build_actor_context_from_oidc_claims(
    claims: Mapping[str, Any],
    *,
    config: OidcProviderConfig,
    request_id: str | None,
    expected_nonce: str | None = None,
) -> ActorContext:
    _validate_oidc_claims(claims, config=config, expected_nonce=expected_nonce)
    return build_actor_context(
        x_actor_sub=str(claims.get("sub") or ""),
        x_tenant_id=str(claims.get(config.tenant_claim) or ""),
        x_actor_roles=_roles_header(claims.get(config.roles_claim)),
        x_request_id=request_id,
        issuer=config.issuer,
    )


def build_actor_context(
    x_actor_sub: str | None,
    x_tenant_id: str | None,
    x_actor_roles: str | None,
    x_request_id: str | None,
    issuer: str = "trusted-header",
) -> ActorContext:
    """Build the public ActorContext contract from trusted request metadata.

    The current local boundary accepts explicit headers so tests and local
    deployments can exercise the contract before the OIDC middleware lands.
    Production OIDC middleware should validate issuer, audience, signature,
    expiry, state and nonce, then populate the same immutable subject and role
    metadata. Approval endpoints must use this context, never request-body
    approver fields.
    """

    subject = (x_actor_sub or "").strip()
    if not subject:
        raise HTTPException(status_code=401, detail="actor_subject_required")
    tenant_id = (x_tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="actor_tenant_required")
    request_id = (x_request_id or "").strip()
    roles = frozenset(
        role.strip().lower()
        for role in (x_actor_roles or "viewer").split(",")
        if role.strip()
    ) or frozenset({"viewer"})
    unknown_roles = roles - VALID_ROLES
    if unknown_roles:
        raise HTTPException(status_code=403, detail="actor_role_unknown")
    return ActorContext(
        tenant_id=tenant_id,
        user_id=subject,
        roles=roles,
        request_id=request_id,
        issuer=issuer,
    )


def actor_context_dependency(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_oidc_nonce: str | None = Header(default=None, alias="X-OIDC-Nonce"),
    x_actor_sub: str | None = Header(default=None, alias="X-Actor-Sub"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_actor_roles: str | None = Header(default=None, alias="X-Actor-Roles"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> ActorContext:
    oidc_config = load_oidc_provider_config()
    if oidc_config.enabled:
        token = _bearer_token(authorization)
        claims = decode_oidc_id_token(token, config=oidc_config)
        return build_actor_context_from_oidc_claims(
            claims,
            config=oidc_config,
            request_id=x_request_id,
            expected_nonce=x_oidc_nonce,
        )
    return build_actor_context(
        x_actor_sub=x_actor_sub,
        x_tenant_id=x_tenant_id,
        x_actor_roles=x_actor_roles,
        x_request_id=x_request_id,
    )


def _validate_oidc_claims(
    claims: Mapping[str, Any],
    *,
    config: OidcProviderConfig,
    expected_nonce: str | None,
) -> None:
    if claims.get("iss") != config.issuer:
        raise HTTPException(status_code=401, detail="oidc_issuer_invalid")
    if not _audience_matches(claims.get("aud"), config.audience):
        raise HTTPException(status_code=401, detail="oidc_audience_invalid")
    if not str(claims.get("sub") or "").strip():
        raise HTTPException(status_code=401, detail="oidc_subject_required")
    if not str(claims.get(config.tenant_claim) or "").strip():
        raise HTTPException(status_code=401, detail="actor_tenant_required")
    expires_at = _epoch_seconds(claims.get("exp"))
    if (
        expires_at is None
        or expires_at + config.clock_skew_seconds <= int(datetime.now(UTC).timestamp())
    ):
        raise HTTPException(status_code=401, detail="oidc_token_expired")
    if expected_nonce is not None and not secrets.compare_digest(
        str(claims.get("nonce") or ""),
        expected_nonce,
    ):
        raise HTTPException(status_code=401, detail="oidc_nonce_invalid")


def _audience_matches(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return expected in {str(item) for item in value}
    return False


def _epoch_seconds(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _roles_header(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return ",".join(str(item) for item in value)
    return None


def _bearer_token(authorization: str | None) -> str:
    value = (authorization or "").strip()
    prefix = "Bearer "
    if not value.startswith(prefix) or not value.removeprefix(prefix).strip():
        raise HTTPException(status_code=401, detail="oidc_bearer_token_required")
    return value.removeprefix(prefix).strip()


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
