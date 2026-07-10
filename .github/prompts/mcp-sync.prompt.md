---
mode: agent
description: Sync DSDM artefacts to external systems (Jira, Confluence, GitHub) by executing command prompts against configured MCP servers via the CLI tools.
---

# Task: Sync via MCP servers

Push the current phase's artefacts to the relevant external system through the
**MCP CLI tools**, executing command prompts against configured MCP servers. See
`.github/instructions/mcp.instructions.md` for the full contract.

## Inputs
- **Project slug** (the `generated/<slug>/` folder)
- **Target system**: `atlassian` (Jira/Confluence), `github`, or another configured server
- **Feature**: what to sync (e.g. publish the business study, seed the backlog, open a release issue)

## Steps
1. Run `mcp_list_servers` — confirm the target server is configured. If it is not,
   report "MCP server '<name>' not configured — skipping" and stop (never block).
2. Run `mcp_list_tools(server="<target>")` to discover the exact tool names.
3. Build the arguments from the on-disk artefacts under `generated/<slug>/`.
4. Execute the command prompt with `mcp_call_tool(server="<target>", tool="<tool>", arguments={...})`.
   - It is a **dry run** by default: inspect the returned `rendered_command`.
   - To actually run it, set `MCP_EXECUTE=1` (and ensure `$MCP_CLIENT` is set) or
     pass `execute=true`, then approve when prompted.
5. For raw protocol methods not exposed as a tool, use `mcp_run_command`.

## Output
- The `rendered_command` for each MCP call (audit trail)
- The server response (when executed) or a note that it ran as a dry run
- A one-line summary of what was synced and where

## Safety
- Never pass secrets/tokens/PII as arguments — rely on each server's `env` block.
- `mcp_call_tool` / `mcp_run_command` require approval; honour Hybrid/Manual modes.
