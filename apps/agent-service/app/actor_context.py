from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

VALID_ROLES = frozenset({"viewer", "analyst", "approver", "admin"})


@dataclass(frozen=True)
class ActorContext:
    """Server-created request actor derived from a verified identity boundary."""

    tenant_id: str
    user_id: str
    roles: frozenset[str]
    request_id: str

    @property
    def can_approve(self) -> bool:
        return bool(self.roles & {"approver", "admin"})

    @property
    def audit_actor(self) -> str:
        return self.user_id

    def require_approver(self) -> None:
        if not self.can_approve:
            raise HTTPException(status_code=403, detail="approver_role_required")


def build_actor_context(
    x_actor_sub: str | None,
    x_tenant_id: str | None,
    x_actor_roles: str | None,
    x_request_id: str | None,
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
    tenant_id = (x_tenant_id or "default").strip() or "default"
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
    )


def actor_context_dependency(
    x_actor_sub: str | None = Header(default=None, alias="X-Actor-Sub"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_actor_roles: str | None = Header(default=None, alias="X-Actor-Roles"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> ActorContext:
    return build_actor_context(
        x_actor_sub=x_actor_sub,
        x_tenant_id=x_tenant_id,
        x_actor_roles=x_actor_roles,
        x_request_id=x_request_id,
    )
