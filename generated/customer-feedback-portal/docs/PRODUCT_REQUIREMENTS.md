# Product Requirements Document — Customer Feedback Portal

_Produced by the `product-manager` agent · `/run-product-management` · see `guide.md` §4.2_

## 1. Executive summary

A web portal that consolidates customer feedback collection (currently
spread across email, phone, and social media) into a single system, so the
support team can triage faster and product managers can see prioritised,
categorised feedback instead of scattered messages.

## 2. Problem statement

Feedback arrives through disconnected channels with no shared status
tracking, no categorisation, and no reporting cadence. Response times are
inconsistent and product decisions aren't informed by aggregated feedback.

## 3. Product vision

A single place customers submit feedback and admins triage it, with a
weekly digest keeping stakeholders informed without anyone having to ask.

## 4. Target audience & personas

- **Customer** — submits feedback, expects acknowledgement and eventual resolution.
- **Support agent** — triages incoming feedback, assigns category/status.
- **Product manager** — reads the weekly digest, uses categorised feedback for roadmap input.

## 5. Business objectives & success metrics

| Objective | Metric | Target |
|---|---|---|
| Faster response | Time to first triage | < 24 hours |
| Adoption | Feedback submissions via portal vs. legacy channels | > 60% within month 1 |
| Reporting cadence | Weekly digest delivery | 100% on-time |

## 6. Feature specifications (MoSCoW)

### Must Have
1. User registration and login (email + password)
2. Feedback submission form (title, description, category)
3. Admin dashboard — list + filter feedback
4. Admin triage — status transitions (New → In Review → In Progress → Resolved → Closed)
5. Feedback categories (Bug Report, Feature Request, General Feedback, Complaint)
6. Weekly email digest to stakeholders

### Should Have
7. Search and filter by category/status/date
8. CSV export of feedback
9. In-app notification center (read/unread)

### Could Have
10. Sentiment tagging (basic keyword-based, not full NLP)
11. Public roadmap board driven by upvoted feature requests

### Won't Have (this release)
- Native mobile app (iOS/Android)
- Multi-language support

## 7. User journeys

- **Submit feedback**: Customer logs in → clicks "Give Feedback" → fills
  form → sees confirmation → receives status-change notifications.
- **Triage**: Admin opens dashboard → filters "New" → reviews item →
  assigns category/status → optionally comments.
- **Weekly digest**: Every Monday 08:00, all admins receive a summary email
  of new/open/resolved counts by category.

## 8. Constraints & assumptions

- Constraints: 6-week timeline, 2-person team, no compliance requirements.
- Assumptions: modern browsers only; English-only for this release;
  internet connectivity required (no offline mode).

## 9. Risks & mitigations

See `RISK_LOG.md` — carried forward from Feasibility, refreshed each phase.

## 10. Release plan

| Release | Scope | Target |
|---|---|---|
| MVP | All 6 Must-Have items | End of week 4 |
| Phase 1 | Should-Have items (search, export, notifications) | Week 5–6 |
| Future | Could-Have items (sentiment, roadmap board) | Post-launch, re-prioritise via `/run-change-request` |

## Feature counts by MoSCoW bucket

Must: 6 · Should: 3 · Could: 2 · Won't: 2

## Suggested MVP scope

All 6 Must-Have items only, targeting end of week 4, leaving weeks 5–6 for
hardening and the two highest-value Should-Have items.

---

**Hand-off:** this PRD is the primary input for `/run-business-study` and
`dev-lead`'s TRD (`/run-design-build`).
