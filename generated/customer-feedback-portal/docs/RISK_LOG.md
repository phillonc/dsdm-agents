# Risk Log — Customer Feedback Portal

_Owned by `feasibility` (created) and `business-study` (maintained) · updated by `change-control` on scope changes_

| # | Risk | Severity | Probability | Mitigation | Status | Phase logged |
|---|------|----------|-------------|------------|--------|---------------|
| 1 | 6-week timeline vs. 2-person team | High | High | Cut Could-Have scope first; strict weekly timeboxing | Open | Feasibility |
| 2 | Weekly email digest delivery reliability | Medium | Medium | Managed transactional provider (SendGrid) with delivery webhooks | Open | Feasibility |
| 3 | No auth provider decided yet | Medium | Low | Defaulted to email+password with bcrypt; SSO deferred | Mitigated | Feasibility |
| 4 | Admin triage UX undefined | Low | Medium | Covered in Functional Model prototyping | Mitigated | Feasibility |
| 5 | Digest cron job has no recovery path if the server restarts mid-run | Medium | Low | Add a `last_run` watermark table + startup catch-up check in Design & Build | Open | Business Study |

## Change log cross-reference

Any scope change that introduces or retires a risk gets logged here by the
`change-control` agent (`/run-change-request`) — see `CHANGE_LOG.md` for the
decision trail behind each addition.
