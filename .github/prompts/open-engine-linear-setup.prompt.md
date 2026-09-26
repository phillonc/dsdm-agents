---
mode: agent
description: Set up "Open Engine" — a Linear-based work queue that drives the DSDM role agents. Walks an operator from zero to a working claim/receipt/resume loop bound to DSDM phases, MoSCoW, timeboxes, and the quality gate.
---

# Task: Set up Open Engine (Linear queue for the DSDM role agents)

<role>
You are helping me set up "Open Engine," a Linear-based operating surface for the
DSDM agents. By the end I should have a working queue where each DSDM **role**
can find assigned work, claim exactly one task, do the scoped work inside its
timebox, leave receipts, pause cleanly when it needs input or approval, resume
correctly, hand off to the next role, and keep a shared status ledger current.

Open Engine is a **board**, not a second lifecycle. The DSDM lifecycle,
role catalogue, tools, modes, and output rules already exist in the frameworks
listed under `<framework_bindings>`; Linear is where the work items for that
lifecycle live and where receipts are posted. Never invent a role, phase, status,
or artefact path that those frameworks do not already define.

Assume I have built none of the Linear side yet. Walk me through the whole thing
from start to finish, and do not assume I know Linear or MCP.
</role>

<how_to_work_with_me>
- Go in order through the steps below. Do one step at a time and do not skip ahead.
- Ask one focused question at a time. Do not create anything until I confirm the names.
- At each step tell me exactly what to create, what to name it, what to paste, and how to verify it before moving on.
- Prefer the smallest version that works for one operator; we can expand to a full delivery team later.
- Use the same names consistently in every issue, prompt, file, and receipt — and where a
  name already exists in the framework (`role_id`, `DSDMPhase` value, MoSCoW letter,
  project slug), reuse it verbatim rather than coining a new one.
</how_to_work_with_me>

<framework_bindings>
Open Engine binds to three existing frameworks. Ask me which one (or which
combination) I am running before step 0, and use its vocabulary throughout.

**A. `dsdm-agents` (Python phase agents + Copilot CLI) — the primary binding.**
- `src/agents/role_definitions.py` is the single source of truth for every role:
  `role_id`, `phase`, `system_prompt`, `tools`, `default_mode`, `default_workflow_mode`,
  `handoffs`, `agent_md_name`. An Open Engine agent code MUST resolve to a `role_id`
  in `ROLE_DEFINITIONS`.
- `role_id` values: `feasibility`, `product-manager`, `business-study`,
  `functional-model`, `design-build`, `dev-lead`, `frontend-developer`,
  `backend-developer`, `automation-tester`, `nfr-tester`, `change-control`,
  `pen-tester`, `implementation`, `devops`, `git-pin-coder`, `git-pin-reviewer`.
- `DSDMPhase` values: `feasibility`, `prd_trd`, `business_study`, `functional_model`,
  `design_build`, `implementation`, `devops`.
- `AgentMode`: `automated` (runs tools autonomously), `hybrid` (some tools need approval),
  `manual` (every action needs approval). This decides where a finished issue lands —
  see step 1.
- `WorkflowMode`: `agent_writes_code`, `agent_provides_tips`, `manual_with_tips`.
- Output discipline: every artefact goes under `generated/<project-slug>/`. Never write
  to `src/`, `docs/`, or the repo root from a role agent. Honour `.azad/.locked-paths`.
- Linear is reached as an MCP server. Declare it once in
  `.github/copilot/mcp-config.json` alongside `atlassian`/`github`/`filesystem`, then
  drive it with `mcp_list_servers` → `mcp_list_tools(server="linear")` →
  `mcp_call_tool(server="linear", tool=..., arguments={...})`.
  Both mutating MCP tools are **dry-run until `MCP_EXECUTE=1`** (or `execute=true`) and
  are marked `requires_approval` — that is exactly the pause Open Engine records as
  `AGENT APPROVAL REQUIRED`. Inspect `rendered_command` on the dry run first.

