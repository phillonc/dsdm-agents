"""Tests for src.tools.tool_registry.Tool and ToolRegistry."""

import json

import pytest

from src.tools.tool_registry import Tool, ToolRegistry


def _schema(required=None, **props):
    return {
        "type": "object",
        "properties": props,
        "required": required or [],
    }


def _ok_handler(**kwargs):
    return json.dumps({"success": True, "received": sorted(kwargs)})


def test_execute_filters_unexpected_params():
    tool = Tool(
        name="t",
        description="d",
        input_schema=_schema(file_path={"type": "string"}),
        handler=_ok_handler,
    )
    out = json.loads(tool.execute(file_path="a", output_dir="/tmp", bogus="x"))
    # Only file_path should reach the handler.
    assert out == {"success": True, "received": ["file_path"]}


def test_execute_applies_parameter_aliases():
    tool = Tool(
        name="t",
        description="d",
        input_schema=_schema(file_path={"type": "string"}),
        handler=_ok_handler,
    )
    # "path" is an alias for "file_path"
    out = json.loads(tool.execute(path="note.txt"))
    assert out == {"success": True, "received": ["file_path"]}


def test_execute_alias_does_not_overwrite_canonical():
    tool = Tool(
        name="t",
        description="d",
        input_schema=_schema(
            required=["file_path"],
            file_path={"type": "string"},
        ),
        handler=_ok_handler,
    )
    out = json.loads(tool.execute(file_path="a.txt", path="b.txt"))
    assert out["received"] == ["file_path"]


def test_execute_reports_missing_required():
    tool = Tool(
        name="t",
        description="d",
        input_schema=_schema(
            required=["file_path"],
            file_path={"type": "string"},
        ),
        handler=_ok_handler,
    )
    out = json.loads(tool.execute(unrelated="x"))
    assert out["success"] is False
    assert "file_path" in out["error"]


def test_execute_wraps_handler_errors():
    def _boom(**_kw):
        raise RuntimeError("kaboom")

    tool = Tool(
        name="t",
        description="d",
        input_schema=_schema(file_path={"type": "string"}),
        handler=_boom,
    )
    out = tool.execute(file_path="a")
    assert "kaboom" in out


def test_registry_register_and_get():
    registry = ToolRegistry()
    tool = Tool("t", "d", _schema(), _ok_handler, category="cat")
    registry.register(tool)
    assert registry.get("t") is tool
    assert registry.get("nope") is None
    assert registry.get_by_category("cat") == [tool]


def test_registry_execute_unknown_tool():
    registry = ToolRegistry()
    assert "Unknown tool" in registry.execute("missing")


def test_to_anthropic_format_shape():
    tool = Tool("t", "describe", _schema(x={"type": "string"}), _ok_handler)
    fmt = tool.to_anthropic_format()
    assert fmt == {
        "name": "t",
        "description": "describe",
        "input_schema": {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": [],
        },
    }
