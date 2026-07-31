# High-Level Architecture — Customer Feedback Portal

_Produced by the `business-study` agent · `/run-business-study`_

## Components

```
┌──────────────┐      HTTPS/JSON      ┌──────────────┐        SQL        ┌──────────────┐
│  React SPA   │ ───────────────────▶ │  Express API │ ─────────────────▶│  PostgreSQL  │
│  (Vite)      │ ◀─────────────────── │  (Node.js)   │ ◀─────────────────│              │
└──────────────┘                      └──────┬───────┘                    └──────────────┘
                                              │
                                              │ node-cron (weekly)
                                              ▼
                                       ┌──────────────┐
                                       │  SendGrid    │
                                       │  (digest)    │
                                       └──────────────┘
```

## Boundaries

- **Frontend (React SPA)** — owns presentation only; no business logic.
  Talks to the API exclusively over HTTPS/JSON.
- **Backend (Express API)** — owns auth, validation, business rules,
  status-transition logic. Single deployable service for MVP (no
  microservices — team size and 6-week timeline don't justify the
  complexity).
- **PostgreSQL** — system of record for users, feedback, categories,
  status history.
- **SendGrid** — outbound email only (digest + transactional
  notifications). No inbound processing.

## Data model (high level)

- `users (id, email, password_hash, role)`
- `feedback (id, user_id, title, description, category, status, created_at)`
- `feedback_comments (id, feedback_id, author_id, body, created_at)`

## Key decisions deferred to Design & Build

- Exact ORM (Prisma assumed, confirm in TRD)
- Rate-limiting middleware choice
- Index strategy for the admin triage query (status + created_at)

See `decisions/001-database-choice.md` for the one architectural decision
already locked in at this phase.
