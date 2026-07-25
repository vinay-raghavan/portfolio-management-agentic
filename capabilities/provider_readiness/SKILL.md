---
name: provider_readiness
description: Provider-readiness checks for configured data sources, import previews, reconciliation, and refresh status.
---

# Provider Readiness Capability

Use this capability before claiming configured provider data is available, fresh, or ready for downstream screeners and recommendations.

## Allowed tools

- `get_data_provider_health`
- `get_provider_refresh_readiness`
- `list_data_providers`
- `list_provider_import_jobs`
- `list_provider_import_previews`
- `list_provider_import_reconciliation`
- `list_provider_profiles`
- `list_provider_source_onboarding`
- `list_provider_source_templates`
- `validate_data_provider_imports`

## Context contract

Use provider catalog, import validation, dry-run previews, and refresh readiness. Never expose resolved local file paths, raw provider payloads, or credential values.

## Response contract

Return `ProviderReadinessResponse` with configured status, setup gaps, stale/backoff state, reconciliation gate, and safe next action.
