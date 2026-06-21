# 0001: New Repository Boundary

## Status

Accepted.

## Context

The capstone should be a clean, standalone agentic project. The work needs ADK structure, MCP tooling, safety gates, evals, container packaging, and Kaggle-specific docs without mixing in private source, local data, or live-trading configuration.

## Decision

Use this repository as the capstone boundary. Keep it self-contained and public-safe.

## Consequences

- The capstone has a clean boundary and can be pushed to `github.com/vinay-raghavan/portfolio-management-agentic`.
- The repo can avoid accidental leakage of real data, credentials, local paths, or private internals.
- Any integration with external services must happen through documented contracts or explicit adapters.
- The first implementation slice should use offline-safe data and policy-controlled MCP tools.
