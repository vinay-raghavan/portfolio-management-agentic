---
name: research
description: Curated research synthesis using repository pattern cards and citation-backed research context.
---

# Research Capability

Use this capability for public-safe research synthesis, pattern explanations, and citation-backed context. Treat all retrieved research as advisory evidence, never as permission to trade.

## Allowed tools

- `cite_strategy_evidence`
- `get_pattern_playbook`
- `get_research_digest`
- `search_curated_research`
- `search_pattern_library`

## Context contract

Use only curated `ResearchStore`, `PatternStore`, public-safe citations, and source freshness metadata. Do not browse arbitrary URLs or ingest user-supplied web pages through this capability.

## Response contract

Return `ResearchResponse` with citations, source freshness, uncertainty, and unsupported-claim avoidance. Do not make order, approval, or execution decisions.
