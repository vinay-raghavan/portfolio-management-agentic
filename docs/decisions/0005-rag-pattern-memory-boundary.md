# 0005 RAG Pattern Memory Boundary

## Status

Accepted.

## Context

The portfolio agent should use existing trading patterns, strategy playbooks, research snippets, and product knowledge without hard-coding every explanation into prompts. Retrieval can improve usefulness, consistency, and citations, especially for pattern matching and recommendation explanations.

The same feature can also create risk if retrieved text is treated as an instruction to trade, if stale pattern notes become hidden policy, or if private financial data or secrets enter the corpus.

## Decision

Add RAG as a read-only advisory layer, not as an execution layer.

Retrieved pattern memory may:

- Find candidate pattern cards and strategy playbooks.
- Provide citations for explanations and paper-strategy rationale.
- Surface counterevidence, risk notes, and prerequisites.
- Help agents navigate capstone docs, tool catalogs, and safety policy.

Retrieved pattern memory must not:

- Place or authorize live trades.
- Enable live strategies.
- Retrieve broker trading tokens or provider secrets.
- Directly create orders from unverified text.
- Bypass typed strategy schemas, backtests, risk checks, MCP policy, evals, or human approval.

The first implementation slice should expose only read-only MCP tools such as `search_pattern_library`, `get_pattern_playbook`, `cite_strategy_evidence`, and `explain_factor_stack`. Pattern cards should be versioned, public-safe, citation-backed, and testable.

For a functioning product, RAG starts as a curated pattern and reference layer,
not as an afterthought. The first store is file-backed through `PatternStore`
and `ResearchStore` interfaces. Runtime retrieval should use Postgres
full-text search over versioned, provenance-aware documents. Vector retrieval
stays deferred until a labeled retrieval benchmark proves a material quality
gain without weakening citation precision, recall, or latency.

The current runtime contract exposes `search_curated_research` as a read-only
MCP tool backed by the same fixture document contract as pattern cards. The
Postgres runtime path is tenant-scoped full-text search over `research_sources`
and `research_documents`; a migration keeps each document search field current
on insert or update, and `PostgresResearchStore` executes the same query through
an injectable connection factory for runtime wiring and production-like tests.
The MCP tool uses fixture retrieval by default and switches to Postgres only
when `PORTFOLIO_RESEARCH_STORE_BACKEND=postgres`,
`PORTFOLIO_RESEARCH_TENANT_ID`, and `PORTFOLIO_DATABASE_URL` are explicitly
configured. Misconfigured Postgres mode returns an error instead of falling
back to fixtures.
Source administration, arbitrary URL ingestion, and research-source refresh
configuration stay outside MCP/model-visible tools.

## Consequences

- Algo and paper-trading flows remain deterministic and auditable.
- RAG improves explanation quality without becoming a hidden trading engine.
- Provider-neutral and platform-neutral safety still lives in MCP policy and tests.
- Future corpus ingestion requires redaction, provenance, retention, and quality checks.
- Price candles, paper orders, simulated fills, approvals, and audit logs remain in structured stores, not vector memory.
- FYERS market/account data remains structured provider data and must not be embedded.

## Verification

- Policy tests classify RAG tools as read-only.
- Contract tests assert citation payloads include source identifiers and version metadata.
- Store contract tests assert pattern cards seed file-backed stores through the
  same document/provenance contract used by future runtime retrieval.
- Postgres contract tests assert tenant-scoped full-text search planning and
  execution, enabled-source filtering, available-document filtering, safe
  provenance mapping, blank/URL query rejection, and no vector retrieval path.
- Eval cases check that pattern-grounded answers cite retrieved context and still refuse live trading.
- Security tests prove retrieval tools cannot expose secrets, local-only notes, or broker credentials.
