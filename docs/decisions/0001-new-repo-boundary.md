# 0001: New Repository Boundary

## Status

Accepted.

## Context


## Decision

Create a new local repository folder at:



## Consequences

- The capstone has a clean boundary and can be pushed to `github.com/vinay-raghavan/portfolio-management-agentic`.
- The public repo can avoid accidental leakage of real data, credentials, or old app internals.
- Any integration with the old app must happen through documented contracts or explicit adapters.
- The first implementation slice should use demo data and policy-controlled MCP tools.

