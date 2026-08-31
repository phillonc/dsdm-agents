# Findings — Requirement → PRD → TRD → TASKS rollout

**Change:** `WF-PRTT-001` implemented across three repositories
**Branch:** `claude/repo-workflow-prd-trd-tasks-wb47uu`
**Date:** 2026-08-31

This document collates every problem found while building the shared workflow,
and what was done about each. An identical copy lives in `DSDM-Agency`,
`dsdm-agents` and `lhs-agents`, alongside
[`WORKFLOW-PRD-TRD-TASKS.md`](WORKFLOW-PRD-TRD-TASKS.md) — the same
"change it in one place, apply it to all three" discipline.

Findings are numbered `F-nn` (resolved) and `O-nn` (open).

---

## Summary

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| [F-01](#f-01) | Lane routing matched keywords mid-word | High | Fixed |
| [F-02](#f-02) | Per-agent task counts silently dropped lanes | High | Fixed |
| [F-03](#f-03) | Crew stage 0 was assigned to an agent without the tool | Medium | Fixed |
| [F-04](#f-04) | Tool parameter names collided with the registry's alias table | Medium | Avoided |
| [F-05](#f-05) | The spec drifted from the implementation while both were being written | Medium | Fixed |
| [F-06](#f-06) | Duplicate role IDs in the assignment output | Low | Fixed |
| [F-07](#f-07) | `npm install` left unrelated lockfile churn | Low | Reverted |
| [F-08](#f-08) | 53 `lhs-agents` test suites and 2 type errors fail in this environment | Low | Pre-existing, not ours |
| [F-09](#f-09) | `lhs-agents` has no DevOps or delivery agent for two lanes | Low | Mapped, not invented |
| [F-10](#f-10) | `dsdm-agents` already had PRD and TRD; TASKS was the actual gap | — | Informational |
| [O-01](#o-01) | Nothing keeps the three spec copies in step | **High** | **Open** |
| [O-02](#o-02) | The `pi` agent runtime does not run the PRD/TRD/TASKS phase | Medium | Open (pre-existing) |
| [O-03](#o-03) | `lhs-agents` workflow is not wired into `workflow-orchestrator.ts` | Medium | Open (deliberate) |
| [O-04](#o-04) | Effort estimates default to 1 unless supplied | Low | Open (by design) |

---

## Resolved

<a id="f-01"></a>

### F-01 — Lane routing matched keywords mid-word
**Severity:** High · **Where:** `routing.py` / `routing.ts`, all three repos

**What was found.** Lane routing began as a plain substring match. The frontend
lane's keyword list contains `ui`, which is a substring of **build**,
**require**, **requirement**, **quick** and **guide**. The DevOps list contains
`ci` and `cd`, which are substrings of many ordinary words. The first
end-to-end smoke test produced a component split that did not match the
requirement text, which is what exposed it.

**Why it mattered.** Nearly every requirement would have been routed to the
frontend lane regardless of content. The TRD's component list, the per-agent
task assignment, and the traceability tables all derive from routing — so a bad
route is not a cosmetic problem, it puts the work on the wrong agent's
checklist and silently drops the right one.

**Resolution.** Keywords are now matched with a word-boundary-anchored,
forward-matching pattern (`\b<keyword>`, case-insensitive). The anchor stops
mid-word matches; forward matching is kept deliberately, so `auth` still covers
*authentication* and *authorised*, and `accessib` covers *accessibility*.
Spec §4.1 states the rule, and a few keyword lists were widened afterwards
(`log in`, `sign in`, `account`, `register`, `email`, `payment`) now that
looser matching no longer caused collateral damage.

**Pinned by.** `test_keywords_match_at_a_word_boundary_not_mid_word`
(DSDM-Agency, dsdm-agents) and `matches keywords at a word boundary, not
mid-word` (lhs-agents) — each asserts both directions: *"Build the stated
requirement"* is not frontend, *"The UI shows progress"* is.

---

<a id="f-02"></a>

### F-02 — Per-agent task counts silently dropped lanes
**Severity:** High · **Where:** `pipeline.summary()`, then two more callers

**What was found.** The per-agent summary was built by keying a dictionary on
the agent's name while iterating lanes. Several roles own more than one lane —
the Technical Coordinator owns architecture, data, security and devops; the
Backend Developer Agent owns data and backend; the Primary DSDM Agent owns
architecture, devops and delivery. Each later lane overwrote the earlier one,
so a multi-lane agent reported only its **last** lane's tasks.

It then recurred twice more: once in `dsdm-agents`'s tool handler and once in
the orchestrator's breakdown helper, both written from the same shape.

**Why it mattered.** The summary is what a reader uses to see who is loaded and
who is idle. A Technical Coordinator with 6 tasks reporting 1 is worse than no
summary at all — the documents themselves were correct, so nothing else
contradicted the wrong number.

**Resolution.** The merge moved onto the model as `TaskPlan.assignments()`, so
every caller inherits it rather than re-deriving it. `summary()` now reads from
that method instead of repeating the loop, and the two `dsdm-agents` callers
were rewritten on top of it. The method's docstring states why it accumulates.
All three ports carry the same method.

**Pinned by.** `test_summary_counts_every_lane_an_agent_owns` (DSDM-Agency),
`test_assignments_merge_the_lanes_one_agent_owns` (dsdm-agents), and both
`merges the lanes one agent owns` and `counts every lane an agent owns in the
summary` (lhs-agents).

---

<a id="f-03"></a>

### F-03 — Crew stage 0 was assigned to an agent without the tool
**Severity:** Medium · **Where:** `tasks/workflow_tasks.py`, DSDM-Agency

**What was found.** The spec originally placed stage 0 (intake) in the
`delivery` lane, so the crew factory handed the intake task to the Project
Manager. The `requirement_intake` tool sits on the Business Analyst, who owns
requirements. The first crew run failed at task 1 and cascaded through all four
downstream tasks, each reporting the missing product from the one before.

**Why it mattered.** The cascade is the gates working as designed, and the
error messages named the right missing product each time — but the root cause
was a lane assignment that did not match DSDM. Normalising a requirement is
requirements work, not delivery management.

**Resolution.** Intake moved to the Business Analyst, and spec §1 changed
stage 0's owning lane from `delivery` to `product`. Stage 3 (TASKS) remains
`delivery`, which is correct — assigning and sequencing work is the Project
Manager's job.

**Pinned by.** `test_crew_runs_the_workflow_end_to_end` and
`test_crew_stops_at_the_gate_when_no_requirement_is_inputted`.

---

<a id="f-04"></a>

### F-04 — Tool parameter names collided with the registry's alias table
**Severity:** Medium · **Where:** `src/tools/workflow_tools.py`, dsdm-agents

**What was found.** `ToolRegistry.Tool.execute` applies an alias table before
dispatch — `project` → `project_name`, `name` → `project_name`, `text`/`body`/
`data` → `content`, `path`/`file`/`filename` → `file_path` — and then **filters
out any argument not in the tool's schema**. A tool exposing a parameter called
`project` would have had it renamed to `project_name`, found no such schema
entry, and dropped it silently. The caller would see the tool run and quietly
ignore the argument.

**Why it mattered.** This is a silent-wrong-answer failure mode, not a crash:
`run_requirement_workflow(project="Merchant Portal")` would have written to the
default location with no error. Found by reading `tool_registry.py` before
naming the parameters, rather than by hitting it.

**Resolution.** The workflow tools use `project_name`, `output_root`,
`requirement` and `include_markdown` — none of which are aliased. The
constraint is recorded in the module docstring so the next tool added there
does not rediscover it.

**Pinned by.** `test_run_workflow_tool_writes_the_documents` exercises
`output_root` through the registry's `execute` path, so the argument is proven
to survive aliasing and filtering.

---

<a id="f-05"></a>

### F-05 — The spec drifted from the implementation while both were being written
**Severity:** Medium · **Where:** `docs/WORKFLOW-PRD-TRD-TASKS.md`

**What was found.** The specification was drafted before the reference
implementation settled, and several statements did not survive contact with the
code:

- the PRD functional-requirement table gained an `Effort` column;
- the TRD architecture-summary table gained a `Name` column;
- "every functional requirement gets a `qa` component" became "the `qa`
  component always satisfies *every* functional requirement" — one component
  per lane, not one per requirement;
- "each component yields one implementation task for its lane" became "one
  implementation task **per functional requirement it satisfies**", which is
  what makes an agent's checklist name individual requirements rather than one
  lump of work per lane;
- the cross-cutting task table was missing the `product` and `architecture`
  rows the implementation emits;
- stage 0's owning lane changed (see [F-03](#f-03));
- keyword matching became word-boundary anchored (see [F-01](#f-01)).

**Why it mattered.** The spec is the contract three implementations are meant
to satisfy. A spec that disagrees with the reference implementation is worse
than none, because the two ports would have been written against the wrong
description.

**Resolution.** Every point above was reconciled against actual behaviour
before the ports were written, and the corrected document was copied
byte-identically into all three repositories. Parity was verified by checksum:

```
f918a8fe84567239d7118f86dca1d568  DSDM-Agency/docs/WORKFLOW-PRD-TRD-TASKS.md
f918a8fe84567239d7118f86dca1d568  dsdm-agents/docs/WORKFLOW-PRD-TRD-TASKS.md
f918a8fe84567239d7118f86dca1d568  lhs-agents/docs/WORKFLOW-PRD-TRD-TASKS.md
```

Keeping them in step from here is [O-01](#o-01), which is **not** solved.

---

<a id="f-06"></a>

### F-06 — Duplicate role IDs in the assignment output
**Severity:** Low · **Where:** `workflow_tools.py` and the orchestrator helper

**What was found.** After [F-02](#f-02) was fixed, an agent owning two lanes
that map to the *same* role listed that role twice — the Backend Developer
Agent owns data and backend, both of which map to `backend-developer`, so
`role_ids` came back as `["backend-developer", "backend-developer"]`.

**Resolution.** `dict.fromkeys(...)` dedupes while preserving order, in both
callers.

**Pinned by.** `test_task_breakdown_tool_reports_every_agents_work` asserts the
Automation Tester's `role_ids` is exactly `["automation-tester"]`.

---

<a id="f-07"></a>

### F-07 — `npm install` left unrelated lockfile churn
**Severity:** Low · **Where:** `lhs-agents/package-lock.json`

**What was found.** Installing dependencies so the TypeScript port could be
type-checked and tested modified `package-lock.json`: an `ollama` entry was
added under `agents/pi-dev-agents` and an `@types/node-cron` entry removed
elsewhere. Neither is related to this change.

**Resolution.** Reverted with `git checkout -- package-lock.json`. The workflow
adds no dependencies to any of the three repositories — it is standard library
in Python and `fs`/`path` in TypeScript.

---

<a id="f-08"></a>

### F-08 — 53 `lhs-agents` test suites and 2 type errors fail in this environment
**Severity:** Low · **Where:** `lhs-agents`, pre-existing

**What was found.** `npx jest` reports 53 suites failing to *run*, and
`npm run type-check:ci` reports 2 new-vs-baseline errors in
`agents/shared/enterprise/config.ts`. Every failure is a missing third-party
module — `ask-sdk-core` (12), `@jest/globals` (4), `zod`, `ws`, `supertest`,
`node-cron`, `fs-extra`, `@anthropic-ai/sdk` — in packages this change does not
touch.

**Why it mattered.** A red suite next to a new change invites the assumption
that the change caused it.

**Resolution.** Confirmed pre-existing by stashing the change and re-running
both commands: **identical** results before and after (53 failed / 75 passed,
and the same two `zod` errors). The change takes the passing test count from
1105 to 1138 and adds one passing suite. Nothing was fixed here — these are
environment gaps, not defects, and are out of scope for this change.

---

<a id="f-09"></a>

### F-09 — `lhs-agents` has no DevOps or delivery agent for two lanes
**Severity:** Low · **Where:** `agents/dsdm-dev`, model mapping

**What was found.** The workflow defines nine lanes. `agents/dsdm-dev` has
six roles in its `Role` union (`FRONTEND_DEVELOPER`, `BACKEND_DEVELOPER`,
`UX_DESIGNER`, `QA_TESTER`, `PEN_TESTER`, `SECURITY_TESTER`) plus the
Decomposition and Primary DSDM agents. There is no DevOps agent and no
delivery manager.

**Why it mattered.** Two tempting wrong answers: drop the lanes (the DevOps and
delivery tasks then never appear, and nobody notices they are missing), or
invent agent names with no code behind them (the checklist names an owner who
does not exist).

**Resolution.** Spec §7's rule — *map to the nearest role you do have, never
drop the lane* — was applied: `devops` and `delivery` fall to the Primary DSDM
Agent, which already orchestrates the workflow, so pipeline readiness and
timebox planning land with the orchestrator. Tasks whose lane maps to a real
`Role` carry it and can become work items; tasks whose lane does not carry
none, rather than a made-up one.

**Pinned by.** `tags tasks with the repository Role their lane maps to`, which
asserts the architecture task's `role` is `undefined`.

---

<a id="f-10"></a>

### F-10 — `dsdm-agents` already had PRD and TRD; TASKS was the actual gap
**Severity:** Informational

**What was found.** `dsdm-agents` already ran a `PRD_TRD` phase in which the
Product Manager authors a PRD and the Dev Lead a TRD, both LLM-driven via
`generate_product_requirements_document` and
`generate_technical_requirements_document`. There was no task-breakdown step at
all, and no guarantee the two documents existed or agreed with each other — the
tools structure an agent's thinking, but the file only lands if the model
remembers to call `file_write`.

**Resolution.** The new step was added *alongside* the existing agents rather
than replacing them, and writes to a different path
(`generated/<project>/docs/<slug>/`) than the narrative documents
(`generated/<project>/docs/PRODUCT_REQUIREMENTS.md`), so nothing is clobbered.
Because it is deterministic and takes no LLM call, the three deliverables now
exist and agree with each other whatever the model produced. The `PRD_TRD` enum
value was **not** renamed — it is referenced from `main.py` and saved configs —
but its comment now records that the phase emits three documents.

---

## Open items

<a id="o-01"></a>

### O-01 — Nothing keeps the three spec copies in step
**Severity:** High · **Status:** Open

`docs/WORKFLOW-PRD-TRD-TASKS.md` is byte-identical in three repositories today,
verified by checksum. **No automated check enforces that.** Someone editing
§4.1's keyword table in one repository will not be told the other two have
drifted, and the ports will silently disagree — the exact failure mode
`lhs-agents/CLAUDE.md` already documents for the UCAF / SSSF mirror ("nothing
keeping the two in step").

The implementations have the same exposure: the keyword lists, lane order, lane
codes, baseline NFRs and cross-cutting task titles are duplicated in three
languages with only the spec and these tests holding them together.

**Suggested fix,** in rough order of cost: a CI job in each repo that fetches
the other two copies and fails on a checksum mismatch; or a golden-file test
per repo that runs one fixed requirement and compares the rendered documents
against a committed expected output, so a routing or ordering change has to be
made deliberately in all three.

Not done here — it needs a decision about cross-repo CI access that is outside
the scope of this change.

<a id="o-02"></a>

### O-02 — The `pi` agent runtime does not run the PRD/TRD/TASKS phase
**Severity:** Medium · **Status:** Open (pre-existing)

`DSDMOrchestrator._PI_PHASE_TO_ROLE_ID` deliberately excludes `PRD_TRD`:
`_run_prd_trd_phase` is a hardcoded multi-agent sub-workflow with its own
approval and sync logic that was never ported to `pi_session_runner`, so it
always runs on the legacy path regardless of `AGENT_RUNTIME`. The new TASKS
step inherits that limitation — it runs wherever the phase runs. This predates
the change and was not widened by it.

<a id="o-03"></a>

### O-03 — `lhs-agents` workflow is not wired into `workflow-orchestrator.ts`
**Severity:** Medium · **Status:** Open (deliberate)

In `lhs-agents` the workflow is reachable as a module (`runWorkflow`) and from
the CLI (`cli.ts --docs`), but `workflow-orchestrator.ts` does not call it.
That orchestrator enforces its own gate sequence — requirements must reach Jira
**and** Confluence before any test code is written — and inserting a document
stage into it changes that contract. Wiring it in is a decision for whoever
owns that gate, not a mechanical follow-up.

<a id="o-04"></a>

### O-04 — Effort estimates default to 1 unless supplied
**Severity:** Low · **Status:** Open (by design)

Intake has no way to estimate effort from prose, so every item defaults to
effort 1 unless the caller supplies a structured item with an `effort` field.
The consequence is that the "Effort" columns in `TASKS.md` and the MoSCoW
balance risk in the TRD are only meaningful when a requirement arrives with
estimates attached. Guessing would be worse than an obvious placeholder, so
this is intentional — but it should be read as "not yet estimated", not "small".
