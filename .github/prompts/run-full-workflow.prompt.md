---
mode: agent
description: Run the entire DSDM workflow end-to-end (Feasibility → Product Mgmt → Business Study → Functional Model → Design & Build → Implementation) for a new project.
---

# Task: Full DSDM workflow

Run the full DSDM lifecycle for the project described below. Use the agents in `.github/agents/` and orchestrate hand-offs between them.

## Inputs you need from the user
- **Project description**: high-level idea + business context
- **Project slug** (lowercase-hyphenated): the folder name under `generated/`
- **Constraints**: deadlines, tech stack, compliance, scale targets
- (optional) **Jira project key** if work items should be created

## Sequence

1. **Feasibility** — invoke `feasibility` agent. If recommendation is **NO-GO**, stop and report. If **GO**, continue.
2. **Product Management** — invoke `product-manager` agent. Produces the PRD.
3. **Business Study** — invoke `business-study` agent. MoSCoW + architecture + timeboxes.
4. **Functional Model** — invoke `functional-model` agent. Build prototype + capture feedback.
5. **Design & Build** — invoke `design-build` agent (which may delegate to `dev-lead`, `frontend-developer`, `backend-developer`, `automation-tester`, `nfr-tester`, `pen-tester`).
6. **Implementation** — invoke `implementation` agent. Deploy + handover (Hybrid mode — confirm before prod actions).
7. **DevOps** — invoke `devops` agent throughout to ensure quality gates, CI/CD, security, monitoring.

## Acceptance criteria
- All phase reports present under `generated/<slug>/docs/`
- Tests pass with ≥80% coverage
- Security scan clean (no Critical/High)
- TRD and PRD exist and are linked
- Deployment plan + rollback plan exist
- Final summary lists artefacts and outstanding risks

## Equivalent CLI invocation
```
python main.py --workflow --input "<project description>"
```

## Stop condition
After step 7 completes, post a summary listing every doc, the test/coverage/security results, and any decisions deferred to the user.
