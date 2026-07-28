from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .credential_vault import (
    CredentialVaultProfile,
    CredentialVaultSecretMaterial,
    CredentialVaultWriteResult,
    build_credential_vault_ref,
    evaluate_credential_vault_readiness,
)
from .fyers_integration import FyersConnection, utc_now


class FyersAuthCodeExchangeClient(Protocol):
    """Data-only FYERS OAuth auth-code exchange client.

    Implementations must not expose order-placement methods or return provider
    token material outside this process boundary.
    """

    def exchange_auth_code(
        self,
        *,
        auth_code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
    ) -> Mapping[str, object]:
        ...


@dataclass(frozen=True, repr=False)
class FyersTokenExchangeResult:
    status: str
    connection: FyersConnection
    vault_write_result: CredentialVaultWriteResult | None
    blocking_reasons: tuple[str, ...]
    token_exchange_attempted: bool
    sensitive_field_count: int
    expires_at_configured: bool

    def __repr__(self) -> str:
        return (
            "FyersTokenExchangeResult("
            f"status={self.status!r}, "
            f"connection_status={self.connection.status!r}, "
            f"blocking_reasons={self.blocking_reasons!r}, "
            f"token_exchange_attempted={self.token_exchange_attempted}, "
            f"sensitive_field_count={self.sensitive_field_count}, "
            f"expires_at_configured={self.expires_at_configured})"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "connection": self.connection.to_dict(),
            "vault_write": (
                self.vault_write_result.to_dict()
                if self.vault_write_result is not None
                else {
                    "written": False,
                    "backend": "disabled",
                    "credential_ref_configured": False,
                    "sensitive_field_count": 0,
                    "expires_at_configured": False,
                    "blocking_reasons": list(self.blocking_reasons),
                }
            ),
            "blocking_reasons": list(self.blocking_reasons),
            "token_exchange": {
                "attempted": self.token_exchange_attempted,
                "sensitive_field_count": self.sensitive_field_count,
                "expires_at_configured": self.expires_at_configured,
            },
        }


class FyersSdkAuthCodeExchangeClient:
    """FYERS SDK adapter scoped to OAuth token exchange only."""

    def exchange_auth_code(
        self,
        *,
        auth_code: str,
        code_verifier: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
    ) -> Mapping[str, object]:
        if not client_secret:
            raise ValueError("fyers_data_app_private_config_missing")
        from fyers_apiv3 import fyersModel

        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=client_secret,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        if not isinstance(response, Mapping):
            raise ValueError("fyers_token_exchange_response_invalid")
        return response


