---
name: fyers_data
description: Read-only broker-data context for FYERS-style provider snapshots without credentials or live-order authority.
---

# FYERS Data Capability

Use this capability for read-only provider status, normalized snapshot freshness, and broker-data availability explanations. FYERS credentials and tokens must never enter prompts, traces, tool arguments, or responses.

## Allowed tools

- `get_data_provider_health`
- `get_market_data_snapshot`
- `get_provider_refresh_readiness`
- `list_data_providers`
- `list_market_data_snapshots`
- `list_provider_import_jobs`
- `list_provider_import_reconciliation`
- `list_provider_profiles`
- `validate_data_provider_imports`

## Context contract

Use `ProviderSnapshotEnvelope`, `BrokerAccountSnapshot`, provider health, and refresh readiness. Treat unavailable provider responses as unavailable, not as empty holdings, zero funds, or Yahoo fallback data.

## Response contract

Return `FyersDataResponse` with provider status, freshness, as-of time, source status, and redacted identifiers. Do not expose credentials or use mutation/live-order tools.