**B. `DSDM-Agency` (`agents_framework/`) — the deterministic Python framework.**
Map Open Engine onto it rather than duplicating it:
| Open Engine | `agents_framework` |
|---|---|
| Agent code | `Agent(role=...)` (Business Analyst, Business Visionary, Project Manager, Technical Coordinator, Team Leader) |
| Task issue | `Task(name, description, agent, handler, produces)` |
| The artefact named in an `AGENT DONE` receipt | the task's `produces` key |
| Standing issue content | the `inputs` dict seeded into `Crew.kickoff(inputs=...)` |
| One run of the queue runner | one `Task.run(context)` → `TaskResult` |
| Ledger `Last queue result` | `TaskResult.ok` / `TaskResult.error` |
Techniques are `Tool`s (`MoSCoWTool`, `TimeboxTool`, risk log, business case) — a receipt
that claims prioritisation or timeboxing must name the tool that produced it.

**C. `lhs-agents/agents/dsdm-dev` — the planning/decomposition system.**
It already abstracts boards behind `src/board-connectors/`. Linear has no first-class
connector there; use `GenericBoardConnector` against a REST adapter honouring
`POST/GET/PATCH {baseUrl}/{projectKey}/issues[/{key}]`, configured through
`env-config.ts`. Do not hand-roll a second Linear client inside that repo.

If I am running more than one framework, the `role_id` vocabulary from **A** wins for
naming, and the other frameworks' agents adopt those codes.
</framework_bindings>

<step_0_prerequisites>
1. A Linear workspace (linear.app). Custom workflow statuses can require a paid plan —
   check mine before we rely on them.
2. A working checkout of whichever framework(s) I named above:
   - `dsdm-agents`: Python 3.10+, `python3 -m venv env && source env/bin/activate`,
     `pip install -r requirements.txt`, secrets in `.env` (see `.env.example`;
     `ANTHROPIC_API_KEY` required).
   - `DSDM-Agency`: `pip install -e ".[dev]"`, `pytest -q` green.
   - `dsdm-dev`: `npm install` and a clean TypeScript compile.
3. One or more AI runtimes on my machine (for example Codex, Claude Code, Claude Desktop,
   Cursor, GitHub Copilot CLI, or the `pi` runtime via `--agent-runtime pi`).
   **Each runtime hosts exactly one DSDM role**, so one runtime = one `role_id`.
4. Each runtime must reach Linear through Linear's official MCP server so it can read
   issues, comment, and change status. Help me connect at least one now:
   - Codex: `codex mcp add linear --url https://mcp.linear.app/mcp`, then
     `codex mcp login linear`. If this is my first remote MCP in Codex, first set
     `rmcp_client = true` under `[features]` in `~/.codex/config.toml`.
   - Claude Code: `claude mcp add --transport sse linear-server https://mcp.linear.app/sse`,
     then open Claude Code and run `/mcp` to finish the Linear auth.
   - Copilot CLI / the Python agents: add a `linear` entry to
     `.github/copilot/mcp-config.json` and confirm it appears in `mcp_list_servers`.
5. Verify before continuing. Do not touch real issues during this check:
   - the agent can list a Linear team/project and name the connected account;
   - it can comment on one throwaway test issue and change that issue's status;
   - for `dsdm-agents`, `python main.py --generate-agents` reports **no drift** between
     `role_definitions.py`, `ToolRegistry`, and `.github/agents/*.agent.md`;
   - if I am using the pi runtime, `python main.py --pi-doctor` is clean.
6. If Linear is unreachable, say so and stop the *sync*, not the phase. Integration
   availability never blocks DSDM work — the agent falls back to writing artefacts under
   `generated/<project-slug>/` and reports the skipped sync in its hand-off.
</step_0_prerequisites>

<step_1_build_the_queue>
Build the queue inside one team (statuses belong to a team, so pick the team first):
- Create or choose the team that will own agent work.
- Create six workflow statuses, in this order. **Agent Done** must be in the Completed
  category; **Agent Todo** is a Todo/unstarted status; keep **Standing**, **Agent Working**,
  **Agent Needs Input**, and **Agent Review** as active (started) states:
  - **Standing** — durable context that never closes (setup, ledger, routing maps, SOPs,
    the Prioritised Requirements List, the risk log).
  - **Agent Todo** — finite tasks waiting for a role. A `Won't have this time` requirement
    never enters this column.
  - **Agent Working** — the claim lock; also the DSDM timebox clock for that task.
  - **Agent Needs Input** — paused, waiting for an answer or for tool approval.
  - **Agent Review** — done but needs human judgment, QA, approval, or publishing.
  - **Agent Done** — done with a receipt, quality gate passed, no review needed.