def exchange_fyers_auth_code_to_vault(
    *,
    connection: FyersConnection,
    auth_code: str,
    code_verifier: str,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    credential_vault_profile: CredentialVaultProfile,
    credential_vault_writer: Any,
    exchange_client: FyersAuthCodeExchangeClient,
    now: datetime | None = None,
) -> FyersTokenExchangeResult:
    """Exchange a FYERS auth code and write provider tokens to the vault.

    Only redacted status, counts and opaque connection state are returned. Token
    values and their provider field names must remain inside the exchange/vault
    boundary.
    """
    timestamp = now or utc_now()
    readiness = evaluate_credential_vault_readiness(credential_vault_profile)
    if not readiness.ready:
        return _blocked_result(
            connection=connection.callback_recorded(now=timestamp),
            blocking_reasons=readiness.blocking_reasons,
            token_exchange_attempted=False,
            sensitive_field_count=0,
            expires_at_configured=False,
        )

    config_blockers = _token_exchange_config_blockers(
        auth_code=auth_code,
        code_verifier=code_verifier,
        client_id=client_id,
        redirect_uri=redirect_uri,
    )
    if config_blockers:
        return _blocked_result(
            connection=connection.callback_recorded(now=timestamp),
            blocking_reasons=tuple(config_blockers),
            token_exchange_attempted=False,
            sensitive_field_count=0,
            expires_at_configured=False,
        )

    try:
        token_response = exchange_client.exchange_auth_code(
            auth_code=auth_code,
            code_verifier=code_verifier,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except Exception:
        return _blocked_result(
            connection=connection.callback_recorded(now=timestamp),
            blocking_reasons=("fyers_data_app_exchange_failed",),
            token_exchange_attempted=True,
            sensitive_field_count=0,
            expires_at_configured=False,
        )

    material, blockers = _secret_material_from_token_response(
        token_response,
        now=timestamp,
    )
    if blockers:
        return _blocked_result(
            connection=connection.callback_recorded(now=timestamp),
            blocking_reasons=tuple(blockers),
            token_exchange_attempted=True,
            sensitive_field_count=0,
            expires_at_configured=False,
        )

    credential_ref = build_credential_vault_ref(
        tenant_id=connection.tenant_id,
        provider=connection.provider,
        purpose="data_access_token",
        subject_hash=connection.user_id_hash,
        backend=credential_vault_profile.backend,
    )
    try:
        write_result = credential_vault_writer.write(
            credential_ref=credential_ref,
            material=material,
        )
    except Exception:
        return _blocked_result(
            connection=connection.callback_recorded(now=timestamp),
            blocking_reasons=("credential_vault_write_failed",),
            token_exchange_attempted=True,
            sensitive_field_count=len(material.payload),
            expires_at_configured=material.expires_at is not None,
        )

    if not write_result.written:
        return FyersTokenExchangeResult(
            status="blocked",
            connection=connection.callback_recorded(now=timestamp),
            vault_write_result=write_result,
            blocking_reasons=write_result.blocking_reasons,
            token_exchange_attempted=True,
            sensitive_field_count=write_result.sensitive_field_count,
            expires_at_configured=write_result.expires_at_configured,
        )

    return FyersTokenExchangeResult(
        status="connected",
        connection=connection.with_credential_ref(
            credential_ref=credential_ref,
            expires_at=material.expires_at,
            now=timestamp,
        ),
        vault_write_result=write_result,
        blocking_reasons=(),
        token_exchange_attempted=True,
        sensitive_field_count=write_result.sensitive_field_count,
        expires_at_configured=write_result.expires_at_configured,
    )


def _blocked_result(
    *,
    connection: FyersConnection,
    blocking_reasons: tuple[str, ...],
    token_exchange_attempted: bool,
    sensitive_field_count: int,
    expires_at_configured: bool,
) -> FyersTokenExchangeResult:
    return FyersTokenExchangeResult(
        status="blocked",
        connection=connection,
        vault_write_result=None,
        blocking_reasons=blocking_reasons,
        token_exchange_attempted=token_exchange_attempted,
        sensitive_field_count=sensitive_field_count,
        expires_at_configured=expires_at_configured,
    )


def _token_exchange_config_blockers(
    *,
    auth_code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
) -> list[str]:
    blockers: list[str] = []
    if not auth_code.strip():
        blockers.append("fyers_browser_authorization_missing")
    if not code_verifier.strip():
        blockers.append("fyers_pkce_verifier_missing")
    if not client_id.strip() or client_id == "configure-fyers-data-app":
        blockers.append("fyers_data_app_client_missing")
    if not redirect_uri.strip():
        blockers.append("fyers_redirect_uri_missing")
    return blockers


def _secret_material_from_token_response(
    response: Mapping[str, object],
    *,
    now: datetime,
) -> tuple[CredentialVaultSecretMaterial, tuple[str, ...]]:
    lowered_keys = {str(key).lower() for key in response}
    if any("trading" in key for key in lowered_keys):
        return CredentialVaultSecretMaterial(payload={}), (
            "fyers_live_broker_material_forbidden",
        )

    payload: dict[str, object] = {}
    primary_value = response.get("access_token")
    secondary_value = response.get("refresh_token")
    if isinstance(primary_value, str) and primary_value.strip():
        payload["access_token"] = primary_value
    if isinstance(secondary_value, str) and secondary_value.strip():
        payload["refresh_token"] = secondary_value
    if "access_token" not in payload:
        return CredentialVaultSecretMaterial(payload={}), ("fyers_data_token_missing",)
    expires_at = _parse_expires_at(response.get("expires_at")) or _derive_expires_at(
        response.get("expires_in"),
        now=now,
    )
    return CredentialVaultSecretMaterial(payload=payload, expires_at=expires_at), ()


def _parse_expires_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _derive_expires_at(value: object, *, now: datetime) -> datetime | None:
    try:
        seconds = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return now + timedelta(seconds=seconds)
