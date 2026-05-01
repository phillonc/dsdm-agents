---
mode: agent
description: Run only the Feasibility phase to get a Go/No-Go recommendation, top risks, and DSDM-fit assessment.
---

# Task: Feasibility study

Use the `feasibility` agent to assess the project below.

## Inputs
- **Project description**
- **Proposed technology stack** (if any)
- **Constraints**: deadlines, budget, regulatory, scale

## Steps
1. Invoke `feasibility` agent with the inputs above.
2. Verify it called `analyze_requirements`, `assess_technical_feasibility`, and `identify_risks` **in parallel**.
3. Confirm `generated/<slug>/docs/FEASIBILITY_REPORT.md` exists.

## Output
- Path to the feasibility report
- GO / NO-GO recommendation with confidence %
- Top 3–5 risks with mitigations

## Equivalent CLI invocation
```
python main.py --phase feasibility --input "<project description>"
```
