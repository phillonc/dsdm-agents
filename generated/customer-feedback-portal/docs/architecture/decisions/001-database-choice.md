# ADR 001: PostgreSQL over MongoDB

_Produced by the `dev-lead` agent · `/run-design-build`_

## Status

Accepted

## Context

Feedback portal data is inherently relational: users own feedback items,
feedback items belong to categories, and status changes form a history
that admins need to query and filter across (by status, category, date,
assignee). We need to choose a primary datastore before Design & Build
starts generating code.

## Decision

Use **PostgreSQL** as the system of record, accessed via Prisma from the
Express API.

## Rationale

- The feedback → category → status-history relationship is a natural fit
  for a relational schema with foreign keys and indexes, not a document
  model.
- The admin dashboard's core query (filter by status + category + date
  range, sorted) is exactly what relational indexes are built for.
- Team has prior PostgreSQL experience (per Feasibility's technology
  assessment) — no ramp-up cost.
- No requirement in the PRD implies schema-less or high write-throughput
  needs that would favour a document store.

## Consequences

- Schema migrations become a first-class concern — Prisma migrations will
  be checked in under `src/backend/prisma/migrations/`.
- Reporting queries (weekly digest counts) can be plain SQL aggregates
  instead of an application-side map-reduce.
- If a future feature needs flexible/unstructured attachments metadata, a
  `jsonb` column is available without introducing a second datastore.

## Alternatives considered

| Option | Rejected because |
|---|---|
| MongoDB | No schema-flexibility requirement; would add operational overhead without benefit |
| SQLite | Fine for local dev, insufficient for the 500-concurrent-user target |
