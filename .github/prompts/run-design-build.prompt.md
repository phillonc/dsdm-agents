---
mode: agent
description: Build production-ready code with tests and a TRD. Delegates to specialised agents (dev-lead, frontend, backend, automation-tester, nfr-tester, pen-tester) as needed.
---

# Task: Design & Build

Invoke the `design-build` agent (which orchestrates the specialists).

## Inputs
- **PRD path** (from `product-manager` run)
- **Functional model report path** (from `functional-model` run)
- **Project slug**
- **Tech stack** (from PRD/business-study or specified explicitly)

## Steps
1. Invoke `design-build` agent.
2. It will hand off to:
   - `dev-lead` — TRD + ADRs
   - `frontend-developer` — UI components
   - `backend-developer` — APIs, data
   - `automation-tester` — test suites
   - `nfr-tester` — performance, accessibility (Hybrid — confirm chaos)
   - `pen-tester` — security review (Manual — confirm every scan)
3. Verify quality gates:
   - All tests pass
   - Lint clean
   - Coverage ≥ 80%
   - Security scan clean (no Critical/High)
4. Confirm artefacts:
   - `generated/<slug>/src/...`
   - `generated/<slug>/tests/...`
   - `generated/<slug>/docs/TECHNICAL_REQUIREMENTS.md`
   - `generated/<slug>/docs/architecture/decisions/...`
   - `generated/<slug>/docs/api/openapi.yaml` (if APIs)

## Output
- Files created
- Test pass / fail counts and coverage %
- Security findings (Critical / High / Medium / Low)
- TRD location
- Ready-for-implementation checklist

## Equivalent CLI invocation
```
python main.py --phase design_build --input "<feature description>"
```
