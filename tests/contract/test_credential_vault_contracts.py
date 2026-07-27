from __future__ import annotations

import pytest

from portfolio_domain import (
    CredentialVaultBackend,
    CredentialVaultSecretMaterial,
    CredentialVaultWriteResult,
    FyersConnection,
    KmsCredentialVaultWriter,
    MacOSKeychainCredentialVaultWriter,
    build_credential_vault_writer,
    build_credential_vault_ref,
    evaluate_credential_vault_readiness,
    load_credential_vault_profile,
    plan_credential_vault_write,
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


def test_credential_vault_write_plan_redacts_secret_material() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "macos_keychain",
            "CREDENTIAL_VAULT_SERVICE": "portfolio-agentic-fyers",
            "CREDENTIAL_VAULT_LOCAL_RUNTIME": "true",
        }
    )
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.MACOS_KEYCHAIN,
    )
    material = CredentialVaultSecretMaterial(
        payload={
            "access_token": "fyers-access-token-secret",
            "refresh_token": "fyers-refresh-token-secret",
        },
    )

    plan = plan_credential_vault_write(
        profile=profile,
        credential_ref=credential_ref,
        material=material,
    )

    serialized = f"{material!r} {plan.to_dict()}".lower()
    assert plan.ready is True
    assert plan.blocking_reasons == ()
    assert plan.to_dict()["sensitive_field_count"] == 2
    assert plan.to_dict()["credential_ref_configured"] is True
    assert "fyers-access-token-secret" not in serialized
    assert "fyers-refresh-token-secret" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized


def test_credential_vault_write_plan_fails_closed_for_disabled_or_mismatched_backend() -> None:
    material = CredentialVaultSecretMaterial(payload={"access_token": "secret"})
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.MACOS_KEYCHAIN,
    )

    disabled_plan = plan_credential_vault_write(
        profile=load_credential_vault_profile({}),
        credential_ref=credential_ref,
        material=material,
    )
    kms_plan = plan_credential_vault_write(
        profile=load_credential_vault_profile(
            {
                "CREDENTIAL_VAULT_BACKEND": "kms",
                "CREDENTIAL_VAULT_KMS_KEY_URI": "projects/p/locations/l/keyRings/r/cryptoKeys/k",
                "CREDENTIAL_VAULT_HOSTED_RUNTIME": "true",
            }
        ),
        credential_ref=credential_ref,
        material=material,
    )

    assert disabled_plan.ready is False
    assert "credential_vault_disabled" in disabled_plan.blocking_reasons
    assert kms_plan.ready is False
    assert "credential_vault_ref_backend_mismatch" in kms_plan.blocking_reasons


def test_credential_vault_write_plan_rejects_live_broker_secret_material() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "macos_keychain",
            "CREDENTIAL_VAULT_SERVICE": "portfolio-agentic-fyers",
            "CREDENTIAL_VAULT_LOCAL_RUNTIME": "true",
        }
    )
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.MACOS_KEYCHAIN,
    )
    plan = plan_credential_vault_write(
        profile=profile,
        credential_ref=credential_ref,
        material=CredentialVaultSecretMaterial(payload={"trading_token": "secret"}),
    )

    assert plan.ready is False
    assert "credential_vault_live_broker_secret_forbidden" in plan.blocking_reasons
    serialized = str(plan.to_dict()).lower()
    assert "trading_token" not in serialized
    assert "secret" not in serialized.replace("credential_vault_live_broker_secret_forbidden", "")


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


def test_macos_keychain_writer_passes_secret_material_on_stdin_not_arguments() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "macos_keychain",
            "CREDENTIAL_VAULT_SERVICE": "portfolio-agentic-fyers",
            "CREDENTIAL_VAULT_LOCAL_RUNTIME": "true",
        }
    )
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.MACOS_KEYCHAIN,
    )
    material = CredentialVaultSecretMaterial(
        payload={
            "access_token": "fyers-access-token-secret",
            "refresh_token": "fyers-refresh-token-secret",
        },
    )
    captured: dict[str, object] = {}

    def runner(args: tuple[str, ...], *, input_text: str) -> None:
        captured["args"] = args
        captured["input_text"] = input_text

    writer = MacOSKeychainCredentialVaultWriter(
        profile=profile,
        command_runner=runner,
    )
    result = writer.write(credential_ref=credential_ref, material=material)

    args = captured["args"]
    assert isinstance(result, CredentialVaultWriteResult)
    assert result.written is True
    assert result.backend == CredentialVaultBackend.MACOS_KEYCHAIN
    assert result.credential_ref_configured is True
    assert result.to_dict()["sensitive_field_count"] == 2
    assert "/usr/bin/security" in args
    assert "add-generic-password" in args
    assert "--stdin" in args
    assert "-w" not in args
    assert "portfolio-agentic-fyers" in args
    assert credential_ref in args
    serialized_args = str(args).lower()
    serialized_result = f"{result!r} {result.to_dict()}".lower()
    assert "fyers-access-token-secret" not in serialized_args
    assert "fyers-refresh-token-secret" not in serialized_args
    assert "fyers-access-token-secret" not in serialized_result
    assert "fyers-refresh-token-secret" not in serialized_result
    assert "access_token" not in serialized_result
    assert "refresh_token" not in serialized_result
    assert "fyers-access-token-secret" in captured["input_text"]


def test_credential_vault_writer_fails_closed_when_write_plan_is_not_ready() -> None:
    profile = load_credential_vault_profile({})
    material = CredentialVaultSecretMaterial(payload={"access_token": "secret"})

    writer = build_credential_vault_writer(profile)
    result = writer.write(
        credential_ref="credential-vault://disabled/fyers/not-real",
        material=material,
    )

    assert result.written is False
    assert result.backend == CredentialVaultBackend.DISABLED
    assert "credential_vault_disabled" in result.blocking_reasons
    assert "secret" not in str(result.to_dict()).lower()


def test_kms_writer_uses_key_uri_without_returning_plaintext() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "kms",
            "CREDENTIAL_VAULT_KMS_KEY_URI": "projects/p/locations/l/keyRings/r/cryptoKeys/k",
            "CREDENTIAL_VAULT_HOSTED_RUNTIME": "true",
        }
    )
    credential_ref = build_credential_vault_ref(
        tenant_id="tenant-1",
        provider="fyers",
        purpose="data_access_token",
        subject_hash="sha256:user",
        backend=CredentialVaultBackend.KMS,
    )
    material = CredentialVaultSecretMaterial(payload={"access_token": "hosted-secret"})
    captured: dict[str, object] = {}

    def kms_writer(*, key_uri: str, credential_ref: str, plaintext: bytes) -> str:
        captured["key_uri"] = key_uri
        captured["credential_ref"] = credential_ref
        captured["plaintext"] = plaintext
        return "kms://ciphertext-handle"

    writer = KmsCredentialVaultWriter(profile=profile, kms_writer=kms_writer)
    result = writer.write(credential_ref=credential_ref, material=material)

    assert result.written is True
    assert result.backend == CredentialVaultBackend.KMS
    assert result.credential_ref_configured is True
    assert captured["key_uri"] == profile.kms_key_uri
    assert captured["credential_ref"] == credential_ref
    assert b"hosted-secret" in captured["plaintext"]
    serialized_result = f"{result!r} {result.to_dict()}".lower()
    assert "hosted-secret" not in serialized_result
    assert "access_token" not in serialized_result
    assert "kms://ciphertext-handle" not in serialized_result
