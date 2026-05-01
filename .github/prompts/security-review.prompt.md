---
mode: agent
description: Run an authorised security review over the current changes — SAST, SCA, secret scan, OWASP Top 10 manual review.
---

# Task: Security review

Invoke the `pen-tester` agent (Manual mode — confirm every active scan).

## Inputs
- **Scope** (paths / services / endpoints)
- **Authorisation evidence** (issue / change ticket reference)
- **Environment** (`local` / `staging` only — never production without separate change ticket)

## Steps
1. **Confirm authorisation** is in scope before starting.
2. Run **SAST**: `bandit 1.9.2` over Python sources.
3. Run **SCA**: `safety 3.7.0` and `pip-audit 2.10.0` over dependencies.
4. Run **secret scan** over the diff.
5. Manual OWASP Top 10 review of:
   - Auth + access control
   - Input validation
   - Crypto usage
   - Logging + monitoring gaps
   - Misconfiguration
6. Classify findings by severity.
7. Produce remediation plan.

## Output
```
generated/<slug>/docs/security/VULNERABILITY_ASSESSMENT.md
generated/<slug>/docs/security/DEPENDENCY_REPORT.md
generated/<slug>/docs/security/REMEDIATION_PLAN.md
```

- Counts by severity (Critical / High / Medium / Low / Informational)
- Block-release findings (any Critical or High)
- Recommended fixes prioritised by severity

## Forbidden
- No exploitation / payload generation against any target without written authorisation
- No probing of production
- No publishing of unredacted findings
