from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from types import MappingProxyType
from typing import Any


class CredentialVaultBackend(str, Enum):
    DISABLED = "disabled"
    MACOS_KEYCHAIN = "macos_keychain"
    KMS = "kms"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CredentialVaultProfile:
    backend: CredentialVaultBackend
    service_name: str | None
    kms_key_uri: str | None
    local_runtime: bool
    hosted_runtime: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend.value,
            "service_configured": bool(self.service_name),
            "kms_key_configured": bool(self.kms_key_uri),
            "local_runtime": self.local_runtime,
            "hosted_runtime": self.hosted_runtime,
        }


@dataclass(frozen=True)
class CredentialVaultReadiness:
    ready: bool
    blocking_reasons: tuple[str, ...]
    token_exchange_allowed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "blocking_reasons": list(self.blocking_reasons),
            "token_exchange_allowed": self.token_exchange_allowed,
        }


@dataclass(frozen=True, repr=False)
class CredentialVaultSecretMaterial:
    payload: Mapping[str, Any]
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))

    def __repr__(self) -> str:
        return (
            "CredentialVaultSecretMaterial("
            f"sensitive_field_count={len(self.payload)}, "
            f"expires_at_configured={self.expires_at is not None}, "
            "payload=<redacted>)"
        )


@dataclass(frozen=True)
class CredentialVaultWritePlan:
    ready: bool
    backend: CredentialVaultBackend
    credential_ref_configured: bool
    sensitive_field_count: int
    expires_at_configured: bool
    blocking_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "backend": self.backend.value,
            "credential_ref_configured": self.credential_ref_configured,
            "sensitive_field_count": self.sensitive_field_count,
            "expires_at_configured": self.expires_at_configured,
            "blocking_reasons": list(self.blocking_reasons),
        }


@dataclass(frozen=True, repr=False)
class CredentialVaultWriteResult:
    written: bool
    backend: CredentialVaultBackend
    credential_ref_configured: bool
    sensitive_field_count: int
    expires_at_configured: bool
    blocking_reasons: tuple[str, ...]

    def __repr__(self) -> str:
        return (
            "CredentialVaultWriteResult("
            f"written={self.written}, "
            f"backend={self.backend.value!r}, "
            f"credential_ref_configured={self.credential_ref_configured}, "
            f"sensitive_field_count={self.sensitive_field_count}, "
            f"expires_at_configured={self.expires_at_configured}, "
            f"blocking_reasons={self.blocking_reasons!r})"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "written": self.written,
            "backend": self.backend.value,
            "credential_ref_configured": self.credential_ref_configured,
            "sensitive_field_count": self.sensitive_field_count,
            "expires_at_configured": self.expires_at_configured,
            "blocking_reasons": list(self.blocking_reasons),
        }


class DisabledCredentialVaultWriter:
    def __init__(self, profile: CredentialVaultProfile) -> None:
        self._profile = profile

    def write(
        self,
        *,
        credential_ref: str,
        material: CredentialVaultSecretMaterial,
    ) -> CredentialVaultWriteResult:
        plan = plan_credential_vault_write(
            profile=self._profile,
            credential_ref=credential_ref,
            material=material,
        )
        return _write_result(plan=plan, written=False)


class MacOSKeychainCredentialVaultWriter:
    def __init__(
        self,
        *,
        profile: CredentialVaultProfile,
        command_runner: Callable[[tuple[str, ...]], None] | None = None,
        security_binary: str = "/usr/bin/security",
    ) -> None:
        self._profile = profile
        self._command_runner = command_runner or _run_security_command
        self._security_binary = security_binary

    def write(
        self,
        *,
        credential_ref: str,
        material: CredentialVaultSecretMaterial,
    ) -> CredentialVaultWriteResult:
        plan = plan_credential_vault_write(
            profile=self._profile,
            credential_ref=credential_ref,
            material=material,
        )
        if not plan.ready:
            return _write_result(plan=plan, written=False)

        args = (
            self._security_binary,
            "add-generic-password",
            "-U",
            "-a",
            credential_ref,
            "-s",
            self._profile.service_name or "",
            "--stdin",
        )
        self._command_runner(args, input_text=_serialize_secret_material(material))
        return _write_result(plan=plan, written=True)


class KmsCredentialVaultWriter:
    def __init__(
        self,
        *,
        profile: CredentialVaultProfile,
        kms_writer: Callable[..., str] | None = None,
    ) -> None:
        self._profile = profile
        self._kms_writer = kms_writer

    def write(
        self,
        *,
        credential_ref: str,
        material: CredentialVaultSecretMaterial,
    ) -> CredentialVaultWriteResult:
        plan = plan_credential_vault_write(
            profile=self._profile,
            credential_ref=credential_ref,
            material=material,
        )
        blocking_reasons = list(plan.blocking_reasons)
        if plan.ready and self._kms_writer is None:
            blocking_reasons.append("credential_vault_kms_writer_missing")
        if blocking_reasons:
            return CredentialVaultWriteResult(
                written=False,
                backend=plan.backend,
                credential_ref_configured=plan.credential_ref_configured,
                sensitive_field_count=plan.sensitive_field_count,
                expires_at_configured=plan.expires_at_configured,
                blocking_reasons=tuple(blocking_reasons),
            )

        self._kms_writer(
            key_uri=self._profile.kms_key_uri or "",
            credential_ref=credential_ref,
            plaintext=_serialize_secret_material(material).encode("utf-8"),
        )
        return _write_result(plan=plan, written=True)


