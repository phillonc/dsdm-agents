# DSDM Agents — GitHub Copilot CLI Guide

This repository contains a suite of AI agents that implement the **Dynamic Systems Development Method (DSDM)** software lifecycle. Each agent owns one phase (or one specialised role inside a phase) and produces concrete artefacts under `generated/<project>/`.

This file is the project-level instruction file read by **GitHub Copilot CLI**, the **GitHub Copilot Coding Agent**, and any other tool that follows the [AGENTS.md](https://agents.md/) standard.

## Project layout

| Path | Purpose |
|------|---------|
| `src/agents/` | Python agent classes (one per role); `role_definitions.py` is the single source of truth for tools/system-prompt/mode per role |
| `src/orchestrator/` | DSDM workflow orchestrator that chains phases together; `pi_session_runner.py` runs a role through the pi.dev runtime when `AGENT_RUNTIME=pi` |
| `src/tools/` | Tool registry consumed by every agent (DSDM tools, file tools, integrations); `tool_service.py` bridges the registry to pi.dev |
| `src/rooms/` | Multi-agent "delivery room" runtime |
| `pi/` | pi.dev TypeScript workspace (`dsdm-tools-bridge`, `dsdm-approval-gate` extensions) — the `pi` agent execution runtime |
| `docs/` | Source-of-truth requirements, workflow diagram, technical reqs |
| `generated/` | **All agent output goes here** — one folder per project |
| `.github/agents/` | Copilot CLI custom agents (one `.agent.md` per role) |
| `.github/instructions/` | Scoped instruction files (tools, integrations, MCP, conventions) |
| `.github/prompts/` | Reusable task prompts (workflows, single-phase runs, deploys, MCP sync) |
| `.github/copilot/mcp-config.json` | MCP server catalogue for the Copilot CLI / MCP CLI tools |

## DSDM phase agents

| Phase | Agent file | Description |
|-------|-----------|-------------|
| Feasibility | `.github/agents/feasibility.agent.md` | Go/No-Go, top risks, DSDM fit |
| Product Management | `.github/agents/product-manager.agent.md` | PRD with MoSCoW priorities |
| Business Study | `.github/agents/business-study.agent.md` | Stakeholders, prioritised requirements, architecture |
| Functional Model | `.github/agents/functional-model.agent.md` | Iterative prototypes + feedback |
| Design & Build | `.github/agents/design-build.agent.md` | Production code, tests, TRD |
| Implementation | `.github/agents/implementation.agent.md` | Deployment plan, smoke tests, handover |
| DevOps | `.github/agents/devops.agent.md` | Quality gates, CI/CD, IaC, security scans |

## Design & Build specialised agents

| Role | Agent file | Mode |
|------|-----------|------|
| Dev Lead | `.github/agents/dev-lead.agent.md` | Hybrid |
| Frontend Developer | `.github/agents/frontend-developer.agent.md` | Automated |
| Backend Developer | `.github/agents/backend-developer.agent.md` | Automated |
| Automation Tester | `.github/agents/automation-tester.agent.md` | Automated |
| NFR Tester | `.github/agents/nfr-tester.agent.md` | Hybrid |
| Penetration Tester | `.github/agents/pen-tester.agent.md` | Manual |

## Reusable tasks (slash-style prompts)

Run with `copilot --prompt-file .github/prompts/<file>.prompt.md` (or via the in-CLI `/` menu).

| Task | File |
|------|------|
| Full DSDM workflow | `.github/prompts/run-full-workflow.prompt.md` |
| Feasibility only | `.github/prompts/run-feasibility.prompt.md` |
| PRD generation | `.github/prompts/run-product-management.prompt.md` |
| Business study only | `.github/prompts/run-business-study.prompt.md` |
| Design & Build only | `.github/prompts/run-design-build.prompt.md` |
| Implementation / deploy | `.github/prompts/run-implementation.prompt.md` |
| Code review | `.github/prompts/code-review.prompt.md` |
| Security review | `.github/prompts/security-review.prompt.md` |
| MCP sync (Jira/Confluence/GitHub) | `.github/prompts/mcp-sync.prompt.md` |

## Conventions every agent must follow

1. **Output location** — write all generated artefacts under `generated/<project-slug>/`. Never write to `src/`, `docs/`, or repo root from an agent run.
2. **Project bootstrap** — call the equivalent of `project_init` (or create the folder skeleton via `mkdir`/`Write`) before writing files in a fresh project.
3. **No shortcuts on quality** — DSDM Principle #5: *Never compromise quality*. Tests must run, lint must pass, security scans must be clean before marking a phase complete.
4. **MoSCoW everywhere** — requirements, user stories, and roadmap items must be tagged Must / Should / Could / Won't.
5. **Hand-off contract** — when a phase finishes, summarise the artefacts produced and the inputs the next phase needs.
6. **Jira / Confluence sync** — when those integrations are available, mirror status changes (`jira_transition_issue`, `sync_work_item_status`, `confluence_update_page`). If a system is reachable only as an **MCP server**, use the MCP CLI tools (`mcp_list_servers` → `mcp_list_tools` → `mcp_call_tool`) to execute the same command prompts — see `.github/instructions/mcp.instructions.md`.
7. **Stop when done** — once the deliverables exist on disk, write a final summary and stop. Do not loop on tool calls.

## Environment

- Python 3.10+; create venv via `python3 -m venv env && source env/bin/activate`.
- Install: `pip install -r requirements.txt`.
- Configure secrets in `.env` (see `.env.example`) — `ANTHROPIC_API_KEY` is required; `JIRA_*` / `CONFLUENCE_*` are optional.
- Entry point: `python main.py --workflow --input "..."` or `python main.py --phase <phase> --input "..."`.

## Agent execution runtime

By default every phase runs on the legacy Python agent loop (`src/agents/base_agent.py`). Pass `--agent-runtime pi` (or set `AGENT_RUNTIME=pi`) to route eligible phases (feasibility, business_study, functional_model, design_build, implementation, devops) through [pi.dev](https://pi.dev/) instead — same tool registry and approval semantics, different execution engine. This is also how a private/self-hosted vLLM model is used: set `LLM_PROVIDER=vllm` plus `DSDM_VLLM_BASE_URL`/`DSDM_VLLM_MODEL_ID` alongside `--agent-runtime pi`. Any role may be configured onto vLLM — there is no built-in restriction reserving specific roles for a hosted provider. Run `python main.py --pi-doctor` to check the setup, and `python main.py --generate-agents` to check `role_definitions.py` for drift against `ToolRegistry`/`.github/agents/*.agent.md`. See `docs/category-defining-features/11-pi-agent-runtime/` for the full design and current migration state.

## Locked paths

`.azad/.locked-paths` lists files agents must not modify. Always honour it.

## Further reading

- `README.md` — full project overview
- `GETTING_STARTED.md` — step-by-step walkthrough
- `docs/TECHNICAL_REQUIREMENTS.md` — system TRD
- `docs/WORKFLOW_DIAGRAM.md` — end-to-end flow
- `docs/DEVOPS_TOOLS.md` — installed tooling and versions
