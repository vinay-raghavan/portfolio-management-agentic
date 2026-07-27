from __future__ import annotations

from portfolio_domain import (
    CredentialVaultBackend,
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
