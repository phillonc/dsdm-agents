# Feasibility Assessment — Customer Feedback Portal

_Produced by the `feasibility` agent · `/run-feasibility` · see `guide.md` §4.1_

## Executive summary

A web-based portal for collecting, triaging, and reporting on customer
feedback. Users submit feedback; admins triage and respond; a weekly digest
summarises open items to stakeholders. Standard CRUD + auth + scheduled-job
stack — no novel technology risk at this scale.

## Recommendation: GO (confidence: 87%)

## Technical feasibility

| Area | Assessment |
|---|---|
| Frontend | React (Vite) SPA — team has prior experience |
| Backend | Node.js/Express REST API — well-understood, fast to scaffold |
| Data | PostgreSQL — relational model fits feedback/category/user well |
| Auth | JWT session auth, bcrypt password hashing — no SSO requirement yet |
| Email | Managed transactional provider (SendGrid) for the weekly digest |
| Complexity | Medium — no distributed systems, no real-time requirement |

## Top risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | 6-week timeline vs. 2-person team | High | Cut Could-Have scope first; timebox weekly; MVP = Must-Haves only |
| 2 | Weekly email digest delivery reliability | Medium | Use a managed transactional email provider (SendGrid) with delivery webhooks |
| 3 | No auth provider decided yet | Medium | Default to email+password with bcrypt; defer SSO to a later release |
| 4 | Admin triage UX undefined | Low | Cover in Functional Model prototyping before Design & Build starts |

## DSDM fit

High. The scope is well-bounded, the team is small, and the 6-week window
maps cleanly onto 3 timeboxes (foundation → triage → hardening). Iterative,
timeboxed delivery suits this project better than a single big-bang release.

## Suggested technology approach

React (Vite) SPA → Express REST API → PostgreSQL via Prisma. `node-cron`
scheduled job for the weekly digest, dispatched through SendGrid. JWT
session auth with bcrypt-hashed passwords.

## Required inputs for the next phase (Product Management)

- Confirm auth strategy (email/password vs. SSO) — feasibility assumes
  email/password for MVP.
- Confirm digest cadence and recipient list ownership (who maintains the
  distribution list).

---

**Next:** `/run-product-management` — see `../PRODUCT_REQUIREMENTS.md`.
