# ADR 0002 — SCD2 historical schema

## Status

Accepted

## Context

Budget figures and contracts change over time and across sources. We need provenance and the ability to show “what was known when”.

## Decision

Use Slowly Changing Dimension Type 2 on mutable facts (`budget_line`, optionally `contract` status):

- `valid_from`, `valid_to`, `is_current`
- Every row carries `source_id` and `ingestion_run_id`
- Conflicting amounts from different sources create a `discrepancy` row; both facts are kept

## Consequences

- Queries for “current” filter `is_current = true`
- Re-ingestion closes previous versions instead of silent overwrite
- Storage grows with history (acceptable for MVP volumes)