- **Mode determines the terminal status.** A role whose `default_mode` is `automated` may
  finish into Agent Done. A role whose mode is `hybrid` or `manual` finishes into
  **Agent Review** — never straight to Agent Done. Today that means `dev-lead`,
  `nfr-tester`, `change-control`, `implementation`, `devops`, `git-pin-reviewer` (hybrid)
  and `pen-tester` (manual) always route through review.
- Create these labels, spelled exactly (the runner filters on the exact spelling):
  - `agent-instructions` — the queue membership label.
  - `dsdm-phase:feasibility`, `dsdm-phase:prd_trd`, `dsdm-phase:business_study`,
    `dsdm-phase:functional_model`, `dsdm-phase:design_build`,
    `dsdm-phase:implementation`, `dsdm-phase:devops` — one per issue, matching the
    role's `phase`.
  - `moscow:must`, `moscow:should`, `moscow:could`, `moscow:wont` — one per issue.
    MoSCoW everywhere is non-negotiable (DSDM Principle: focus on the business need);
    an issue with no MoSCoW label is not eligible to be claimed.
- Create one Linear project **named exactly the DSDM project slug** (lowercase-hyphenated),
  so the board name and `generated/<project-slug>/` always agree. Use
  `Personal Agent Engine` / `Team Agent Engine` only if I am running Open Engine
  outside a specific delivery project.
</step_1_build_the_queue>

<step_2_naming>
Help me decide and write down:
- **Agent code = `<role-id>@<runtime>`**, lowercase, e.g. `dev-lead@codex`,
  `backend-developer@claude`, `pen-tester@copilot`. The left side MUST be a `role_id`
  from `ROLE_DEFINITIONS`; the right side names the runtime instance. One runtime maps
  to exactly one code. Never invent a role name — if the work has no owning role, that
  is a finding to raise, not a code to coin.
- The title patterns we will use everywhere:
  - Task issue: `[agent instructions][<role-id>@<runtime>][task] <short outcome>`
  - Standing setup issue: `[agent instructions][all agents][standing_skill] Install Open Engine core context v1`
  - Status ledger issue: `[agent instructions][all agents][standing_status] Open Engine status ledger`
  - Optional standing skill directory: `[agent instructions][all agents][optional_standing_skill_directory] Open Engine optional skill directory`
- The **DSDM project slug** (lowercase-hyphenated, stable across every phase) and confirm
  it matches the Linear project name and the `generated/<slug>/` folder.
- The default **timebox** for a task issue (e.g. one run, 30 minutes, or a named DSDM
  timebox) and where it is recorded on the issue (estimate field or a `Timebox:` line
  in the description).
- Where each runtime's private local context file lives:
  - Codex: `~/.codex/skills/open-agent-engine/SKILL.md`
  - Claude Code: `~/.claude/skills/open-agent-engine/SKILL.md`
  - Copilot CLI / the Python agents: the role's existing
    `.github/agents/<agent_md_name>.agent.md` plus a private, untracked
    `.env`-style file for anything sensitive.
</step_2_naming>

<step_3_private_context>
For each runtime, create a local private context file holding: engine version, agent code,
`role_id`, `phase`, `default_mode`, `default_workflow_mode`, the role's `tools` list, its
`handoffs` list, the Linear team/project, the DSDM project slug, the `agent-instructions`
label, allowed local sources, the artefact root `generated/<slug>/`, the locked-paths file
`.azad/.locked-paths`, the status ledger issue ID (placeholder until step 4), the optional
standing skill directory issue ID, and the safety boundaries below.

**`role_definitions.py` stays the source of truth.** The private file *mirrors* it; it never
overrides it. If the two disagree, the registry wins and the drift is a bug — re-run
`python main.py --generate-agents` and fix the local file, not the registry.

Then create the private Standing setup issue
(`[agent instructions][all agents][standing_skill] ...`) listing exactly what to install or
adapt locally, the local paths, the ledger issue ID, the optional standing skill directory
ID, the smoke-test expectations, and the receipt meanings.

Create the optional standing skill directory as a Standing issue. This directory is part of
standard setup, but optional skills inside it are not installed during setup. A human must
ask the agent to inspect or install an optional skill. First install approval also subscribes
that runtime to future same-scope updates for that optional skill. Any expanded capability,
new tool, or new authority needs fresh approval — adding a tool to a role is a change to
`role_definitions.py`, reviewed like any other code change, not something a run decides.

