# Technical Requirements Document — Customer Feedback Portal

_Produced by the `dev-lead` agent (via `design-build`) · `/run-design-build` · see `guide.md` §4.4_

## 1. Architecture summary

React (Vite) SPA → Express REST API → PostgreSQL (Prisma). Scheduled
`node-cron` job dispatches the weekly digest through SendGrid. See
`architecture/HIGH_LEVEL_ARCHITECTURE.md` and `architecture/decisions/`.

## 2. API surface (MVP)

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/auth/register` | Create account | none |
| POST | `/auth/login` | Issue JWT | none |
| POST | `/feedback` | Submit feedback | user |
| GET | `/feedback` | List feedback (admin: all, user: own) | user |
| PATCH | `/feedback/:id` | Update status/category | admin |
| GET | `/admin/digest-preview` | Preview the next digest email | admin |

## 3. Component breakdown

- **Frontend**: `src/frontend/{components,pages,hooks}` — 14 files
  (submission form, admin triage table, auth pages, notification bell).
- **Backend**: `src/backend/{routes,services,models}` — 11 files
  (auth, feedback CRUD, digest service, Prisma schema).
- **Tests**: `tests/{unit,integration}` — 9 files.

## 4. Quality gates (must pass before Implementation)

| Check | Threshold | Owner |
|---|---|---|
| Test pass rate | 100% | `automation-tester` |
| Coverage | ≥ 80% | `automation-tester` |
| Lint | 0 errors | `dev-lead` |
| Security scan | 0 Critical / 0 High | `pen-tester` |
| Performance (p95, 50 rps) | < 500ms | `nfr-tester` |
| Accessibility | WCAG AA, 0 blocking | `nfr-tester` |

## 5. Latest run results

Tests: 47/47 passed · Coverage: 84% · Security: 0 Critical / 0 High / 1
Medium / 2 Low · Performance: p95 218ms @ 50 rps (PASS) · Accessibility: 2
minor WCAG AA issues (contrast on secondary buttons, non-blocking).

Full security findings: `security/VULNERABILITY_ASSESSMENT.md`.

## 6. Ready-for-implementation checklist

- [x] All tests pass
- [x] Lint clean
- [x] Coverage ≥ 80%
- [x] No Critical/High security findings
- [ ] Medium finding (rate limiting on `POST /feedback`) — recommended
      before production, does not block staging

---

**Next:** `/run-implementation` (staging first) or `/security-review` for
the full remediation plan.
