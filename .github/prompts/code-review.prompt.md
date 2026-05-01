---
mode: agent
description: Run a code review pass over the current changes — quality, standards, security, performance.
---

# Task: Code review

Invoke the `dev-lead` agent (with `pen-tester` for security findings).

## Inputs
- **Branch / PR / file paths** to review
- **Severity threshold** (default: report Medium and above)

## Steps
1. `dev-lead` reviews:
   - Architecture conformance (against TRD + ADRs)
   - SOLID + clean code
   - Naming, structure, readability
   - Test coverage for changes
   - Documentation gaps
2. `pen-tester` reviews for:
   - OWASP Top 10
   - Hard-coded secrets / credentials
   - Vulnerable dependencies
3. Aggregate findings into a single review report.

## Output
- Inline-style comments per file/line
- Severity-classified findings (Critical / High / Medium / Low / Informational)
- Suggested fixes
- Overall recommendation: **Approve / Request Changes / Block**

## Conventions
- Be specific: cite the file and line.
- Distinguish *must-fix* from *nice-to-have*.
- Reference the relevant principle or standard (DSDM, OWASP, SOLID).
