# DSDM Agents — Framework Overview

- **Repository:** `dsdm-agents`
- **Language:** Python 3.10+
- **Entry point:** `python main.py`
- **Browser console:** `python main.py --gui` (default `127.0.0.1:8770`)
- **Output:** everything an agent produces lands under `generated/<project-slug>/`

---

## What it does

DSDM Agents implements the **Dynamic Systems Development Method lifecycle as a
set of agents**. Each agent owns one phase — or one specialised role inside a
phase — and produces concrete artefacts on disk. Run a phase and you get a
document; run the workflow and you get the whole chain, each phase handing the
next its inputs.

Two things distinguish it from a prompt library:

**`role_definitions.py` is the single source of truth.** Tools, system prompt
and default mode per role live in one file, and
`python main.py --generate-agents` checks it for drift against the
`ToolRegistry` and the `.github/agents/*.agent.md` files. The Copilot agent
definitions and the Python agent classes cannot silently disagree.

**Autonomous Delivery Rooms.** A room (`src/rooms/`) is a multi-agent runtime
with its own state, health, progress, blockers, decisions, handoffs and
artefacts — a persistent workspace for a delivery, not a single agent call.

There are two execution runtimes for the same roles: the legacy Python agent
loop (`src/agents/base_agent.py`), and **pi.dev** (`--agent-runtime pi`) with
the same tool registry and approval semantics but a different engine.

## Best suited for

- **Running a real DSDM delivery**, phase by phase, with the artefacts each
  phase is supposed to produce.
- **Multi-agent delivery with visible state.** A delivery room shows who is
  blocked, what was decided, what was handed off and what exists on disk.
- **MoSCoW-disciplined requirements.** Everything — requirements, stories,
  roadmap items — is tagged Must / Should / Could / Won't.
