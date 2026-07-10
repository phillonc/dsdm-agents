---
applyTo: ".github/agents/**"
description: How agents reach MCP servers (Atlassian, GitHub, filesystem) via CLI tools that execute command prompts. Read this when an agent needs to call an MCP server.
---

# MCP CLI Integration Guide

Agents reach **MCP (Model Context Protocol) servers** — Atlassian (Jira /
Confluence), GitHub, the file system, and any other configured server — by
executing *command prompts* through a command-line MCP client. This is the
uniform, config-driven path that complements the first-party Python integrations
(`jira_*`, `confluence_*`): use a named Python tool when one exists; reach for
the MCP CLI tools for anything a server exposes that isn't wrapped yet.

## Configuration

MCP servers are declared once in **`.github/copilot/mcp-config.json`**
(the `mcpServers` shape shared by GitHub Copilot CLI and VS Code). Override the
location with `$MCP_CONFIG_PATH`. The client CLI is `$MCP_CLIENT` (default
`mcp call`) — set it to whichever MCP client the environment provides
(`copilot mcp`, `mcp`, …).

```jsonc
// .github/copilot/mcp-config.json
{ "mcpServers": {
    "atlassian":  { "command": "npx", "args": ["-y", "mcp-remote", "https://mcp.atlassian.com/v1/sse"] },
    "github":     { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] },
    "filesystem": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "generated"] }
} }
```

## The MCP CLI tools

Registered in `src/tools/integrations/mcp_tools.py` (category `mcp`):

| Tool | Purpose | Approval |
|------|---------|----------|
| `mcp_list_servers` | List configured MCP servers | read-only |
| `mcp_list_tools` | Discover a server's tools (`tools/list`) | read-only |
| `mcp_call_tool` | Execute a command prompt: call a server tool (`tools/call`) with JSON `arguments` | requires approval |
| `mcp_run_command` | Run a raw MCP method (`resources/read`, …) — escape hatch | requires approval |

### Usage pattern

1. `mcp_list_servers` — confirm which servers are wired up. If none, **silently
   skip** MCP steps (never block a phase on integration availability).
2. `mcp_list_tools(server="atlassian")` — discover the exact tool names before calling.
3. `mcp_call_tool(server="atlassian", tool="jira_create_issue", arguments={...})`
   — execute the command prompt for the feature you need.

### Safety

- `mcp_call_tool` / `mcp_run_command` are **dry-run by default**: they resolve
  and return the exact command without running it. They execute only when
  `MCP_EXECUTE=1` (or `execute=true` is passed) **and** a client CLI is
  configured. Inspect the `rendered_command` on a dry run before executing.
- Both mutating tools are marked `requires_approval` — honour Hybrid/Manual
  agent modes and pause for approval before executing.
- Never pass secrets, tokens, or PII as arguments; rely on the server's `env`
  block (which reads from the environment) for credentials.

## When to prefer what

- **Named Python tool exists** (`jira_create_issue`, `confluence_create_dsdm_doc`,
  …) → use it; it already handles output paths, validation, and sync.
- **No wrapper, but an MCP server exposes it** → use `mcp_call_tool`.
- **Neither** → do it locally (file tools) and note the gap in the hand-off.
