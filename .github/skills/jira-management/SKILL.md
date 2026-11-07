---
name: jira-management
description: Set up, inspect, and maintain Jira projects, issues, workflows, assignments, and acceptance evidence through an authorized Atlassian MCP connection. Use for Jira setup, backlog creation, status updates, and DSDM issue tracking.
---

# Jira Management

Read `consultation.md` and `AGENTS.md` before any action. Follow their approval gates. This skill is usable from GitHub Copilot without Python, Pi, or an Anthropic extension.

## Connection and discovery

1. Check whether the current Copilot environment exposes an authenticated Atlassian MCP server. If not, explain that Jira operations are blocked until the user connects one; do not claim configuration succeeded.
2. Discover the actual Jira tools, their input schemas, accessible sites, project keys, issue types, and permissions. Do not assume Python `jira_*` tools or a specific MCP tool name are available.
3. Use read-only operations first to inspect existing project configuration, workflows, issue types, statuses, fields, boards, and current issues.
4. Never request credentials in chat or put tokens in Markdown, source control, tool arguments, or logs. Use the MCP connection's authenticated account.

## Set up a Jira project

1. Ask for the project/site and desired project type only when not already specified or discoverable.
2. Inspect existing configuration to avoid duplicates. Present a short proposed change list covering issue types, workflow statuses, permissions, and fields.
3. Obtain explicit approval before creating a project, changing workflows, permissions, issue schemes, or automation.
4. Apply only approved changes with supported MCP operations. If a required tool is missing, report the gap; do not improvise an API call or claim completion.
5. Read back the resulting project configuration and report verified changes and remaining gaps.

## Create and maintain DSDM work

1. Decompose approved scope into Epic → Story/Task → Sub-task only where the target Jira project supports those types.
2. Every item must have a traceable objective, owner, reviewer, MoSCoW priority, acceptance criteria (prefer Given/When/Then), dependencies, and verification requirements.
3. Check for an existing matching issue before creating a new one. Do not create duplicates.
4. Map MoSCoW to supported labels or fields; never assume a custom field exists.
5. Assign only real, authorized Jira users. Agent names may be tracked in a supported field, label, or description, but do not impersonate Jira users.
6. Update issue status only after checking available transitions. Attach actual commit/PR links and test evidence; do not mark Done without verified acceptance.
7. Read back changed issues and return their keys/links with a concise audit summary.

## Approval and safety

- Read-only discovery needs no extra approval beyond normal access.
- Obtain explicit authorization for issue creation, bulk edits, transitions, assignments, project configuration, and external publication where required by `consultation.md`.
- Require G1 for ambiguous requirements, G2 for workflow/schema changes, G3 for permission changes, G4 for irreversible actions, and G5 for failed quality checks.
- Never delete issues, alter access, or change project-wide settings without approval specific to the action.
- If Jira is unavailable, provide a proposed issue plan without pretending it was synchronized.

## Output

Report site/project, issue keys, before/after changes, evidence links, approvals obtained, operations not performed, and blockers. Keep Jira as the canonical work-item status system; do not duplicate complete PRD/TRD documents into issue descriptions when a Confluence link is appropriate.
