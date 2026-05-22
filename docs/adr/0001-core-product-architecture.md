# ADR-0001: Core Product Architecture Skeleton

Date: 2026-05-22
Status: Accepted

## Context

We need a baseline architecture for a creator-led growth product with:

- authentication-ready user model
- content ingestion and publishing primitives
- growth metrics capture
- deployable path to staging from main branch

## Decision

We adopt a modular monolith for Week 1-4 with clear service boundaries in code:

- `users` domain: identity and account profile
- `content` domain: creator content metadata and lifecycle
- `metrics` domain: event counters and attribution primitives

API boundary:

- REST HTTP API for all baseline entities
- schema-first persistence via Prisma

Persistence:

- SQLite for local/dev speed
- Postgres-compatible schema for staging/prod migration

Delivery:

- GitHub Actions CI for lint/test gates
- staging deployment path documented with containerized runtime and environment-variable based config

## Tradeoffs

Pros:

- fast iteration with low operational overhead
- clear migration path to service extraction later
- easy onboarding for first engineering hires

Cons:

- tighter coupling than independent services
- scaling bottlenecks if high-throughput workloads arrive early

## Consequences

- Domain modules must maintain clear boundaries despite monolith packaging.
- New features should attach to one domain first and only cross boundaries through explicit interfaces.
- By Week 5+, analytics event throughput should be reviewed for extraction into pipeline-specific services.
