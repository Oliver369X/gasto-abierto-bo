# ADR 0001 — Lean stack for MVP

## Status

Accepted

## Context

The product vision mentions Kafka, Airflow, Elasticsearch and Kubernetes. For an early open-source project with few maintainers, that stack is expensive to operate and hard for contributors to run locally.

## Decision

Ship MVP on Docker Compose with:

- FastAPI + PostgreSQL + Redis/ARQ + MinIO + Playwright + Next.js

Keep stable interfaces (`SourceAdapter`, `JobEnvelope`) so Kafka/Airflow/ES can be added in Phase 2 without rewriting parsers.

## Consequences

- `docker compose up` is the contributor path.
- No K8s manifests in MVP.
- Nightly live scrapes are optional (`workflow_dispatch`), not required for CI green.
