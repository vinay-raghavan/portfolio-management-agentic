from __future__ import annotations

import pytest

from portfolio_domain import (
    CredentialVaultBackend,
    FyersConnection,
    build_credential_vault_ref,
    evaluate_credential_vault_readiness,
    load_credential_vault_profile,
)


def test_credential_vault_defaults_to_disabled_fail_closed_without_secrets() -> None:
    profile = load_credential_vault_profile({})
    readiness = evaluate_credential_vault_readiness(profile)

    assert profile.backend == CredentialVaultBackend.DISABLED
    assert readiness.ready is False
    assert "credential_vault_disabled" in readiness.blocking_reasons
    assert "token" not in str(profile.to_dict()).lower()
    assert "secret" not in str(readiness.to_dict()).lower()


def test_unknown_credential_vault_backend_fails_closed() -> None:
    profile = load_credential_vault_profile({"CREDENTIAL_VAULT_BACKEND": "plaintext"})
    readiness = evaluate_credential_vault_readiness(profile)

    assert profile.backend == CredentialVaultBackend.UNKNOWN
    assert readiness.ready is False
    assert "credential_vault_backend_unknown" in readiness.blocking_reasons


def test_credential_vault_refs_are_scoped_and_redacted_from_connection_payloads() -> None:
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.MACOS_KEYCHAIN,
    )
    connection = FyersConnection.disconnected(
        tenant_id="tenant-1",
        user_id="user-1",
        connection_id="fyers-connection-1",
    ).with_credential_ref(credential_ref=credential_ref)

    payload = connection.to_dict()
    serialized = str(payload).lower()

    assert credential_ref.startswith("credential-vault://macos_keychain/fyers/")
    assert "data_access_token" not in credential_ref
    assert connection.credential_ref == credential_ref
    assert payload["credential_ref_configured"] is True
    assert "credential_ref" not in payload
    assert credential_ref not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized


def test_credential_vault_refs_require_real_vault_backend() -> None:
    with pytest.raises(ValueError, match="vault backend"):
        build_credential_vault_ref(
            tenant_id="tenant-1",
            provider="fyers",
            purpose="data_access_token",
            subject_hash="sha256:user",
            backend=CredentialVaultBackend.DISABLED,
        )


def test_macos_keychain_vault_requires_service_name_and_local_runtime() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "macos_keychain",
            "CREDENTIAL_VAULT_SERVICE": "portfolio-agentic-fyers",
            "CREDENTIAL_VAULT_LOCAL_RUNTIME": "true",
        }
    )
    readiness = evaluate_credential_vault_readiness(profile)

    assert profile.backend == CredentialVaultBackend.MACOS_KEYCHAIN
    assert profile.service_name == "portfolio-agentic-fyers"
    assert readiness.ready is True
    assert readiness.blocking_reasons == ()


def test_kms_vault_requires_key_uri_and_hosted_runtime() -> None:
    missing = evaluate_credential_vault_readiness(
        load_credential_vault_profile(
            {
                "CREDENTIAL_VAULT_BACKEND": "kms",
                "CREDENTIAL_VAULT_HOSTED_RUNTIME": "true",
            }
        )
    )
    ready = evaluate_credential_vault_readiness(
        load_credential_vault_profile(
            {
                "CREDENTIAL_VAULT_BACKEND": "kms",
                "CREDENTIAL_VAULT_KMS_KEY_URI": "projects/p/locations/l/keyRings/r/cryptoKeys/k",
                "CREDENTIAL_VAULT_HOSTED_RUNTIME": "true",
            }
        )
    )

    assert missing.ready is False
    assert "credential_vault_kms_key_uri_missing" in missing.blocking_reasons
    assert ready.ready is True
