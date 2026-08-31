# Progress — Requirement → PRD → TRD → TASKS rollout

**Change:** `WF-PRTT-001` implemented across three repositories
**Branch:** `claude/repo-workflow-prd-trd-tasks-wb47uu` (all three)
**Date:** 2026-08-31
**Status:** Delivered and pushed. Open items in [`findings.md`](findings.md).

An identical copy of this document lives in `DSDM-Agency`, `dsdm-agents` and
`lhs-agents`, alongside [`WORKFLOW-PRD-TRD-TASKS.md`](WORKFLOW-PRD-TRD-TASKS.md).

---

## 1. Objective

Give all three agent repositories the **same** workflow: when a requirement is
inputted, the agent framework produces a PRD, then a TRD, then a TASKS markdown
file, so that **each agent has its own set of tasks** to complete.

## 2. What was delivered

One specification, three implementations of it.

```
requirement ─▶ [0 intake] ─▶ [1 PRD] ─▶ [2 TRD] ─▶ [3 TASKS]
                              PRD.md     TRD.md     TASKS.md
```

| Stage | Owning lane | Gate to enter | Product |
|-------|-------------|---------------|---------|
| 0 `INTAKE` | product | requirement has a non-empty title | normalised requirement |
| 1 `PRD` | product | ≥ 1 requirement item | `PRD.md` |
| 2 `TRD` | architecture | ≥ 1 functional requirement | `TRD.md` |
| 3 `TASKS` | delivery | ≥ 1 component | `TASKS.md` |

`TASKS.md` is the deliverable the request was about: one section per agent,
each with its own checklist, every task traced back through a TRD component to
the requirement it came from, with dependencies naming what has to land first.

**The central design decision** was to define the workflow over nine delivery
*lanes* (product, architecture, data, backend, frontend, security, qa, devops,
delivery) rather than over agent names. The three repositories have entirely
different rosters — DSDM roles, Claude-SDK phase agents, and TypeScript role
agents — and lanes are what let them share one pipeline without either
flattening the rosters or forking the spec.

## 3. Sequence of work

| # | Step | Outcome |
|---|------|---------|
| 1 | Surveyed all three repositories | Found `dsdm-agents` already had PRD and TRD generation but no task breakdown ([F-10]); `DSDM-Agency` had a clean deterministic framework to host the reference implementation; `lhs-agents` had a DSDM dev-agent package with its own role union |
| 2 | Wrote the shared specification | Stages, gates, ID schemes, document headings, lane routing, lane→agent mapping |
| 3 | Built the reference implementation in `DSDM-Agency` | Pinned exact renderer behaviour before porting anything |
| 4 | Reconciled the spec against it | Six statements had drifted ([F-05]); corrected before the ports were written |
| 5 | Ported to `dsdm-agents` and wired into the orchestrator | TASKS step added to the existing `PRD_TRD` phase |
| 6 | Ported to `lhs-agents` in TypeScript | Plus a `--docs` CLI mode |
| 7 | Verified cross-repo parity | Same requirement through the Python and TypeScript ports |
| 8 | Documentation, tests, commits, push | Three branches pushed |

Building the reference implementation *first* and only then correcting the spec
was the sequencing that mattered: the two ports were written against a
description that had already survived contact with working code.

## 4. What landed, per repository

### `DSDM-Agency` — reference implementation
Commits `1610cda`, `d6dfaad`

| Path | What |
|------|------|
| `agents_framework/workflow/` | `model` · `intake` · `routing` · `stages` · `documents` · `pipeline` · `__init__` |
| `agents_framework/tools/workflow_docs.py` | The stages as framework `Tool`s |
| `agents_framework/tasks/workflow_tasks.py` | The stages as crew tasks + `requirement_workflow_crew()` |
| `agents_framework/agents/dsdm_agents.py` | Added `solution_developer()` and `solution_tester()` so every lane has an owner; wired workflow tools onto existing roles |
| `examples/requirement_to_tasks.py` | Runnable end-to-end demo |
| `tests/test_workflow.py` | 33 tests |
| Docs | `docs/WORKFLOW-PRD-TRD-TASKS.md`, `docs/08-agents-framework.md`, `README.md`, `.gitignore` |

Entry points: `run_workflow()` and `requirement_workflow_crew()`.

### `dsdm-agents` — Python port, wired into the orchestrator
Commits `745910e`, `37fffb0`

| Path | What |
|------|------|
| `src/workflow/` | The same seven modules, with this repo's roster and `generated/` output paths |
| `src/tools/workflow_tools.py` | `run_requirement_workflow` (writes) and `generate_task_breakdown` (previews) |
| `src/tools/dsdm_tools.py` | Registers both in the DSDM tool registry |
| `src/orchestrator/dsdm_orchestrator.py` | The TASKS step inside `_run_prd_trd_phase`, plus `_run_requirement_task_breakdown()`; result carried to the next phase |
| `src/agents/{product_manager,dev_lead}_agent.py` | The two tools added to those rosters |
| `tests/test_requirement_workflow.py` | 31 tests |
| Docs | `docs/WORKFLOW-PRD-TRD-TASKS.md`, `docs/WORKFLOW_DIAGRAM.md`, `README.md`, `AGENTS.md` |

