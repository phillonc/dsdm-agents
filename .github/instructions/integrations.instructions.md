---
applyTo: ".github/agents/**"
description: How agents integrate with Jira, Confluence, GitHub, and the local file system. Read this when an agent needs to sync work items or publish docs.
---

# Integrations Guide

## Atlassian (Jira + Confluence)

### Activation
- The Atlassian integration is **opt-in**. It is active when both:
  1. The corresponding env vars are set (`JIRA_URL`, `JIRA_USER`, `JIRA_TOKEN`, `CONFLUENCE_URL`, `CONFLUENCE_USER`, `CONFLUENCE_TOKEN` — see `.env.example`); and
  2. The orchestrator was started with `include_jira=True` / `include_confluence=True`.
- If either is missing, **silently skip** the sync calls — never block a phase on integration availability.

### Standard sync pattern
For every work-item lifecycle change emit:
1. `jira_transition_issue(issue_key, target_status)`
2. `jira_add_comment(issue_key, comment)` with the relevant context
3. `sync_work_item_status(issue_key)` — updates Confluence pages mapped to that issue

### Mapping
Jira issues are mapped to Confluence pages via `jira_set_confluence_page_mapping(issue_key, page_id)` once and then synced automatically by `sync_work_item_status`.

### MoSCoW labelling
When creating a Jira issue from a requirement, set the `priority` label to one of `MoSCoW-Must`, `MoSCoW-Should`, `MoSCoW-Could`, `MoSCoW-Wont`.

### DSDM phase pages
Use `confluence_create_dsdm_doc(phase=..., title=..., content=...)` for canonical phase documentation:
- Feasibility Report
- Business Study
- Functional Model Report
- Technical Requirements Document (TRD)
- Implementation / Handover

## GitHub

### Branching
The current branch for this iteration is `claude/create-dsdm-copilot-agents-vIbuC`. Create your own feature branch off `main` for new work; do **not** push directly to `main`.

### Commits
- Conventional Commits style (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`).
- Each commit must be atomic and pass tests.
- Reference the Jira key in the commit footer when applicable: `Refs: PROJ-123`.

### Pull requests
- Title: short, imperative.
- Body: summary + test plan.
- Never enable auto-merge or force-push without explicit approval.

### Locked paths
`.azad/.locked-paths` lists paths agents must not modify. Always honour it.

## Local file system

### Output discipline
- Every artefact lands under `generated/<project-slug>/`.
- Never write to `src/`, `docs/`, or repo root from a phase agent.
- Use `project_init` (or equivalent skeleton creation) once per project, then `file_write` for content.

### Project slug
- Lowercase, hyphenated.
- Derived from the user's input project name.
- Stable across phases — every phase writes to the **same** `generated/<slug>/`.

## Web

- Outbound HTTP from agents must go through the configured tool (`WebFetch`, MCP) — no raw `curl` for production data.
- Never POST credentials, tokens, secrets, or PII to third-party services.
