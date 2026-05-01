---
mode: agent
description: Run the DevOps quality gate — tests, coverage, lint, security scans, and report against the 14 Development Principles.
---

# Task: DevOps quality gate

Invoke the `devops` agent.

## Inputs
- **Project slug** (or repo path)
- **Gate severity** (`pr` / `release`)
  - `pr`: must pass — tests, lint, coverage, SAST
  - `release`: also includes performance, accessibility, dependency audit

## Steps
1. `run_tests` — pytest suite
2. `check_coverage` — must be ≥80% (gate level dependent)
3. `run_linter` — ruff
4. `run_security_scan` — bandit + safety + pip-audit
5. `check_code_quality` — aggregate score
6. (release only) `run_performance_test` — locust scenarios
7. (release only) `check_accessibility` — pa11y
8. (release only) `analyze_dependencies` — graph + vuln report

## Output
- Pass / Fail per check
- Citation of the relevant Development Principle for each
- Block-release findings flagged
- Suggested remediations

## Stop condition
After every gate has run, post a one-screen summary table and stop.
