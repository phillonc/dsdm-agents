"""MCP (Model Context Protocol) CLI tools for DSDM agents.

These tools let an agent reach **MCP servers** — Atlassian (Jira/Confluence),
GitHub, the file system, and any other configured server — by executing
*command prompts* through a command-line MCP client. This complements the
first-party Python integrations (`jira_tools`, `confluence_tools`): where those
call vendor REST APIs directly, the MCP tools give agents a uniform,
config-driven way to invoke whatever an MCP server exposes.

Design notes
------------
* **Config-driven** — servers are declared once in an ``mcp-config.json``
  (``mcpServers`` shape, matching GitHub Copilot CLI / VS Code). The default
  location is ``.github/copilot/mcp-config.json`` or ``$MCP_CONFIG_PATH``.
* **Client-agnostic** — the client CLI is ``$MCP_CLIENT`` (whitespace-split),
  defaulting to ``mcp call``. Swap it for ``copilot mcp`` or any client that
  speaks the same ``--server/--method/--tool/--arguments`` flags.
* **Safe by default** — invoking a tool (``mcp_call_tool`` / ``mcp_run_command``)
  requires approval and only executes when ``$MCP_EXECUTE`` is truthy; otherwise
  it returns the fully-resolved command as a dry run. Discovery tools
  (``mcp_list_servers`` / ``mcp_list_tools``) are read-only.
"""

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..tool_registry import Tool, ToolRegistry

# MCP JSON-RPC methods understood by the client. A bare tool name is treated as
# ``tools/call <name>``.
_PROTOCOL_METHODS = {
    "tools/list",
    "tools/call",
    "resources/list",
    "resources/read",
    "prompts/list",
}

_DEFAULT_CLIENT = ["mcp", "call"]
_DEFAULT_CONFIG_PATHS = (
    ".github/copilot/mcp-config.json",
    ".vscode/mcp.json",
)


