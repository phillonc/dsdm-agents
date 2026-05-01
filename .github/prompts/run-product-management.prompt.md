---
mode: agent
description: Generate a comprehensive PRD from a feasibility report or raw business requirements.
---

# Task: Generate Product Requirements Document (PRD)

Invoke the `product-manager` agent to produce a PRD.

## Inputs
- **Feasibility report path** (from a previous `feasibility` run) **or** raw business requirements
- **Project slug**
- **Target users / personas** (optional — agent will derive if missing)
- **KPIs / success metrics** (optional)

## Steps
1. Invoke `product-manager` agent with the inputs.
2. Confirm `generated/<slug>/docs/PRODUCT_REQUIREMENTS.md` exists.
3. Verify the PRD contains all 10 sections:
   1. Executive Summary
   2. Problem Statement
   3. Product Vision
   4. Target Audience & Personas
   5. Business Objectives & Success Metrics
   6. Feature Specifications (with MoSCoW)
   7. User Journeys
   8. Constraints & Assumptions
   9. Risks & Mitigations
   10. Release Plan (MVP → Phase 1 → Future)

## Output
- Path to the PRD
- Feature counts per MoSCoW bucket (Must / Should / Could / Won't)
- Suggested first MVP scope

## Hand-off
The PRD output is the primary input for `dev-lead` (TRD generation).
