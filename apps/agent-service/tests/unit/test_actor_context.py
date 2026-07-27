from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.actor_context import ActorContext, build_actor_context


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
