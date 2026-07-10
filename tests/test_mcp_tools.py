"""Tests for the MCP CLI tools."""

import json

from src.tools.integrations.mcp_tools import MCPCliClient, register_mcp_tools
from src.tools.tool_registry import ToolRegistry

_SERVERS = {
    "atlassian": {"command": "npx", "args": ["-y", "mcp-remote", "https://example/sse"]},
    "github": {"command": "npx", "args": ["-y", "server-github"], "env": {"TOKEN": "x"}},
}


def _client(tmp_path):
    cfg = tmp_path / "mcp-config.json"
    cfg.write_text(json.dumps({"mcpServers": _SERVERS}))
    return MCPCliClient(config_path=str(cfg), client=["mcp", "call"])


def _registry(tmp_path, monkeypatch):
    monkeypatch.delenv("MCP_EXECUTE", raising=False)
    cfg = tmp_path / "mcp-config.json"
    cfg.write_text(json.dumps({"mcpServers": _SERVERS}))
    monkeypatch.setenv("MCP_CONFIG_PATH", str(cfg))
    # Reset the module-level client so it picks up the test config.
    import src.tools.integrations.mcp_tools as mod

    mod._client = MCPCliClient(config_path=str(cfg), client=["mcp", "call"])
    registry = ToolRegistry()
    register_mcp_tools(registry)
    return registry


# -- client ----------------------------------------------------------------
def test_lists_servers_from_config(tmp_path):
    assert sorted(_client(tmp_path).servers) == ["atlassian", "github"]


def test_protocol_method_argv(tmp_path):
    argv = _client(tmp_path).build_argv("atlassian", "tools/list")
    assert argv == ["mcp", "call", "--server", "atlassian", "--method", "tools/list"]


def test_bare_tool_name_becomes_tools_call(tmp_path):
    argv = _client(tmp_path).build_argv(
        "atlassian", "jira_create_issue", {"summary": "hi"}
    )
    assert "--method" in argv and "tools/call" in argv
    assert "--tool" in argv and "jira_create_issue" in argv
    assert json.loads(argv[-1]) == {"summary": "hi"}


def test_unknown_server_raises(tmp_path):
    try:
        _client(tmp_path).build_argv("jira", "tools/list")
    except ValueError as exc:
        assert "Unknown MCP server" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_invoke_is_dry_run_by_default(tmp_path):
    out = _client(tmp_path).invoke("atlassian", "tools/list")
    assert out["dry_run"] is True and out["executed"] is False
    assert out["rendered_command"].startswith("mcp call --server atlassian")


# -- registered tools ------------------------------------------------------
def test_registered_tools(tmp_path, monkeypatch):
    registry = _registry(tmp_path, monkeypatch)
    assert {t.name for t in registry.get_by_category("mcp")} == {
        "mcp_list_servers",
        "mcp_list_tools",
        "mcp_call_tool",
        "mcp_run_command",
    }


def test_list_servers_tool(tmp_path, monkeypatch):
    registry = _registry(tmp_path, monkeypatch)
    result = json.loads(registry.execute("mcp_list_servers"))
    assert result["success"] and result["count"] == 2


def test_call_tool_dry_run(tmp_path, monkeypatch):
    registry = _registry(tmp_path, monkeypatch)
    result = json.loads(
        registry.execute(
            "mcp_call_tool",
            server="atlassian",
            tool="jira_create_issue",
            arguments={"project_key": "DSDM", "summary": "x"},
        )
    )
    assert result["dry_run"] is True
    assert "jira_create_issue" in result["rendered_command"]


def test_call_tool_requires_approval(tmp_path, monkeypatch):
    registry = _registry(tmp_path, monkeypatch)
    assert registry.get("mcp_call_tool").requires_approval is True
    assert registry.get("mcp_list_servers").requires_approval is False
