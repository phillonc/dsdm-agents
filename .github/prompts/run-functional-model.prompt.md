---
mode: agent
description: Build a functional prototype iteratively, gather feedback, and refine requirements.
---

# Task: Functional model iteration

Invoke the `functional-model` agent.

## Inputs
- **Business study path** (from `business-study` run)
- **Project slug**
- **Iteration count** (default 1; require explicit value to run more)
- **Top features** to prototype (defaults to all Must-Haves)

## Steps
1. Invoke `functional-model` agent.
2. Confirm prototype exists under `generated/<slug>/prototypes/`.
3. Confirm `generated/<slug>/docs/FUNCTIONAL_MODEL_REPORT.md` and `NON_FUNCTIONAL_REQUIREMENTS.md` exist.

## Output
- Paths to prototypes
- Functional model report
- Refined requirements
- NFR list
