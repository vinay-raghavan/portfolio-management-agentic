from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


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
