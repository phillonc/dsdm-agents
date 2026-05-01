# GitHub Copilot CLI agents — DSDM

This directory holds custom agent definitions for [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) following the [`.agent.md`](https://docs.github.com/en/copilot/reference/custom-agents-configuration) format.

## How to use

### From the CLI
```bash
# Pick an agent interactively
copilot

# Run with a specific agent
copilot --agent feasibility "<your prompt>"

# Run a saved task / prompt
copilot --prompt-file .github/prompts/run-full-workflow.prompt.md
```

### From VS Code
The same files are recognised by GitHub Copilot in VS Code. Use the agent chooser in chat (`@feasibility`, `@design-build`, etc.).

## Agent catalogue

### DSDM phase agents

| File | Phase | Mode | When to use |
|------|-------|------|-------------|
| `feasibility.agent.md` | Feasibility | Automated | Brand-new project: assess viability |
| `product-manager.agent.md` | PRD/TRD | Automated | Have feasibility output → need PRD |
| `business-study.agent.md` | Business Study | Automated | Have PRD → need MoSCoW + architecture + timeboxes |
| `functional-model.agent.md` | Functional Model | Automated | Build prototypes & gather feedback |
| `design-build.agent.md` | Design & Build | Automated | Build production code with tests + TRD |
| `implementation.agent.md` | Implementation | Hybrid | Deploy to prod with rollback + handover |
| `devops.agent.md` | Cross-cutting | Hybrid | Quality gates, CI/CD, IaC, security |

### Design & Build specialists

| File | Role | Mode |
|------|------|------|
| `dev-lead.agent.md` | Tech leadership, TRD, ADRs, code review | Hybrid |
| `frontend-developer.agent.md` | UI / components / a11y | Automated |
| `backend-developer.agent.md` | APIs / data / business logic | Automated |
| `automation-tester.agent.md` | Unit / integration / E2E tests + CI | Automated |
| `nfr-tester.agent.md` | Performance / scalability / a11y / chaos | Hybrid |
| `pen-tester.agent.md` | Security testing & OWASP review | Manual |

## Modes

- **Automated** — runs without per-step approval
- **Hybrid** — runs autonomously but pauses before risky / destructive steps
- **Manual** — every action requires explicit approval

## Frontmatter fields used

```yaml
---
name: <agent-id>          # used as @<name> handle
description: <one-liner>  # required; shown in agent picker
tools: [read, write, edit, search, execute]
model: claude-sonnet-4-6  # optional pin
handoffs:                 # optional — ordered hand-off targets
  - label: "..."
    agent: <other-agent>
---
```

## Related

- `../../AGENTS.md` — repo-wide project instructions
- `../instructions/` — scoped guidance (tools catalogue, integrations, conventions)
- `../prompts/` — reusable task prompts
- `../../README.md` — full project overview
- `../../GETTING_STARTED.md` — walkthrough