The new step sits **alongside** the existing LLM-driven agents, not in place of
them, and writes to a different path so nothing is clobbered. Because it takes
no LLM call, the three deliverables now exist and agree with each other
whatever the model produced. The `PRD_TRD` enum value was deliberately not
renamed — `main.py` and saved configs reference it.

### `lhs-agents` — TypeScript port
Commit `5d1d4bc`

| Path | What |
|------|------|
| `agents/dsdm-dev/src/requirement-workflow/` | The same seven modules in TypeScript |
| `agents/dsdm-dev/cli.ts` | `--docs` mode: run the workflow over requirement files |
| `.../requirement-workflow/__tests__/` | 33 tests |
| Docs | `docs/WORKFLOW-PRD-TRD-TASKS.md`, `CLAUDE.md`, `agents/dsdm-dev/README.md` |

Tasks whose lane maps to a `Role` in `types.ts` carry it, so they can become
work items. Lanes with no matching role carry none rather than a made-up one.

## 5. Verification

### Tests

| Repository | New | Suite total | Result |
|------------|-----|-------------|--------|
| `DSDM-Agency` | 33 | 48 | All pass |
| `dsdm-agents` | 31 | 177 | All pass |
| `lhs-agents` | 33 | 1138 passing | All pass; `tsc` and `eslint` clean |

Each suite asserts the same invariants from spec §9 against its own port: every
stage is gated, every requirement traces forward into a component and on into a
task, every requirement gets a QA owner, renderers are pure, lane order is
fixed.

`lhs-agents` also has 53 suites that fail to *run* on missing third-party
modules, and 2 `type-check:ci` errors in a file this change does not touch.
Both were confirmed **pre-existing** by stashing the change and re-running —
identical before and after. See [F-08]. The change took the passing test count
from 1105 to 1138.

### Cross-repo parity

The same requirement was run through the Python reference implementation and
the TypeScript port, and the outputs compared:

| Comparison | Result |
|------------|--------|
| `PRD.md` headings | identical |
| `TRD.md` headings | identical |
| `TASKS.md` headings | identical apart from agent names |
| All identifiers (`REQ-`, `PRD-FR-`, `PRD-NFR-`, `TRD-C-`, `TRD-R-`, `TASK-`) in all three documents | identical |
| `docs/WORKFLOW-PRD-TRD-TASKS.md` across three repos | identical by checksum (`f918a8f…`) |

Which is the property the whole exercise was for: **run one requirement through
all three repositories and the three `TASKS.md` files differ only in who is
named as the owner.**

## 6. Problems found and fixed

Ten findings, detailed in [`findings.md`](findings.md). The two that mattered:

- **[F-01] Lane routing matched keywords mid-word.** `ui` is a substring of
  *build* and *requirement*, so nearly every requirement would have been routed
  to the frontend — putting work on the wrong agent's checklist and dropping it
  from the right one. Fixed with word-boundary anchoring.
- **[F-02] Per-agent counts silently dropped lanes.** Several roles own more
  than one lane, and a dictionary keyed on the agent name overwrote rather than
  accumulated, so a multi-lane agent reported only its last lane's tasks. Fixed
  by moving the merge onto `TaskPlan.assignments()` so every caller inherits it
  — it had already recurred in three separate places.

## 7. Not done

Deliberately out of scope, or blocked on a decision that is not mine:

| Item | Why |
|------|-----|
| **Pull requests** | Not requested. The three branches are pushed and ready. |
| **A check keeping the three spec copies in step** — [O-01] | Needs a decision on cross-repo CI access. This is the highest open risk: the copies are identical today with nothing enforcing it, the same drift the UCAF/SSSF mirror already suffers. |
| **`pi` runtime support for the phase** — [O-02] | `PRD_TRD` was already excluded from the pi path before this change; the new step inherits that and does not widen it. |
| **Wiring the workflow into `lhs-agents/workflow-orchestrator.ts`** — [O-03] | That orchestrator enforces a requirements-to-Jira-and-Confluence gate before any test code. Inserting a document stage changes that contract — a decision for whoever owns the gate. |
| **Effort estimation from prose** — [O-04] | Intake cannot estimate, so effort defaults to 1. Guessing would be worse than an obvious placeholder; read the column as "not yet estimated". |

## 8. How to use it

```bash
# DSDM-Agency
python -m examples.requirement_to_tasks

# lhs-agents
npx ts-node agents/dsdm-dev/cli.ts --docs --req docs/spec.md
```

```python
# DSDM-Agency
from agents_framework.workflow import run_workflow
result = run_workflow(requirement_text)

# dsdm-agents
from src.workflow import run_workflow
result = run_workflow(requirement_text, project="Merchant Portal")

result.plan.assignments()    # agent -> the lanes and task IDs they own
result.written["TASKS.md"]   # path to the per-agent checklist
```

```ts
// lhs-agents
import { runWorkflow } from './src/requirement-workflow';
const result = runWorkflow(requirementText, { outputRoot: 'workflow-output' });
result.assignments;
```

In `dsdm-agents` it also runs automatically: the `PRD_TRD` phase ends by
producing all three documents and reporting each agent's task count.

[F-01]: findings.md#f-01
[F-02]: findings.md#f-02
[F-05]: findings.md#f-05
[F-08]: findings.md#f-08
[F-10]: findings.md#f-10
[O-01]: findings.md#o-01
[O-02]: findings.md#o-02
[O-03]: findings.md#o-03
[O-04]: findings.md#o-04
