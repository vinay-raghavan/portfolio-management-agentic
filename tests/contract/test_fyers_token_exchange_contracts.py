from __future__ import annotations

from datetime import UTC, datetime, timedelta

from portfolio_domain import (
    CredentialVaultBackend,
    FyersConnection,
    build_credential_vault_writer,
    exchange_fyers_auth_code_to_vault,
    load_credential_vault_profile,
)

TENANT_ID = "tenant-fyers-token-exchange"
USER_ID = "user-fyers-token-exchange"
NOW = datetime(2026, 7, 28, 9, 30, tzinfo=UTC)


class _FakeFyersTokenExchangeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    def exchange_auth_code(
        self,
        *,
        auth_code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "auth_code": auth_code,
                "code_verifier": code_verifier,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            }
        )
        return {
            "access_token": "fyers-access-token-secret",
            "refresh_token": "fyers-refresh-token-secret",
            "expires_at": (NOW + timedelta(hours=8)).isoformat(),
        }


def test_fyers_auth_code_exchange_writes_token_material_to_vault_without_leaks() -> None:
    profile = load_credential_vault_profile(
        {
            "CREDENTIAL_VAULT_BACKEND": "macos_keychain",
            "CREDENTIAL_VAULT_SERVICE": "portfolio-agentic-fyers",
            "CREDENTIAL_VAULT_LOCAL_RUNTIME": "true",
        }
    )
    captured: dict[str, object] = {}

    def command_runner(args: tuple[str, ...], *, input_text: str) -> None:
        captured["args"] = args
        captured["input_text"] = input_text

    connection = FyersConnection.disconnected(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        connection_id="fyers-connection-1",
        now=NOW,
    )
    exchange_client = _FakeFyersTokenExchangeClient()
    writer = build_credential_vault_writer(profile, command_runner=command_runner)

    result = exchange_fyers_auth_code_to_vault(
        connection=connection,
        auth_code="browser-auth-code",
        code_verifier="pkce-verifier-from-server-cache",
        client_id="FYERSDATA-100",
        client_secret="fyers-client-secret",
        redirect_uri="https://app.example.test/fyers/callback",
        credential_vault_profile=profile,
        credential_vault_writer=writer,
        exchange_client=exchange_client,
        now=NOW,
    )

    payload = result.to_dict()
    connected = result.connection
    serialized = f"{payload} {connected.to_dict()} {captured['args']}".lower()

    assert result.status == "connected"
    assert connected.status == "connected"
    assert connected.credential_status == "vault_reference_configured"
    assert connected.credential_ref is not None
    assert connected.credential_ref.startswith("credential-vault://macos_keychain/fyers/")
    assert payload["connection"]["credential_ref_configured"] is True
    assert payload["vault_write"]["written"] is True
    assert payload["vault_write"]["backend"] == CredentialVaultBackend.MACOS_KEYCHAIN.value
    assert payload["token_exchange"]["attempted"] is True
    assert payload["token_exchange"]["sensitive_field_count"] == 2
    assert exchange_client.calls == [
        {
            "auth_code": "browser-auth-code",
            "code_verifier": "pkce-verifier-from-server-cache",
            "client_id": "FYERSDATA-100",
            "client_secret": "fyers-client-secret",
            "redirect_uri": "https://app.example.test/fyers/callback",
        }
    ]
    assert "fyers-access-token-secret" in str(captured["input_text"])
    assert "fyers-refresh-token-secret" in str(captured["input_text"])
    assert "fyers-access-token-secret" not in serialized
    assert "fyers-refresh-token-secret" not in serialized
    assert "fyers-client-secret" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "client_secret" not in serialized
    assert "trading_token" not in serialized


def test_fyers_auth_code_exchange_fails_closed_when_vault_is_disabled() -> None:
    profile = load_credential_vault_profile({})
    exchange_client = _FakeFyersTokenExchangeClient()
    connection = FyersConnection.disconnected(
        tenant_id=TENANT_ID,
        user_id=USER_ID,
        connection_id="fyers-connection-1",
        now=NOW,
    )

    result = exchange_fyers_auth_code_to_vault(
        connection=connection,
        auth_code="browser-auth-code",
        code_verifier="pkce-verifier-from-server-cache",
        client_id="FYERSDATA-100",
        client_secret="fyers-client-secret",
        redirect_uri="https://app.example.test/fyers/callback",
        credential_vault_profile=profile,
        credential_vault_writer=build_credential_vault_writer(profile),
        exchange_client=exchange_client,
        now=NOW,
    )

    payload = result.to_dict()
    serialized = f"{payload} {result.connection.to_dict()}".lower()

    assert result.status == "blocked"
    assert result.connection.status == "reconnect_required"
    assert result.connection.credential_status == "token_exchange_not_configured"
    assert "credential_vault_disabled" in result.blocking_reasons
    assert payload["token_exchange"]["attempted"] is False
    assert exchange_client.calls == []
    assert "fyers-client-secret" not in serialized
    assert "access_token" not in serialized
    assert "client_secret" not in serialized
