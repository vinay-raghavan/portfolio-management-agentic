# 0005 RAG Pattern Memory Boundary

## Status

Accepted.

## Context

The portfolio agent should eventually use existing trading patterns, strategy playbooks, research snippets, and capstone knowledge without hard-coding every explanation into prompts. Retrieval can improve usefulness, consistency, and citations, especially for pattern matching and recommendation explanations.

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

The first implementation slice should expose only read-only MCP tools such as `search_pattern_library`, `get_pattern_playbook`, and `cite_strategy_evidence`. Pattern cards should be versioned, public-safe, citation-backed, and testable.

## Consequences

- Algo and paper-trading flows remain deterministic and auditable.
- RAG improves explanation quality without becoming a hidden trading engine.
- Provider-neutral and platform-neutral safety still lives in MCP policy and tests.
- Future corpus ingestion requires redaction, provenance, retention, and quality checks.

## Verification

- Policy tests classify RAG tools as read-only.
- Contract tests assert citation payloads include source identifiers and version metadata.
- Eval cases check that pattern-grounded answers cite retrieved context and still refuse live trading.
- Security tests prove retrieval tools cannot expose secrets, local-only notes, or broker credentials.
