# PRD: MoSCoW-to-Code Traceability Engine

## 1. Product Summary

MoSCoW-to-Code Traceability Engine links every prioritized requirement to the artifacts that prove delivery: user stories, acceptance criteria, architecture decisions, source files, tests, deployment evidence, monitoring signals, and release notes.

The feature gives users a governance-grade view of whether Must, Should, Could, and Won't-have requirements are planned, implemented, tested, deployed, or blocked.

## 2. Problem Statement

DSDM relies on MoSCoW prioritization and controlled delivery. However, requirements often become disconnected from code, tests, and deployment evidence. This makes it difficult to prove whether Must-have scope is complete or whether quality has been compromised.

Traceability makes delivery transparent and auditable.

## 3. Target Users

- Product owners validating scope
- Delivery managers tracking Must-have completion
- Developers understanding requirement impact
- QA teams proving coverage
- Auditors and consultants needing evidence

## 4. Goals

- Trace requirements from business priority to implementation and verification.
- Show status of Must/Should/Could/Won't requirements.
- Identify untested or undeployed requirements.
- Produce a release readiness report.
- Support requirement impact analysis.

## 5. Non-Goals

- Replacing Jira, GitHub, or test frameworks.
- Guaranteeing semantic correctness of code without tests and review.
- Building a complex enterprise UI in MVP.

## 6. Core User Stories

### Must Have

1. As a user, I can register MoSCoW requirements for a project.
2. As an agent, I can link generated code files to requirements.
3. As an agent, I can link test files and test results to requirements.
4. As a user, I can see which Must-have requirements are not implemented or not tested.
5. As a user, I can generate a release readiness report.

### Should Have

1. As a user, I can see requirement coverage by priority.
2. As a user, I can see which artifacts prove each requirement.
3. As a user, I can detect when code changes affect a Must-have requirement.
4. As a user, I can export traceability matrix as Markdown and JSON.

### Could Have

1. Git commit integration.
2. Pull request checks that block release when Must-have tests are missing.
3. Coverage visualization.
4. Jira requirement sync.

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| MTC-PRD-FR-001 | Store requirements with MoSCoW priority | Must |
| MTC-PRD-FR-002 | Link requirement to user stories and acceptance criteria | Must |
| MTC-PRD-FR-003 | Link requirement to source files | Must |
| MTC-PRD-FR-004 | Link requirement to test files | Must |
| MTC-PRD-FR-005 | Store latest test status for linked tests | Must |
| MTC-PRD-FR-006 | Generate traceability matrix | Must |
| MTC-PRD-FR-007 | Generate release readiness summary | Must |
| MTC-PRD-FR-008 | Detect unimplemented Must-have requirements | Must |
| MTC-PRD-FR-009 | Detect untested Must-have requirements | Must |
| MTC-PRD-FR-010 | Export traceability as Markdown and JSON | Should |

## 8. Acceptance Criteria

- Given a Must-have requirement exists, when no code links exist, then it appears as unimplemented.
- Given a requirement has code but no tests, when readiness is calculated, then it appears as implemented but untested.
- Given all Must-have requirements have passing tests, when readiness is calculated, then Must-have coverage is marked ready.
- Given a traceability matrix is exported, then each requirement includes priority, status, code links, test links, and evidence.

## 9. Status Model

Requirement status should include:

- `proposed`
- `accepted`
- `designed`
- `implemented`
- `tested`
- `deployed`
- `blocked`
- `deferred`

## 10. Metrics

- 100% of Must-have requirements have explicit status.
- 90% of implemented Must-have requirements have linked tests.
- Release readiness report generated in under 5 seconds for normal projects.
- Reduced manual requirement reconciliation effort.

## 11. Risks

- Agents may link files incorrectly without validation.
- Traceability can become noisy if too granular.
- Users may treat linked evidence as proof without reviewing quality.

## 12. Release Plan

### MVP

- Requirement registry.
- Link source files and tests.
- Traceability matrix.
- Release readiness report.
- Markdown/JSON export.

### V2

- Git diff integration.
- PR checks.
- Jira sync.
- Visual dashboard.
- Automated test result ingestion.

## 13. Open Questions

- Should traceability reuse Living Project Memory Graph or remain separate?
- Should links be manually confirmed in hybrid/manual mode?
- Should test evidence be imported from pytest/Jest reports or inferred from file names in MVP?