class MCPCliClient:
    """Bridge to MCP servers via a command-line MCP client."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        client: Optional[List[str]] = None,
    ) -> None:
        self._config_path = config_path or os.environ.get("MCP_CONFIG_PATH")
        self._servers: Optional[Dict[str, Dict[str, Any]]] = None
        if client is not None:
            self._client = list(client)
        elif os.environ.get("MCP_CLIENT"):
            self._client = shlex.split(os.environ["MCP_CLIENT"])
        else:
            self._client = list(_DEFAULT_CLIENT)

    # -- configuration -----------------------------------------------------
    def _resolve_config_path(self) -> Optional[Path]:
        if self._config_path:
            return Path(self._config_path)
        for candidate in _DEFAULT_CONFIG_PATHS:
            path = Path(candidate)
            if path.exists():
                return path
        return None

    @property
    def servers(self) -> Dict[str, Dict[str, Any]]:
        """Configured MCP servers, loaded lazily from the config file."""
        if self._servers is None:
            path = self._resolve_config_path()
            if path and path.exists():
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._servers = dict(data.get("mcpServers", data))
            else:
                self._servers = {}
        return self._servers

    @property
    def is_configured(self) -> bool:
        return bool(self.servers)

    def _server_env(self, server: str) -> Dict[str, str]:
        env = self.servers.get(server, {}).get("env", {}) or {}
        return {str(k): str(v) for k, v in env.items()}

    # -- command construction ---------------------------------------------
    def build_argv(
        self,
        server: str,
        method_or_tool: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Build the client argv for a server invocation."""
        if server not in self.servers:
            raise ValueError(
                f"Unknown MCP server '{server}'. Configured: {sorted(self.servers)}"
            )

        argv = list(self._client) + ["--server", server]
        if method_or_tool in _PROTOCOL_METHODS:
            argv += ["--method", method_or_tool]
        else:
            argv += ["--method", "tools/call", "--tool", method_or_tool]
        if arguments:
            argv += ["--arguments", json.dumps(arguments, sort_keys=True)]
        return argv

    # -- execution ---------------------------------------------------------
    def invoke(
        self,
        server: str,
        method_or_tool: str,
        arguments: Optional[Dict[str, Any]] = None,
        execute: Optional[bool] = None,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Resolve and (optionally) run a command prompt against a server."""
        argv = self.build_argv(server, method_or_tool, arguments)
        rendered = " ".join(shlex.quote(token) for token in argv)
        payload: Dict[str, Any] = {
            "success": True,
            "server": server,
            "command": method_or_tool,
            "arguments": arguments or {},
            "argv": argv,
            "rendered_command": rendered,
        }

        if execute is None:
            execute = _truthy(os.environ.get("MCP_EXECUTE"))
        if not execute:
            payload["executed"] = False
            payload["dry_run"] = True
            payload["note"] = (
                "Dry run — set MCP_EXECUTE=1 (or pass execute=true) with a client "
                "CLI configured ($MCP_CLIENT) to run this command."
            )
            return payload

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **self._server_env(server)},
            )
            payload.update(
                executed=True,
                dry_run=False,
                success=completed.returncode == 0,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired:
            payload.update(success=False, executed=True, error=f"MCP command timed out after {timeout}s")
        except FileNotFoundError as exc:
            payload.update(
                success=False,
                executed=False,
                error=f"MCP client not found ({exc}). Set $MCP_CLIENT to an installed client.",
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in the payload
            payload.update(success=False, executed=True, error=str(exc))
        return payload


def _truthy(value: Optional[str]) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# Module-level client reused across tool handlers.
_client = MCPCliClient()


# ==================== TOOL HANDLERS ====================

def _handle_list_servers() -> str:
    servers = _client.servers
    return json.dumps({
        "success": True,
        "configured": bool(servers),
        "servers": {
            name: {"command": spec.get("command"), "args": spec.get("args", [])}
            for name, spec in servers.items()
        },
        "count": len(servers),
    })


def _handle_list_tools(server: str) -> str:
    return json.dumps(_client.invoke(server, "tools/list"))


def _handle_call_tool(
    server: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
    execute: Optional[bool] = None,
) -> str:
    return json.dumps(_client.invoke(server, tool, arguments=arguments, execute=execute))


def _handle_run_command(
    server: str,
    method: str,
    arguments: Optional[Dict[str, Any]] = None,
    execute: Optional[bool] = None,
) -> str:
    return json.dumps(_client.invoke(server, method, arguments=arguments, execute=execute))


# ==================== REGISTRATION ====================

def register_mcp_tools(registry: ToolRegistry) -> None:
    """Register MCP CLI tools with the registry."""

    registry.register(Tool(
        name="mcp_list_servers",
        description=(
            "List the MCP servers configured for this repo (from "
            ".github/copilot/mcp-config.json or $MCP_CONFIG_PATH). Read-only."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_handle_list_servers,
        category="mcp",
    ))

    registry.register(Tool(
        name="mcp_list_tools",
        description=(
            "Discover the tools an MCP server exposes by running its 'tools/list' "
            "method through the CLI client. Read-only."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Configured MCP server name (e.g. 'atlassian', 'github').",
                },
            },
            "required": ["server"],
        },
        handler=_handle_list_tools,
        category="mcp",
    ))

    registry.register(Tool(
        name="mcp_call_tool",
        description=(
            "Execute a command prompt against an MCP server by calling one of its "
            "tools (tools/call). Pass the tool name and a JSON 'arguments' object. "
            "Dry-run unless MCP_EXECUTE is set or execute=true."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Configured MCP server name (e.g. 'atlassian', 'github').",
                },
                "tool": {
                    "type": "string",
                    "description": "The MCP tool to invoke (e.g. 'jira_create_issue').",
                },
                "arguments": {
                    "type": "object",
                    "description": "JSON arguments passed to the MCP tool.",
                },
                "execute": {
                    "type": "boolean",
                    "description": "Actually run the command (default: dry run unless MCP_EXECUTE).",
                },
            },
            "required": ["server", "tool"],
        },
        handler=_handle_call_tool,
        requires_approval=True,
        category="mcp",
    ))

    registry.register(Tool(
        name="mcp_run_command",
        description=(
            "Run a raw MCP protocol method (e.g. 'tools/call', 'resources/read') "
            "against a server — escape hatch for capabilities not covered by a "
            "named tool. Dry-run unless MCP_EXECUTE is set or execute=true."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Configured MCP server name.",
                },
                "method": {
                    "type": "string",
                    "description": "MCP method or tool name to invoke.",
                },
                "arguments": {
                    "type": "object",
                    "description": "JSON arguments for the method/tool.",
                },
                "execute": {
                    "type": "boolean",
                    "description": "Actually run the command (default: dry run unless MCP_EXECUTE).",
                },
            },
            "required": ["server", "method"],
        },
        handler=_handle_run_command,
        requires_approval=True,
        category="mcp",
    ))