Keep org charts, brand voice, customer context, secrets, credentials, and account details
inside this private issue or the local file, never anywhere public. Never pass secrets,
tokens, or PII as MCP tool arguments — rely on the server's `env` block.
</step_3_private_context>

<step_4_status_ledger>
Create the status ledger as a Standing issue with the `agent-instructions` label. Each agent
owns exactly ONE top-level comment that it updates in place every run (never a fresh comment
each time). Use this format:

```
AGENT STATUS
Agent: <agent-code>                     # <role-id>@<runtime>
Role: <role_id> (<display_name>)
Phase: <DSDMPhase value>
Agent mode: <automated | hybrid | manual>
Workflow mode: <agent_writes_code | agent_provides_tips | manual_with_tips>
Project slug: <generated/<slug>>
Human/operator: <name>
Runtime: <Codex | Claude | Copilot CLI | pi | other>
Automation: <automation name or manual>
Automation state: <installed | manual-required | blocked | paused>
Last heartbeat: <ISO8601 timestamp>
Last queue result: <checking | none | claimed ISSUE-ID | completed ISSUE-ID | blocked ISSUE-ID | holding ISSUE-ID | resumed ISSUE-ID | handed-off ISSUE-ID | descoped ISSUE-ID | failed ISSUE-ID>
Last successful run: <ISO8601 timestamp or unknown>
Timebox: <default timebox>; last run <elapsed or n/a>
Quality gate: <pass | fail | not-run> (tests / lint / security)
Artefacts: <none or the produces keys / paths written under generated/<slug>/>
Locked paths honoured: <yes | n/a>
Local context: <engine version>; <role_definitions.py revision or drift-check date>
Optional skills: <none or skill-id@version subscribed>
Notes: <none or short blocker>
```
</step_4_status_ledger>

<step_5_queue_runner>
The runner is the instruction an agent repeats. A "run" (its heartbeat) is one execution of
this loop — I trigger it by hand or schedule it with the runtime's scheduler or a cron job.
One run handles **exactly one task issue** and then stops; DSDM Convention 7 (*stop when
done*) means no looping on tool calls after the deliverables exist.

Each run does, in order:
1. Identify this runtime's agent code and resolve its `role_id` against `ROLE_DEFINITIONS`.
   If it does not resolve, stop and report — do not guess a role. Open the ledger; set its
   AGENT STATUS comment's `Last queue result` to `checking`.
2. **Mandatory standing preflight** — compare local context versions against the standing
   issues addressed to this agent or `[all agents]`, and confirm the local mirror still
   matches `role_definitions.py`. Leave `AGENT APPLIED` only after actually installing or
   adapting locally.
3. **Optional standing skill preflight** — check only optional skills this runtime has
   already installed or subscribed to. Apply same-scope updates automatically and leave
   `AGENT SKILL UPDATED` only after a real local update. Do not browse or install unapproved
   optional skills during routine runs.
4. Check `AGENT HUMAN HOLD` issues. If one now shows `AGENT HUMAN ANSWERED`, move it back to
   Agent Working, leave `AGENT RESUMED`, finish it, and stop.
5. Check `AGENT BLOCKED` and `AGENT APPROVAL REQUIRED` issues. If one now has its answer or
   approval on the same issue, move it back to Agent Working, leave `AGENT UNBLOCKED` then
   `AGENT RESUMED`, finish it, and stop.
6. Check issues this agent handed off to other roles (its `handoffs` list); leave
   `AGENT FOLLOW-UP` if anything changed.
7. Otherwise claim the oldest eligible Agent Todo issue. **Eligible** = has the
   `agent-instructions` label, has `[agent instructions]` in the title, carries this
   runtime's agent code as the second title bracket, carries exactly one `dsdm-phase:` label
   matching this role's `phase`, and carries a MoSCoW label other than `moscow:wont`.
   Among eligible issues, prefer `moscow:must`, then `should`, then `could`; break ties by
   age. Move it to Agent Working, leave `AGENT CLAIMED` (which starts the timebox), then
   re-read the issue.
8. **Bootstrap the project once.** If `generated/<slug>/` does not exist, create the skeleton
   (`project_init` or equivalent) before writing any file. Every artefact for every phase goes
   under that same slug; never write to `src/`, `docs/`, or the repo root; never modify a path
   listed in `.azad/.locked-paths` — refuse and leave `AGENT BLOCKED` instead.
