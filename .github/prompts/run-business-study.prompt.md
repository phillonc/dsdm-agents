---
mode: agent
description: Run only the Business Study phase — stakeholders, MoSCoW requirements, high-level architecture, timeboxes.
---

# Task: Business study

Invoke the `business-study` agent.

## Inputs
- **PRD path** (from `product-manager` run) or feasibility report
- **Project slug**
- **Stakeholders** (optional — agent will identify if missing)

## Steps
1. Invoke `business-study` agent.
2. Confirm these files exist:
   - `generated/<slug>/docs/BUSINESS_STUDY.md`
   - `generated/<slug>/docs/architecture/HIGH_LEVEL_ARCHITECTURE.md`
   - `generated/<slug>/docs/RISK_LOG.md`
3. Verify MoSCoW prioritisation is applied to every requirement.

## Output
- Counts of Must / Should / Could / Won't items
- High-level architecture summary
- Initial timebox plan
- Risk log entry count

## Equivalent CLI invocation
```
python main.py --phase business_study --input "<requirements>"
```
