# Workflow: Requirement → PRD → TRD → TASKS

**Status:** normative · **Spec ID:** `WF-PRTT-001` · **Version:** 1.1.0

This document is the **shared contract** for the requirement-intake workflow. An
identical copy lives in each of the three agent repositories:

**Version 1.1.0** added stage 3, the Definition of Done, and the per-lane Done
check that closes each agent's task list. It also raised the accessibility
baseline from WCAG 2.1 AA to **2.2 AAA**, settling a disagreement between the
workflow's own baseline, the requirement documents in `lhs-agents`, and the
tasks `role-agents.ts` already generates.

| Repository | Implementation | Default output root |
|------------|----------------|---------------------|
| `DSDM-Agency` | `agents_framework/workflow/` (Python, reference implementation) | `workflow-output/` |
| `dsdm-agents` | `src/workflow/` (Python) | `generated/<project>/docs/` |
| `lhs-agents` | `agents/dsdm-dev/src/requirement-workflow/` (TypeScript) | `workflow-output/` |

The three implementations differ in language and in which agents they own. They
do **not** differ in the pipeline, the gates, the ID schemes, or the section
headings of the documents they emit. A change to any of those is a change to
this document, applied to all three repositories together.

---

## 1. The pipeline

When a requirement is inputted, the agent framework runs five stages in order.
Each stage consumes the previous stage's product and every stage is a **hard
gate** — stage *N+1* refuses to run if stage *N* did not produce its product.

```
requirement text/file
        │
        ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
│ 0. INTAKE  │─▶│  1. PRD    │─▶│  2. TRD    │─▶│  3. DONE   │─▶│  4. TASKS  │
│ normalise  │  │ product    │  │ technical  │  │ what good  │  │ per-agent  │
│ requirement│  │ lane       │  │architecture│  │ looks like │  │ breakdown  │
└────────────┘  └────────────┘  └────────────┘  └────────────┘  └────────────┘
                      │               │               │               │
                   PRD.md          TRD.md    DEFINITION-OF-DONE.md  TASKS.md
```

| # | Stage | Owning lane | Gate to enter | Product |
|---|-------|-------------|---------------|---------|
| 0 | `INTAKE` | `product` | requirement has a non-empty title | normalised `Requirement` |
| 1 | `PRD` | `product` | intake produced ≥ 1 requirement item | `PRD.md` |
| 2 | `TRD` | `architecture` | PRD contains ≥ 1 functional requirement | `TRD.md` |
| 3 | `DONE` | `qa` | PRD has ≥ 1 requirement **and** TRD has ≥ 1 component | `DEFINITION-OF-DONE.md` |
| 4 | `TASKS` | `delivery` | TRD has ≥ 1 component **and** the DoD has ≥ 1 criterion | `TASKS.md` |

`DONE` comes **before** `TASKS`, not after it. Each lane's task list closes with
a check against the criteria that lane owns, so the bar has to exist before the
work is assigned — you cannot measure against a standard written afterwards.

A gate failure is an **error**, never a silent skip. The implementation raises
(Python) or throws (TypeScript) with a message naming the missing product.

---

## 2. Stage 0 — Intake

The workflow accepts a requirement as free text, a markdown file, or a
structured object. All three are normalised to the same shape.

```
Requirement
  id            REQ-001 style identifier (generated if absent)
  title         short name — REQUIRED, non-empty
  description   free text; may contain markdown bullets
  requester     who asked for it (optional)
  priority      MoSCoW: M | S | C | W   (default S)
  effort        numeric estimate (default 1)
  goals         list of business outcomes
  constraints   list of constraints
  acceptance    list of acceptance criteria
```

**Item extraction.** Every markdown bullet (`-`, `*`, or `N.`) in `description`
becomes one requirement item. If `description` contains no bullets, the whole
description is a single item. Items are numbered `REQ-001`, `REQ-002`, … in
source order. This rule is what makes the pipeline deterministic: the same
requirement text always yields the same documents.

**Slug.** The requirement title is slugified (lowercase, non-alphanumerics to
`-`, collapsed, trimmed) and names the output directory.

---

## 3. Stage 1 — PRD

Emits `PRD.md` with these sections, in this order. Headings are normative.

```markdown
# Product Requirements Document — <title>

| Field | Value |            ← metadata block: Requirement ID, Spec, Version,
                               Priority, Requester, Stage

## 1. Overview
## 2. Problem Statement
## 3. Goals and Success Metrics
## 4. Users and Stakeholders
## 5. Functional Requirements      ← table: ID | Requirement | Priority | Effort | Source
## 6. Non-Functional Requirements  ← table: ID | Category | Requirement
## 7. Out of Scope
## 8. Assumptions and Constraints
## 9. Acceptance Criteria
## 10. Traceability               ← table: Requirement item → PRD-FR ID
```