def build_credential_vault_writer(
    profile: CredentialVaultProfile,
    *,
    command_runner: Callable[..., None] | None = None,
    kms_writer: Callable[..., str] | None = None,
) -> DisabledCredentialVaultWriter | MacOSKeychainCredentialVaultWriter | KmsCredentialVaultWriter:
    if profile.backend == CredentialVaultBackend.MACOS_KEYCHAIN:
        return MacOSKeychainCredentialVaultWriter(
            profile=profile,
            command_runner=command_runner,
        )
    if profile.backend == CredentialVaultBackend.KMS:
        return KmsCredentialVaultWriter(profile=profile, kms_writer=kms_writer)
    return DisabledCredentialVaultWriter(profile)


def build_credential_vault_ref(
    *,
    tenant_id: str,
    provider: str,
    purpose: str,
    subject_hash: str,
    backend: CredentialVaultBackend,
) -> str:
    """Build an opaque, non-secret reference for token material stored elsewhere."""
    if backend not in {CredentialVaultBackend.MACOS_KEYCHAIN, CredentialVaultBackend.KMS}:
        raise ValueError("credential vault reference requires a real vault backend")
    normalized_provider = _safe_ref_part(provider)
    normalized_backend = backend.value
    digest = sha256(
        f"{tenant_id}:{normalized_provider}:{purpose}:{subject_hash}".encode("utf-8")
    ).hexdigest()
    return f"credential-vault://{normalized_backend}/{normalized_provider}/{digest[:32]}"


def plan_credential_vault_write(
    *,
    profile: CredentialVaultProfile,
    credential_ref: str,
    material: CredentialVaultSecretMaterial,
) -> CredentialVaultWritePlan:
    readiness = evaluate_credential_vault_readiness(profile)
    blocking_reasons = list(readiness.blocking_reasons)
    expected_prefix = f"credential-vault://{profile.backend.value}/"
    if not credential_ref or not credential_ref.startswith(expected_prefix):
        blocking_reasons.append("credential_vault_ref_backend_mismatch")
    if not material.payload:
        blocking_reasons.append("credential_vault_secret_payload_empty")
    if _contains_live_broker_secret(material.payload):
        blocking_reasons.append("credential_vault_live_broker_secret_forbidden")
    return CredentialVaultWritePlan(
        ready=not blocking_reasons,
        backend=profile.backend,
        credential_ref_configured=bool(credential_ref),
        sensitive_field_count=len(material.payload),
        expires_at_configured=material.expires_at is not None,
        blocking_reasons=tuple(blocking_reasons),
    )


def load_credential_vault_profile(
    env: Mapping[str, str],
) -> CredentialVaultProfile:
    backend_name = (
        env.get("CREDENTIAL_VAULT_BACKEND") or CredentialVaultBackend.DISABLED.value
    ).strip().lower()
    try:
        backend = CredentialVaultBackend(backend_name)
    except ValueError:
        backend = CredentialVaultBackend.UNKNOWN
    return CredentialVaultProfile(
        backend=backend,
        service_name=_blank_to_none(env.get("CREDENTIAL_VAULT_SERVICE")),
        kms_key_uri=_blank_to_none(env.get("CREDENTIAL_VAULT_KMS_KEY_URI")),
        local_runtime=_truthy(env.get("CREDENTIAL_VAULT_LOCAL_RUNTIME")),
        hosted_runtime=_truthy(env.get("CREDENTIAL_VAULT_HOSTED_RUNTIME")),
    )


def evaluate_credential_vault_readiness(
    profile: CredentialVaultProfile,
) -> CredentialVaultReadiness:
    blocking_reasons: list[str] = []
    if profile.backend == CredentialVaultBackend.DISABLED:
        blocking_reasons.append("credential_vault_disabled")
    elif profile.backend == CredentialVaultBackend.UNKNOWN:
        blocking_reasons.append("credential_vault_backend_unknown")
    elif profile.backend == CredentialVaultBackend.MACOS_KEYCHAIN:
        if not profile.local_runtime:
            blocking_reasons.append("credential_vault_local_runtime_required")
        if not profile.service_name:
            blocking_reasons.append("credential_vault_service_missing")
    elif profile.backend == CredentialVaultBackend.KMS:
        if not profile.hosted_runtime:
            blocking_reasons.append("credential_vault_hosted_runtime_required")
        if not profile.kms_key_uri:
            blocking_reasons.append("credential_vault_kms_key_uri_missing")
    return CredentialVaultReadiness(
        ready=not blocking_reasons,
        blocking_reasons=tuple(blocking_reasons),
        token_exchange_allowed=not blocking_reasons,
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_ref_part(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    if not normalized or not all(character.isalnum() or character == "-" for character in normalized):
        raise ValueError("credential vault reference parts must be non-empty slugs")
    return normalized


def _contains_live_broker_secret(payload: Mapping[str, Any]) -> bool:
    return any("trading" in str(key).lower() for key in payload)


def _write_result(
    *,
    plan: CredentialVaultWritePlan,
    written: bool,
) -> CredentialVaultWriteResult:
    return CredentialVaultWriteResult(
        written=written,
        backend=plan.backend,
        credential_ref_configured=plan.credential_ref_configured,
        sensitive_field_count=plan.sensitive_field_count,
        expires_at_configured=plan.expires_at_configured,
        blocking_reasons=plan.blocking_reasons,
    )


def _serialize_secret_material(material: CredentialVaultSecretMaterial) -> str:
    return json.dumps(
        {
            "payload": dict(material.payload),
            "expires_at": material.expires_at.isoformat() if material.expires_at else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _run_security_command(args: tuple[str, ...], *, input_text: str) -> None:
    subprocess.run(
        args,
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )
