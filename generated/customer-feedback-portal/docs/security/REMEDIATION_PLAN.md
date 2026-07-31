# Remediation Plan — Customer Feedback Portal

_Produced by the `pen-tester` agent · `/security-review`_

| Priority | Finding | Fix | Owner | Target |
|---|---|---|---|---|
| 1 (before public launch) | No rate limiting on `POST /feedback` | Add `express-rate-limit`, 20 req/min/IP | `backend-developer` | Before Timebox 3 close |
| 2 (before public launch) | `lodash@4.17.19` transitive CVE | `npm audit fix` | `backend-developer` | Next CI run |
| 3 (nice to have) | No admin audit log | Add `audit_log` table + write hook on status change | `backend-developer` | Phase 1 (Should-Have) |
| 4 (informational) | 7-day JWT expiry | Shorten to 24h for admin sessions | `dev-lead` | Design review |

## Block-release status

**Not blocked.** No Critical or High findings. Priorities 1–2 are
recommended before the public (non-staging) launch but do not block a
staging deployment via `/run-implementation`.
