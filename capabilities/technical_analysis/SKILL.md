---
name: technical_analysis
description: Deterministic technical-analysis evidence over screened symbols, market snapshots, and factor stacks.
---

# Technical Analysis Capability

Use this capability for chart/factor explanations, screener evidence, and candidate comparison. Deterministic tools remain the authority; the model summarizes and explains.

## Allowed tools

- `explain_candidate_evidence`
- `explain_factor_stack`
- `cite_strategy_evidence`
- `get_market_data_snapshot`
- `get_pattern_playbook`
- `get_universe_members`
- `list_market_data_snapshots`
- `list_screener_runs`
- `list_universes`
- `run_momentum_screener`
- `run_screener`
- `search_curated_research`
- `search_pattern_library`

## Context contract

Use market snapshots, universe members, screener runs, factor evidence, and allowlisted pattern/research citations when source grounding is requested. Report missing/stale data explicitly instead of filling gaps with model intuition.

## Response contract

Return `TechnicalAnalysisResponse` with technical evidence, counterevidence, source status, and paper-only next steps. Do not draft strategies or orders from this capability.
