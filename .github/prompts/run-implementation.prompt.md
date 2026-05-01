---
mode: agent
description: Deploy the tested system to production with rollback, smoke tests, training, and handover. Hybrid mode — confirms before destructive prod actions.
---

# Task: Implementation / Deployment

Invoke the `implementation` agent.

## Inputs
- **Project slug** (must already have a tested system under `generated/<slug>/`)
- **Target environment** (`staging` / `production`)
- **Approver** (user must confirm before each prod action)

## Steps
1. Invoke `implementation` agent.
2. Confirm staging deployment succeeds and smoke tests pass.
3. Confirm rollback plan exists **and has been tested** before promoting to prod.
4. **PAUSE** for explicit user approval before deploying to production.
5. Deploy → verify → monitor for soak period.
6. Conduct post-implementation review.

## Acceptance criteria
- Smoke tests pass post-deploy
- Health checks green
- Rollback drilled successfully
- Stakeholders notified at each checkpoint

## Output artefacts
```
generated/<slug>/docs/DEPLOYMENT_PLAN.md
generated/<slug>/docs/ROLLBACK_PLAN.md
generated/<slug>/docs/TRAINING_MATERIALS.md
generated/<slug>/docs/HANDOVER_DOCS.md
generated/<slug>/docs/POST_IMPLEMENTATION_REVIEW.md
generated/<slug>/docs/LESSONS_LEARNED.md
```

## Equivalent CLI invocation
```
python main.py --phase implementation --input "<deployment scope>"
```