**Functional requirement IDs** are `PRD-FR-001`, `PRD-FR-002`, … — one per
intake item, in order, so `REQ-00N` always maps to `PRD-FR-00N`.

**Non-functional requirements** are `PRD-NFR-001`… and are drawn from a fixed
baseline set (performance, security, accessibility, observability,
maintainability) plus any constraint the requirement supplies. The baseline is
always present so no PRD ships without NFRs. The accessibility baseline is
**WCAG 2.2 AAA**, matching §5.

---

## 4. Stage 2 — TRD

Emits `TRD.md`. Every functional requirement in the PRD is routed to one or
more delivery lanes, and each lane that receives work becomes one **technical
component**. A component records every `PRD-FR` it satisfies, so the mapping
runs both ways and can be checked mechanically.

```markdown
# Technical Requirements Document — <title>

| Field | Value |            ← metadata, including the PRD it derives from

## 1. Overview
## 2. Architecture Summary       ← table: Component | Name | Lane | Satisfies
## 3. Components                 ← one ### block per component
## 4. Data and Interfaces
## 5. Non-Functional and Technical Constraints
## 6. Testing Strategy
## 7. Risks
## 8. Traceability               ← table: PRD-FR ID → TRD-C IDs
```

**Component IDs** are `TRD-C-001`, `TRD-C-002`, … assigned in lane order (see
§7), not in requirement order, so the component list reads front-to-back
through the stack. There is at most one component per lane.

Only the six **implementation lanes** — `data`, `backend`, `frontend`,
`security`, `qa`, `devops` — become components. `product`, `architecture` and
`delivery` own documents and governance instead, and reach `TASKS.md` through
the cross-cutting tasks in §6.

### 4.1 Lane routing

Each functional requirement is routed to delivery lanes by a case-insensitive
keyword match against its text. A keyword matches at a **word boundary** and
matches forward, so `auth` covers *authentication* and *authorised* while `ui`
does **not** match *build* or *requirement* — an unanchored match would route
almost everything to the frontend.

| Lane | Routed when the requirement mentions |
|------|--------------------------------------|
| `frontend` | ui, screen, page, view, form, button, layout, css, react, mobile, browser, dashboard, navigation, accessib |
| `backend` | api, endpoint, service, server, logic, workflow, integration, webhook, queue, job, process, account, register, registration, notification, email, payment, calculate, validate, rule |
| `data` | data, database, schema, model, migration, store, persist, record, report, analytics, index, search |
| `security` | auth, login, log in, sign in, sign-in, permission, role, encrypt, gdpr, consent, audit, token, secret, credential, pii, password |
| `devops` | deploy, ci, cd, pipeline, monitor, alert, infrastructure, scale, availability, backup, release |

A requirement matching no keyword is routed to `backend` — the default lane.
A requirement may match several lanes and then appears in several components.

`qa` is **not** keyword-routed: the `qa` component always satisfies *every*
functional requirement, so nothing reaches `TASKS.md` without a verification
owner.

---

## 5. Stage 3 — Definition of Done

Emits `DEFINITION-OF-DONE.md`: what *good* looks like for this requirement,
written through three lenses.

| Perspective | The question it answers |
|-------------|-------------------------|
| `user` | Can someone actually do the thing, without help and without barriers? |
| `business` | Did we get the outcome we asked for, and can we prove it? |
| `technical` | Will this still work on Monday, and can we change it safely? |

```markdown
# Definition of Done — <title>

| Field | Value |            ← metadata, deriving from the PRD and the TRD

## 1. What Good Looks Like
## 2. Universal Criteria         ← 2.1 User · 2.2 Business · 2.3 Technical
## 3. Criteria by Feature        ← one ### block per PRD-FR
## 4. Sign-off                   ← table: Perspective | Signed off by | Covering
## 5. Ownership                  ← table: Lane | Criteria it answers for
```

**Criterion IDs** are `DOD-U-001`… for universal criteria and
`DOD-F00N-001`… for criteria belonging to `PRD-FR-00N`.

Every criterion carries **evidence**: how you would know it has been met. A
criterion with no evidence is an opinion, and cannot be checked.

### 5.1 Universal criteria

These hold for every requirement. The four marked **(mandatory)** were set by
explicit decision and may not be removed without changing this spec.