- **Working from a coding-agent CLI.** `.github/agents/*.agent.md` and
  `.github/prompts/*.prompt.md` make every role and task available to GitHub
  Copilot CLI and any tool following the [AGENTS.md](https://agents.md/)
  standard.
- **Private or self-hosted models.** `LLM_PROVIDER=vllm` with
  `--agent-runtime pi` targets a self-hosted vLLM endpoint; **any** role may be
  configured onto it — there is no restriction reserving roles for a hosted
  provider.

## What it is not

- **Not a general-purpose agent framework.** The phases, roles and artefacts
  are DSDM's. Using it for non-DSDM work means fighting its structure.
- **Not a place to write into `src/`, `docs/` or the repo root.** Every agent
  run writes under `generated/<project-slug>/`. This is a hard convention.
- **Not free to skip quality on.** DSDM Principle #5 — *never compromise
  quality* — is enforced as a convention every agent must follow: tests run,
  lint passes, security scans are clean before a phase is complete.
- **Not permitted to touch locked paths.** `.azad/.locked-paths` lists files
  agents must not modify. Honour it.
- **Not a loop.** Once the deliverables exist on disk, an agent writes its
  summary and stops. Continuing to call tools after that is a bug, not
  thoroughness.

---

## Agents in this framework

Sixteen roles, defined in
[`src/agents/role_definitions.py`](../src/agents/role_definitions.py) and
mirrored as Copilot agents in `.github/agents/`.

### Phase agents

| Role id | Agent | Phase | Default mode | Produces |
|---|---|---|---|---|
| `feasibility` | Feasibility Agent | feasibility | Automated | Go/No-Go, top risks, DSDM fit |
| `product-manager` | Product Manager | prd_trd | Automated | PRD with MoSCoW priorities |
| `business-study` | Business Study Agent | business_study | Automated | Stakeholders, prioritised requirements, architecture |
| `functional-model` | Functional Model Agent | functional_model | Automated | Iterative prototypes + feedback |
| `design-build` | Design & Build Agent | design_build | Automated | Production code, tests, TRD |
| `implementation` | Implementation Agent | implementation | Hybrid | Deployment plan, smoke tests, handover |
| `devops` | DevOps Agent | devops | Hybrid | Quality gates, CI/CD, IaC, security scans |

### Design & Build specialists

| Role id | Agent | Default mode |
|---|---|---|
| `dev-lead` | Dev Lead | Hybrid |
| `frontend-developer` | Frontend Developer | Automated |
| `backend-developer` | Backend Developer | Automated |
| `automation-tester` | Automation Tester | Automated |
| `nfr-tester` | NFR Tester | Hybrid |
| `pen-tester` | Penetration Tester | **Manual** |
| `change-control` | Change Control Agent | Hybrid |

### Git Pin throughput agents

| Role id | Agent | Default mode |
|---|---|---|
| `git-pin-coder` | Git Pin Coding Agent | Automated |
| `git-pin-reviewer` | Git Pin Review Agent | Hybrid |

`design-build` hands off to dev-lead, frontend, backend and automation-tester;
`dev-lead` additionally hands off to nfr-tester and pen-tester.

### Modes

`AgentMode` is `manual`, `automated` or `hybrid`, overridable per run with
`--mode`. Separately, `WorkflowMode` (`src/agents/workflow_modes.py`) controls
who writes the code: `agent_writes_code`, `agent_provides_tips`, or
`manual_with_tips` — the developer writes and the agent advises.

---

## Basic scenarios

### 1. Set up

```bash
python3 -m venv env && source env/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ANTHROPIC_API_KEY required; JIRA_* / CONFLUENCE_* optional
```

### 2. Run one phase

```bash
python main.py --phase feasibility --input "A booking platform for independent gyms"
python main.py --phase business_study --input "…"
python main.py --phase design_build --input "…"
```

Phases: `feasibility`, `business_study`, `functional_model`, `design_build`,
`implementation`, `devops`.

### 3. Run the whole workflow

```bash
python main.py --workflow --input "A booking platform for independent gyms"
```

### 4. See what's available

```bash
python main.py --list-phases
python main.py --list-tools
python main.py --interactive        # or -i
```

### 5. Use the browser console

```bash
python main.py --gui                              # 127.0.0.1:8770, opens a browser
python main.py --gui --gui-port 9000 --no-browser
python main.py --gui --gui-host 0.0.0.0           # a token is generated automatically for non-loopback
```

See [`docs/GUI.md`](GUI.md).

---

## Complex scenarios

### An Autonomous Delivery Room, end to end

A room is the multi-agent form of a delivery. Create it, run it, watch it,
export it.

```bash
# 1. Create against a template
python main.py --room-create --room-project gym-booking --room-template mvp
# Templates: mvp | platform | migration | enterprise | compliance

# 2. Create and run in one step
python main.py --room-run --room-project gym-booking --room-template platform \
  --input "Multi-tenant booking platform for independent gyms"

# 3. Watch it
python main.py --room-status --room-project gym-booking

# 4. Re-create over an existing room
python main.py --room-create --room-project gym-booking --room-template mvp --room-overwrite
```

### Filter the delivery-room dashboard

The dashboard is composed of named sections; filter it rather than reading all
of it.

```bash
# Just the health and blockers
python main.py --room-dashboard --room-project gym-booking \
  --dashboard-sections summary,health,blockers

# Only what one agent is doing
python main.py --room-dashboard --room-project gym-booking \
  --dashboard-agent backend-developer

# Critical blockers in one phase, including resolved ones
python main.py --room-dashboard --room-project gym-booking \
  --dashboard-phase design_build \
  --dashboard-severity critical \
  --dashboard-include-resolved

# Artefacts of one type, written to a file
python main.py --room-dashboard --room-project gym-booking \
  --dashboard-artifact-type trd \
  --dashboard-output generated/gym-booking/dashboard.md

# Or the full export
python main.py --room-export --room-project gym-booking
```

Sections: `summary`, `health`, `agents`, `blockers`, `decisions`, `handoffs`,
`artifacts`, `actions`.

### The Git Pin high-throughput pipeline

Parallel agent execution for the coding phases:

```bash
python main.py --git-pin-pipeline --input "Implement the booking API" --max-concurrent 4
python main.py --git-pin-pipeline --input "…" --max-concurrent 8
```

Backed by `src/agents/git_pin_agent_core.py`,
`git_pin_coding_agent.py` and `git_pin_throughput_optimizer.py`.

### Switch runtime and provider

```bash
# Diagnose the pi.dev setup first
python main.py --pi-doctor

# Route eligible phases through pi.dev
python main.py --workflow --input "…" --agent-runtime pi

# Private/self-hosted vLLM — requires --agent-runtime pi
export LLM_PROVIDER=vllm
export DSDM_VLLM_BASE_URL=https://… DSDM_VLLM_MODEL_ID=…
python main.py --phase design_build --input "…" --agent-runtime pi --llm-provider vllm

# Other providers
python main.py --workflow --input "…" --llm-provider anthropic   # default
python main.py --workflow --input "…" --llm-provider ollama
```

Eligible phases for the pi runtime: `feasibility`, `business_study`,
`functional_model`, `design_build`, `implementation`, `devops`.

### Check the role definitions haven't drifted

```bash
python main.py --generate-agents
```

Checks `role_definitions.py` against the `ToolRegistry` and
`.github/agents/*.agent.md`, and exits. Run it after editing any of the three.

---

## Slash-style prompts (Copilot CLI and AGENTS.md-compatible tools)

These are the repository's slash commands. Run one with
`copilot --prompt-file .github/prompts/<file>.prompt.md`, or pick it from the
in-CLI `/` menu.

| Task | Prompt file |
|---|---|
| Full DSDM workflow | `run-full-workflow.prompt.md` |
| Feasibility only | `run-feasibility.prompt.md` |
| PRD generation | `run-product-management.prompt.md` |
| Business study only | `run-business-study.prompt.md` |
| Functional model iteration | `run-functional-model.prompt.md` |
| Design & Build only | `run-design-build.prompt.md` |
| Implementation / deploy | `run-implementation.prompt.md` |
| Code review | `code-review.prompt.md` |
| Security review | `security-review.prompt.md` |
| DevOps quality gate | `devops-quality-gate.prompt.md` |
| Scope change request | `run-change-request.prompt.md` |
| MCP sync (Jira/Confluence/GitHub) | `mcp-sync.prompt.md` |
| Open Engine (Linear queue) setup | `open-engine-linear-setup.prompt.md` |

Worked examples:

```bash
# Full workflow through the Copilot CLI
copilot --prompt-file .github/prompts/run-full-workflow.prompt.md

# A single phase, then its review gate
copilot --prompt-file .github/prompts/run-design-build.prompt.md
copilot --prompt-file .github/prompts/code-review.prompt.md
copilot --prompt-file .github/prompts/security-review.prompt.md
copilot --prompt-file .github/prompts/devops-quality-gate.prompt.md

# Mirror status into Jira/Confluence when a phase completes
copilot --prompt-file .github/prompts/mcp-sync.prompt.md
```

Scoped instruction files in `.github/instructions/` — `conventions`,
`dsdm-tools`, `integrations`, `mcp` — apply automatically to matching work.
The MCP server catalogue is `.github/copilot/mcp-config.json`; where a system is
reachable only as an MCP server, use `mcp_list_servers` → `mcp_list_tools` →
`mcp_call_tool` rather than a bespoke client.

---

## Conventions every agent must follow

1. **Output location** — write all artefacts under `generated/<project-slug>/`.
   Never write to `src/`, `docs/` or the repo root from an agent run.
2. **Project bootstrap** — call `project_init` (or create the folder skeleton)
   before writing files in a fresh project.
3. **No shortcuts on quality** — tests run, lint passes, security scans clean
   before a phase is complete.
4. **MoSCoW everywhere** — requirements, stories and roadmap items are tagged
   Must / Should / Could / Won't.
5. **Hand-off contract** — on finishing a phase, summarise the artefacts
   produced and the inputs the next phase needs.
6. **Jira / Confluence sync** — mirror status changes when those integrations
   are available (`jira_transition_issue`, `sync_work_item_status`,
   `confluence_update_page`).
7. **Stop when done** — write the final summary and stop; do not loop on tool
   calls.

---

## Relationship to the other DSDM frameworks

Three repositories run DSDM agent frameworks, and they are not copies of each
other:

| Repository | Framework | Shape |
|---|---|---|
| **`dsdm-agents`** (this one) | Python phase agents + delivery rooms | A full lifecycle runtime with persistent multi-agent state |
| **`DSDM-Agency`** | `agents_framework/` | A dependency-free crew library — Agent/Tool/Task/Crew mapped onto DSDM roles, techniques and products |
| **`lhs-agents`** | `agents/dsdm-dev/` | Requirements decomposition and TDD-first planning inside the LocalHighStreet platform |

All three are specified to ship the same **Requirement → PRD → TRD → TASKS**
pipeline (`WF-PRTT-001`) against one byte-identical spec —
`lhs-agents/docs/WORKFLOW-PRD-TRD-TASKS.md`. Run the same requirement through
each and the three `TASKS.md` files should differ only in the agent names: same
task IDs, same traceability, same ordering. A change to the stages, gates, ID
schemes or document headings is a change to that spec, applied to all three
repositories together.

> **Current state:** this repository does not yet contain `src/workflow/`. The
> shared pipeline is specified for it but not present here; the DSDM lifecycle
> agents above are what this repo runs today.

---

## Cautions

- **`.azad/.locked-paths` is binding.** Agents must not modify what it lists.
- **`generated/` is the only writable target for an agent run.**
- **`--llm-provider vllm` requires `--agent-runtime pi`** — it is rejected
  otherwise.
- **Run `--generate-agents` after touching `role_definitions.py`,
  `ToolRegistry` or any `.agent.md`.** These three drift silently otherwise.
- **The GUI binds to loopback by default.** A non-loopback `--gui-host`
  generates an access token; do not disable it to make a demo easier.

## See also

- [`README.md`](../README.md) — full project overview
- [`GETTING_STARTED.md`](../GETTING_STARTED.md) — step-by-step walkthrough
- [`AGENTS.md`](../AGENTS.md) — the AGENTS.md-standard instruction file
- [`docs/GUI.md`](GUI.md) · [`docs/TECHNICAL_REQUIREMENTS.md`](TECHNICAL_REQUIREMENTS.md) · [`docs/WORKFLOW_DIAGRAM.md`](WORKFLOW_DIAGRAM.md) · [`docs/DEVOPS_TOOLS.md`](DEVOPS_TOOLS.md)
- [`docs/category-defining-features/`](category-defining-features/) — delivery rooms, memory graph, traceability engine, pi runtime
