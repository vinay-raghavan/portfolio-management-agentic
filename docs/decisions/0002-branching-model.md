# 0002: Branching Model

## Status

Accepted.

## Context

The project needs standard Git practices before agent scaffolding starts. `main` should not be used for day-to-day work because it represents releasable history.

## Decision

Use a Gitflow-style branching model:

- `main`: release-only branch.
- `develop`: default integration branch.
- `feature/*`: feature work branched from `develop` and merged back into `develop`.
- `fix/*`: defect fixes branched from `develop` and merged back into `develop`.
- `release/*`: optional release stabilization branches before merging into `main`.

The GitHub repository default branch is `develop`.

Current active branch for scaffold work:

`feature/agentic-scaffold`

## Consequences

- Future agent work must begin from `develop` or a current topic branch based on `develop`.
- No development commits should be made directly on `main`.
- Release merges into `main` should happen intentionally after checks, evals, review, and release-gate evidence.