| Perspective | Criterion | Owning lane |
|-------------|-----------|-------------|
| `user` | Accessibility: **WCAG 2.2 AAA** — 7:1 contrast, enhanced focus indicators, full keyboard navigation, 44×44px minimum targets, screen-reader verified | `frontend` |
| `user` | The journey completes unaided: happy path, error, empty and loading states all handled | `frontend` |
| `user` | Existing users are not regressed | `qa` |
| `business` | **(mandatory)** A named **Business Ambassador** has seen it work and accepted it | `product` |
| `business` | **(mandatory)** Every PRD success metric is **instrumented** and readable in production | `product` |
| `business` | Must Have scope is complete, or the shortfall re-negotiated and recorded | `delivery` |
| `technical` | **(mandatory)** Unit test coverage on changed code **≥ 80%**, every acceptance criterion tested | `qa` |
| `technical` | CI green on the merge commit: build, lint, type-check, full suite | `devops` |
| `technical` | **(mandatory)** A **rollback plan** is documented and rehearsed | `devops` |
| `technical` | Reviewed and merged: ≥ 1 reviewer, no unresolved threads | `architecture` |
| `technical` | Every failure path emits a structured, traceable log record | `backend` |

### 5.2 Ownership, and the difference from applicability

Two separate questions, and conflating them produces ticks that mean nothing:

**Who answers for it.** Every criterion names exactly **one** owning lane. A
criterion owned by everybody is owned by nobody. If that lane has no work in
this requirement, the criterion falls to the lane that signs off its
perspective (`user` → `product`, `business` → `delivery`, `technical` →
`architecture`) — it changes hands rather than disappearing.

**Whether it applies at all.** A few criteria depend on a lane *existing*: a
requirement with no interface cannot meaningfully meet an accessibility bar.
Those are marked **not applicable**, with the reason, and are attached to no
Done check. They stay visible in the document so a reader can see they were
considered — but nobody is asked to tick them.

Only the two `frontend` user criteria are conditional in this way. Everything
else always applies: CI still has to be green whether or not the requirement
mentions deployment.

### 5.3 Per-feature criteria

Every functional requirement gets its own block, and always at least one
criterion from **each of the three perspectives** — so nothing can be called
done on technical grounds alone:

| Perspective | Criterion | Owning lane |
|-------------|-----------|-------------|
| `user` | `PRD-FR-00N` is demonstrable end to end — someone can watch it happen | `qa` |
| `technical` | Automated tests cover it at the right level and fail on regression | `qa` |
| `business` | Must Have → no known open defects; otherwise → defects logged, triaged and accepted | `delivery` |

It then earns further criteria from the **same lane routing that built the
TRD** (§4.1), so a data feature is held to data standards and a user-facing one
to user-facing standards, with nobody hand-maintaining the mapping:

| Routed lane | Criterion it earns | Perspective |
|-------------|--------------------|-------------|
| `frontend` | Responsive across supported breakpoints, and design reviewed | `user` |
| `backend` | Documented contract, validated inputs, defined error responses | `technical` |
| `data` | Forward-only migration with a tested rollback; no personal data in logs | `technical` |
| `security` | Authorised as well as authenticated, every attempt audited | `technical` |
| `security` | Where personal data is handled, lawful basis and consent path recorded | `business` |
| `devops` | Deployed via the pipeline, monitored, alert fires on the real failure mode | `technical` |

---

## 6. Stage 4 — TASKS

Emits `TASKS.md`. This is the file that gives **each agent its own set of
tasks**: one section per lane that has work, and inside it a checklist only
that lane's agent is expected to complete.

```markdown
# Task Breakdown — <title>

| Field | Value |            ← metadata, including the TRD it derives from

## 1. Assignment Summary        ← table: Agent | Lane | Tasks | Effort
## 2. Execution Order           ← the lane order work should proceed in
## 3. Tasks by Agent
### 3.N <Agent role> — `<lane>`
     - [ ] **TASK-<LANE>-00N** — <title>
             - Traces to: PRD-FR-00N, TRD-C-00N, DOD-U-00N
             - Priority / Effort / Depends on
             - Acceptance: …
## 4. Traceability              ← table: TRD-C ID → TASK IDs
```

**Task IDs** are `TASK-<LANE-CODE>-001`, numbered per lane so each agent's list
is self-contained.

| Lane | Code | Lane | Code |
|------|------|------|------|
| `product` | `PRD` | `qa` | `QA` |
| `architecture` | `ARC` | `security` | `SEC` |
| `frontend` | `FE` | `devops` | `OPS` |
| `backend` | `BE` | `delivery` | `DEL` |
| `data` | `DATA` | | |

**Task derivation.** Each component yields **one implementation task per
functional requirement it satisfies** — so an agent's list names the individual
requirements it is on the hook for, not one lump of work per lane. On top of
that, every run emits a fixed set of cross-cutting tasks, so the same
governance happens on every requirement whatever it contains:

