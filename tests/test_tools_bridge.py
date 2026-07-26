"""Tests for the pi.dev tools bridge (src/tools/tool_service.py)."""

import json

import pytest
import requests

from src.tools.tool_registry import Tool, ToolRegistry
from src.tools.tool_service import ToolBridgeServer, build_manifest, run_tool_service_in_background


def _echo(text: str) -> str:
    return json.dumps({"success": True, "echo": text})


def _boom() -> str:
    raise RuntimeError("handler blew up")


def _fixture_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool(
        name="echo_tool",
        description="Echoes back the given text.",
        input_schema={
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to echo"}},
            "required": ["text"],
        },
        handler=_echo,
        category="feasibility",
    ))
    registry.register(Tool(
        name="approval_tool",
        description="A tool that requires manual approval.",
        input_schema={"type": "object", "properties": {}},
        handler=lambda: json.dumps({"success": True}),
        requires_approval=True,
        category="implementation",
    ))
    registry.register(Tool(
        name="broken_tool",
        description="A tool whose handler always raises.",
        input_schema={"type": "object", "properties": {}},
        handler=_boom,
        category="feasibility",
    ))
    return registry


@pytest.fixture(scope="module")
def bridge():
    registry = _fixture_registry()
    server = run_tool_service_in_background(registry)
    yield server
    server.shutdown()


def _url(bridge, path: str) -> str:
    return f"{bridge.base_url}{path}"


# -- binding -----------------------------------------------------------------
def test_refuses_to_bind_off_localhost():
    with pytest.raises(ValueError):
        ToolBridgeServer(_fixture_registry(), host="0.0.0.0")


def test_binds_to_ephemeral_localhost_port(bridge):
    host, port = bridge.server_address[:2]
    assert host == "127.0.0.1"
    assert port > 0
    assert bridge.base_url == f"http://127.0.0.1:{port}"


# -- manifest ------------------------------------------------------------------
def test_build_manifest_matches_registry_shape():
    registry = _fixture_registry()
    manifest = build_manifest(registry)
    by_name = {entry["name"]: entry for entry in manifest}

    assert set(by_name) == {"echo_tool", "approval_tool", "broken_tool"}
    assert by_name["echo_tool"]["input_schema"] == registry.get("echo_tool").input_schema
    assert by_name["echo_tool"]["requires_approval"] is False
    assert by_name["echo_tool"]["category"] == "feasibility"
    assert by_name["approval_tool"]["requires_approval"] is True


def test_get_tools_endpoint(bridge):
    resp = requests.get(_url(bridge, "/tools"), timeout=5)
    assert resp.status_code == 200
    tools = {t["name"] for t in resp.json()["tools"]}
    assert tools == {"echo_tool", "approval_tool", "broken_tool"}


def test_health_endpoint(bridge):
    resp = requests.get(_url(bridge, "/health"), timeout=5)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unknown_get_path_is_404(bridge):
    resp = requests.get(_url(bridge, "/nope"), timeout=5)
    assert resp.status_code == 404


# -- execute -------------------------------------------------------------------
def test_execute_success(bridge):
    resp = requests.post(
        _url(bridge, "/tools/echo_tool/execute"),
        json={"arguments": {"text": "hello"}, "run_context": {"phase": "feasibility"}},
        timeout=5,
    )
    assert resp.status_code == 200
    result = json.loads(resp.json()["result"])
    assert result == {"success": True, "echo": "hello"}


def test_execute_missing_required_argument_surfaces_registry_error(bridge):
    resp = requests.post(_url(bridge, "/tools/echo_tool/execute"), json={"arguments": {}}, timeout=5)
    assert resp.status_code == 200  # bridge itself succeeded; the tool reported the error
    result = json.loads(resp.json()["result"])
    assert result["success"] is False
    assert "text" in result["error"]


def test_execute_handler_exception_is_caught(bridge):
    resp = requests.post(_url(bridge, "/tools/broken_tool/execute"), json={"arguments": {}}, timeout=5)
    assert resp.status_code == 200
    assert "handler blew up" in resp.json()["result"]


def test_execute_unknown_tool_is_404(bridge):
    resp = requests.post(_url(bridge, "/tools/does_not_exist/execute"), json={"arguments": {}}, timeout=5)
    assert resp.status_code == 404


def test_execute_malformed_json_is_400(bridge):
    resp = requests.post(
        _url(bridge, "/tools/echo_tool/execute"),
        data=b"{not json",
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    assert resp.status_code == 400


def test_execute_non_object_arguments_is_400(bridge):
    resp = requests.post(
        _url(bridge, "/tools/echo_tool/execute"),
        json={"arguments": ["not", "a", "dict"]},
        timeout=5,
    )
    assert resp.status_code == 400


def test_execute_no_body_defaults_to_empty_arguments(bridge):
    resp = requests.post(_url(bridge, "/tools/approval_tool/execute"), timeout=5)
    assert resp.status_code == 200
    assert json.loads(resp.json()["result"]) == {"success": True}