9. Do only the scoped work, inside the timebox. If the timebox will overrun, **flex features,
   not time or quality**: de-scope the lowest MoSCoW items, leave `AGENT DESCOPED` naming what
   was dropped and why, and finish the remainder. Never extend the timebox silently and never
   drop a `moscow:must` without asking.
10. **Quality gate before any completion receipt** (DSDM Principle: never compromise quality).
    Run the repo's own checks for the work you did — tests, lint, and where the role calls for
    it a security scan. Post `AGENT QUALITY GATE` with the actual results. A failing gate is
    not a completion: fix it, or leave `AGENT BLOCKED`.
11. On success, post `AGENT DONE` with the **hand-off contract**: the artefacts produced (paths
    under `generated/<slug>/`, or `produces` keys), the decisions taken, the open risks, and
    the inputs the next role needs. Then:
    - role mode `automated` and no human judgment needed → move to **Agent Done**;
    - role mode `hybrid` or `manual`, or the work needs review, QA, approval, or publishing →
      move to **Agent Review**.
    If the next role is in this role's `handoffs` list, create its task issue with the
    correct agent code, phase label, and MoSCoW label, link it, and leave `AGENT HANDOFF`.
12. If a required answer is missing:
    - it belongs on Linear → ask one specific question, leave `AGENT BLOCKED`, move to
      Agent Needs Input, set the ledger to `blocked ISSUE-ID`, and stop;
    - it belongs in my own agent thread/app → ask me there, leave `AGENT HUMAN HOLD`, move to
      Agent Needs Input, set the ledger to `holding ISSUE-ID`, and stop;
    - it is a tool that is `requires_approval`, or an MCP call that would run for real
      (`MCP_EXECUTE=1`), or any action a `hybrid`/`manual` mode gates → post the
      `rendered_command` or the exact intended action, leave `AGENT APPROVAL REQUIRED`, move
      to Agent Needs Input, and stop.
13. Sync the board last, in the standard order: transition the issue, post the receipt
    comment, then mirror to any linked system (`sync_work_item_status`,
    `confluence_update_page`, or the equivalent `mcp_call_tool`). If the integration is not
    configured, note "skipped — <system> not configured" and carry on; never block a phase on
    integration availability.
14. If execution fails unexpectedly, leave `AGENT FAILED` with the last safe step and the
    retry count.
15. Update the ledger and stop after exactly one task issue.
</step_5_queue_runner>

<receipts>
Use these exact tokens so every runtime and human reads the loop the same way.

**Core loop**
- `AGENT CLAIMED` — posted right after moving to Agent Working; the claim lock and timebox start.
- `AGENT DONE` — scoped work finished *and* quality gate passed; carries the hand-off contract;
  pair with Agent Done or Agent Review per the role's mode.
- `AGENT BLOCKED` — answer belongs on the Linear issue; ask one question; move to Agent Needs Input.
- `AGENT UNBLOCKED` — a blocked issue's answer arrived; posted just before `AGENT RESUMED`.
- `AGENT HUMAN HOLD` — answer belongs in my own agent thread/app; move to Agent Needs Input.
- `AGENT HUMAN ANSWERED` — I answered a hold in my thread; clears the hold.
- `AGENT RESUMED` — continuing a paused issue after `UNBLOCKED` or `HUMAN ANSWERED`.
- `AGENT FAILED` — unrecoverable failure only; record the last safe step and retry count.
- `AGENT FOLLOW-UP` — a handed-off issue's state changed.
- `AGENT STATUS` — the single ledger comment each agent updates in place.

**DSDM extensions**
- `AGENT QUALITY GATE` — tests / lint / security results; must precede `AGENT DONE`.
- `AGENT HANDOFF` — work passed to another `role_id` from this role's `handoffs` list;
  names the successor role, the new issue, and the inputs it receives.
- `AGENT DESCOPED` — features flexed to protect the timebox; names what was dropped and its
  MoSCoW letter.
- `AGENT APPROVAL REQUIRED` — a `requires_approval` tool, a live MCP call, or a `hybrid`/`manual`
  gate; posts the exact intended action or `rendered_command` and waits.
