---
name: confluence-management
description: Set up and maintain Confluence spaces, pages, DSDM PRDs/TRDs, decisions, and project status using an authorized Atlassian MCP connection. Use for Confluence structure, document publication, updates, and Jira-linked documentation.
---

# Confluence Management

Read `consultation.md` and `AGENTS.md` before any action. Follow their approval gates. This skill works in GitHub Copilot without Python, Pi, or an Anthropic extension.

## Connection and discovery

1. Verify that an authenticated Atlassian MCP connection is available in the current Copilot environment. If absent, report the integration as blocked and provide the proposed page structure only.
2. Discover the actual Confluence tools and accessible sites/spaces. Do not assume tool names, write privileges, or support for a particular editor format.
3. Read existing pages, parent/child structure, titles, page identifiers, versions, and editor format before creating or updating content.
4. Use the MCP connection's authenticated identity. Never place credentials or private tokens in repository Markdown.

## Set up a space or page hierarchy

1. Confirm the target site, space and intended documentation scope. Search for an existing space and matching pages first.
2. Propose a minimal hierarchy: Overview, Requirements (PRD), Technical Design (TRD), Architecture, Decisions, Delivery Evidence, and Handover. Create only pages needed for the approved task.
3. Request approval before creating a space, changing permissions, publishing new pages, or restructuring existing content.
4. Use only supported MCP operations and the editor/body format returned by the provider. Do not invent page IDs or version numbers.
5. Read back the created structure and report actual URLs and any skipped items.

## Update documentation

1. Fetch the latest page content and version immediately before editing.
2. Preserve existing material unless removal or replacement is explicitly requested. For an update, modify only the requested sections.
3. Produce clear PRDs/TRDs with traceable requirement IDs, MoSCoW priorities, functional and non-functional requirements, Gherkin acceptance criteria, assumptions, risks, and links to evidence where relevant.
4. Include Jira issue keys and GitHub PR links only when verified. Jira owns work-item status; Confluence owns approved documentation.
5. Obtain approval for external publication and other operations gated by `consultation.md`.
6. Apply the change using supported version-safe update semantics. On a conflict, re-fetch and reconcile; never overwrite a newer version blindly.
7. Fetch the updated page and verify its content, rendered tables, links, and parent placement when the available tools support that verification.

## Approval and safety

- Use G1 for unclear requirements, G2 for architecture decisions, G3 for restricted content or permission changes, G4 for publication, destructive moves or deletion, and G5 for missing acceptance evidence.
- Do not create duplicate pages when an appropriate existing page can be updated.
- Never publish secrets, personal data, unapproved drafts, or fabricated test results.
- If access or tooling is insufficient, stop the affected operation and describe exactly what is blocked.

## Output

Report space, page title, verified URL, created/updated sections, source requirements, approval status, and outstanding validation. Do not claim publication or successful formatting until confirmed.