| Lane | Always-present task |
|------|---------------------|
| `product` | Confirm the PRD with stakeholders and freeze scope |
| `architecture` | Sign off the TRD and publish the component boundaries |
| `security` | Security review of the TRD |
| `qa` | Author the test plan covering every functional requirement |
| `devops` | Confirm pipeline and deployment readiness |
| `delivery` | Produce the timebox plan and confirm the MoSCoW balance |

A lane's cross-cutting task is numbered first, so it is always `TASK-<CODE>-001`
and its implementation tasks follow.

**The Done check.** Every lane's list **closes** with one final task: *verify
this lane's work against the Definition of Done*. It traces to every applicable
criterion that lane owns (§5.2), and its acceptance names them. This is what
stops the DoD being a document nobody opens — each agent is measured on the
criteria it answers for, and every applicable criterion appears in exactly one
agent's Done check.

**Dependencies.** Every task except the `architecture` sign-off depends on that
sign-off — nothing starts before the component boundaries are agreed. A `qa`
task additionally depends on the implementation tasks covering the same
functional requirement, because you cannot verify what has not been built. A
lane's Done check depends on every other task in that lane, for the same
reason. The execution order in §2 of the file is the lane order of §7.

---

## 7. Lane order

Lanes are always presented — in the TRD component list, in the TASKS execution
order, and in the assignment summary — in this order:

```
product → architecture → data → backend → frontend → security → qa → devops → delivery
```

---

## 8. Agent mapping

The workflow is defined over **lanes**, not over any repository's agent names.
Each repository maps its own agents onto the lanes, so the pipeline is the same
everywhere while the roster stays repo-specific.

| Lane | `DSDM-Agency` | `dsdm-agents` | `lhs-agents` (`agents/dsdm-dev`) |
|------|---------------|---------------|----------------------------------|
| `product` | Business Analyst | Product Manager Agent | Decomposition Agent |
| `architecture` | Technical Coordinator | Dev Lead Agent | Primary DSDM Agent |
| `data` | Technical Coordinator | Backend Developer Agent | Backend Developer Agent |
| `backend` | Solution Developer | Backend Developer Agent | Backend Developer Agent |
| `frontend` | Solution Developer | Frontend Developer Agent | Frontend Developer Agent |
| `security` | Technical Coordinator | Pen Tester Agent | Security Tester Agent |
| `qa` | Solution Tester | Automation Tester Agent | QA Tester Agent |
| `devops` | Technical Coordinator | DevOps Agent | Primary DSDM Agent |
| `delivery` | Project Manager | Implementation Agent | Primary DSDM Agent |

A repository that has no distinct agent for a lane maps it to the nearest role
it does have — `lhs-agents` has no DevOps or delivery-manager agent in this
package, so those lanes fall to the Primary DSDM Agent that already
orchestrates the workflow. A lane is never dropped: the tasks still appear,
assigned to whoever answers for them there.

The consequence is worth stating plainly, because it is the point of the
shared spec: run the same requirement through all three repositories and the
three `TASKS.md` files are identical apart from the agent names — same task
IDs, same traceability, same ordering.

---

## 9. Output contract

```
<output_root>/<requirement-slug>/
    PRD.md
    TRD.md
    DEFINITION-OF-DONE.md
    TASKS.md
```

Writing is atomic per run: either all four files are written or the run fails
at a gate before writing anything. Re-running with the same requirement
overwrites the directory with identical content — the renderers are pure
functions of the requirement, so the workflow is reproducible and diffable.

Documents carry no timestamps or random identifiers in their body for exactly
that reason. Run metadata (when, by whom) belongs in the caller's logs, not in
the deliverable.

---

## 10. Invariants

These hold in all three implementations and are covered by tests in each:

1. **Every stage is gated.** Running TRD without a PRD, or TASKS without a TRD,
   raises rather than emitting an empty document.
2. **Every functional requirement traces forward.** Each `PRD-FR` appears in at
   least one `TRD-C`, and each `TRD-C` appears in at least one `TASK`. The
   traceability tables in the documents are generated from the same data, never
   hand-maintained.
3. **Every requirement gets a QA owner.** The `qa` lane always has tasks.
4. **Every feature is held to all three perspectives.** Each `PRD-FR` carries at
   least one `user`, one `business` and one `technical` criterion, so nothing
   can be called done on technical grounds alone.
5. **Every applicable criterion reaches exactly one Done check.** No criterion
   is owned by two lanes, and none is owned by none. A criterion marked not
   applicable reaches no Done check at all — it is never reassigned to whoever
   happens to be free, because a tick that cannot mean anything teaches people
   to tick boxes.
6. **Every criterion carries evidence.** What would show it has been met, not
   just what must be true.
7. **Renderers are pure.** The same requirement yields byte-identical
   documents on every run, in every repository.
8. **Lane order is fixed** (§7) and is the single source of ordering for all
   four documents.