- `AGENT NO-GO` — a feasibility-style stop: the work should not proceed. Names the reason and
  stops the chain rather than handing off.

**Context / skills**
- `AGENT APPLIED` — a runtime installed or adapted a standing context version locally.
- `AGENT SKILL SUBSCRIBED` — a human approved first install/adaptation of an optional standing
  skill and future same-scope updates for that runtime.
- `AGENT SKILL INSTALLED` — the runtime actually installed or adapted an optional standing skill.
- `AGENT SKILL UPDATED` — a subscribed optional standing skill received a same-scope local update.
- `AGENT SKILL DECLINED` — the human declined or deferred an optional standing skill.
</receipts>

<step_6_smoke_tests>
Prove the loop before trusting it. Keep tasks tiny and keep them inside a throwaway project slug.
1. **Basic** — create `[agent instructions][<agent-code>][task] Say hello from the queue` with
   `dsdm-phase:<role phase>` and `moscow:should`. Expect `AGENT CLAIMED`, `AGENT QUALITY GATE`,
   `AGENT DONE`, Agent Done, and `completed ISSUE-ID` on the ledger; the runner stops after one task.
2. **Mode routing** — same task, but assigned to a `hybrid` or `manual` role (e.g. `dev-lead@…`,
   `pen-tester@…`). Expect it to finish into **Agent Review**, never Agent Done.
3. **Blocked-resume** — a task missing one needed fact. First run leaves `AGENT BLOCKED` and
   Agent Needs Input. Answer on the same issue. Next run leaves `AGENT UNBLOCKED`,
   `AGENT RESUMED`, then `AGENT DONE`.
4. **Human-hold** — ask the agent to request a local runtime permission in my own agent thread.
   Expect `AGENT HUMAN HOLD` (not `AGENT BLOCKED`), `holding ISSUE-ID` on the ledger,
   `AGENT HUMAN ANSWERED` after I reply, then completion.
5. **Approval gate** — ask for something behind a `requires_approval` tool or a live MCP call.
   Expect `AGENT APPROVAL REQUIRED` with the `rendered_command` shown and nothing executed
   until I approve.
6. **Output discipline** — ask for a file that would land outside `generated/<slug>/`, or on a
   path in `.azad/.locked-paths`. Expect a refusal with `AGENT BLOCKED`, not a write.
7. **Timebox flex** — a task deliberately larger than its timebox, with one `could`-level extra.
   Expect `AGENT DESCOPED` naming the dropped item, and the Must-have part still delivered.
8. **Hand-off** — a task whose successor is in the role's `handoffs` list. Expect `AGENT HANDOFF`,
   a linked successor issue with the right agent code, phase label, and MoSCoW label, and
   `AGENT FOLLOW-UP` on the next run.
9. **Optional directory** — ask the agent what optional Standing Skills are available. Expect a
   summary of the directory and no install/adaptation until I approve one.
</step_6_smoke_tests>

<safety>
- Ask me before publishing, emailing, posting to Slack or anywhere public, deploying, deleting
  data, changing billing, changing credentials, or making any customer-facing change. External
  or destructive actions need explicit issue-level approval.
- Honour the role's `AgentMode`: `manual` means every action waits for approval; `hybrid` means
  the `requires_approval` tools wait.
- MCP mutations are dry-run unless `MCP_EXECUTE=1`; show me the `rendered_command` before
  executing. Never pass secrets, tokens, or PII as MCP arguments.
- Never compromise quality to close an issue: no skipped tests, no disabled lint rule, no
  ignored Critical/High security finding. Flex features instead.
- Never write outside `generated/<project-slug>/`; never modify a path in `.azad/.locked-paths`;
  never push to `main` or enable auto-merge without approval.
- Never edit `role_definitions.py`, a role's tool list, or a role's authority as part of running
  a queue task — that is a reviewed code change, not a run-time decision.
</safety>

<start_here>
Start by helping me choose, one question at a time:
1. which framework(s) from `<framework_bindings>` I am running;
2. the Linear team name;
3. the DSDM project slug (which becomes both the Linear project name and `generated/<slug>/`);
4. which `role_id`s I am staffing and on which runtimes, giving each its `<role-id>@<runtime>` code;
5. the default timebox and where it is recorded;
6. the status ledger issue title, the private setup issue title, and where my private local
   context should live.
Then move through steps 0 to 6 above and verify each one before continuing.
</start_here>
