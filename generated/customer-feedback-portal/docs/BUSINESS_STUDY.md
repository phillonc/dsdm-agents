# Business Study — Customer Feedback Portal

_Produced by the `business-study` agent · `/run-business-study` · see `guide.md` §4.3_

## Business area definition

Current process: feedback arrives via email, phone, and social media with
no shared tracking. This project consolidates intake into one portal with
a defined triage workflow.

## Stakeholders

| Stakeholder | Role | Interest |
|---|---|---|
| VP Customer Success | Sponsor | Faster response times, adoption |
| Customer Experience Manager | Product Owner | Feature scope, prioritisation |
| Support team | Primary users (admin side) | Usable triage workflow |
| Product managers | Consumers of digest | Categorised, trustworthy data |
| Customers | Primary users (submission side) | Easy submission, visible status |

## Prioritised requirements (MoSCoW)

Must: 6 · Should: 3 · Could: 2 · Won't: 2 — see `PRODUCT_REQUIREMENTS.md` §6
for the full itemised list. Every requirement below carries its MoSCoW tag
into Jira as a `MoSCoW-*` label when Jira sync is enabled.

## High-level architecture

See `architecture/HIGH_LEVEL_ARCHITECTURE.md`.

## Timebox plan

| Timebox | Weeks | Scope | Exit criteria |
|---|---|---|---|
| Timebox 1 | 1–2 | Auth + feedback submission | User can register, log in, submit feedback |
| Timebox 2 | 3–4 | Admin triage + categories (MVP complete) | All 6 Must-Haves shippable to staging |
| Timebox 3 | 5–6 | Digest emails, hardening, Should-Have stretch | Weekly digest live; search/export/notifications if time allows |

## Risk log

5 entries — see `RISK_LOG.md`. 4 carried forward from Feasibility, 1 new:
the weekly digest cron job has no recovery path if the server restarts
mid-run.

---

**Next:** `/run-functional-model` to prototype the triage UI before
`/run-design-build`.
