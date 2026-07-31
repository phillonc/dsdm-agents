# customer-feedback-portal — example project

This folder is a **worked example**, not a real generated project. Every
document under `docs/` matches, artefact-for-artefact, the illustrative
slash-command transcripts in [`guide.md`](../../guide.md) (§4 "Example
outputs"). It exists so you can open a real file instead of only reading
prose in the guide — the content is hand-written to be representative of
what each DSDM Agents phase/slash command produces, not the output of an
actual agent run.

Source requirements: [`examples/sample_feedback_portal.md`](../../examples/sample_feedback_portal.md).

## Documents

| File | Produced by | Slash command |
|---|---|---|
| `docs/FEASIBILITY_REPORT.md` | `feasibility` agent | `/run-feasibility` |
| `docs/PRODUCT_REQUIREMENTS.md` | `product-manager` agent | `/run-product-management` |
| `docs/BUSINESS_STUDY.md` | `business-study` agent | `/run-business-study` |
| `docs/architecture/HIGH_LEVEL_ARCHITECTURE.md` | `business-study` agent | `/run-business-study` |
| `docs/RISK_LOG.md` | `business-study` agent (updated by later phases) | `/run-business-study` |
| `docs/TECHNICAL_REQUIREMENTS.md` | `dev-lead` (via `design-build`) | `/run-design-build` |
| `docs/architecture/decisions/001-database-choice.md` | `dev-lead` | `/run-design-build` |
| `docs/security/VULNERABILITY_ASSESSMENT.md` | `pen-tester` | `/security-review` |
| `docs/security/DEPENDENCY_REPORT.md` | `pen-tester` | `/security-review` |
| `docs/security/REMEDIATION_PLAN.md` | `pen-tester` | `/security-review` |
| `docs/CHANGE_LOG.md` | `change-control` agent | `/run-change-request` |

A real run of these phases would also populate `src/`, `tests/`, and
`prototypes/` — omitted here to keep the example focused on the documents
readers actually open while learning the slash commands.
