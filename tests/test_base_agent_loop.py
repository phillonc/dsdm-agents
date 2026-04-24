"""Tests for the BaseAgent run loop (stop_reason handling, approval, stuck detection)."""

import json

import pytest

from src.agents.base_agent import (
    AgentConfig,
    AgentMode,
    AgentResult,
    BaseAgent,
    ProgressEvent,
)
from src.agents.workflow_modes import WorkflowMode
from src.tools.tool_registry import Tool, ToolRegistry


class _Agent(BaseAgent):
    """Minimal concrete agent for testing the loop."""

    def _process_output(self, output: str) -> AgentResult:
        return AgentResult(success=True, output=output)


class _StubLLM:
    """Deterministic LLM stub that replays a canned sequence of responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def chat(self, **_kwargs):
        self.calls += 1
        if not self._responses:
            raise AssertionError("LLM called more times than expected")
        return self._responses.pop(0)


def _config(phase="feasibility", workflow_mode=WorkflowMode.AGENT_WRITES_CODE, **overrides):
    base = dict(
        name="test",
        description="desc",
        phase=phase,
        system_prompt="sp",
        tools=[],
        mode=AgentMode.AUTOMATED,
        workflow_mode=workflow_mode,
        max_iterations=5,
    )
    base.update(overrides)
    return AgentConfig(**base)


def _make_agent(responses, tools=None, **config_overrides):
    registry = ToolRegistry()
    for tool in tools or []:
        registry.register(tool)
    return _Agent(
        config=_config(tools=[t.name for t in (tools or [])], **config_overrides),
        tool_registry=registry,
        llm_client=_StubLLM(responses),
    )


def test_end_turn_returns_content():
    agent = _make_agent([
        {"content": "done", "stop_reason": "end_turn", "tool_calls": []},
    ])
    result = agent.run("do it")
    assert result.success is True
    assert result.output == "done"


def test_empty_stop_reason_then_end_turn():
    agent = _make_agent([
        {"content": "thinking", "stop_reason": "", "tool_calls": []},
    ])
    result = agent.run("go")
    # Content-with-no-stop_reason is treated as complete.
    assert result.output == "thinking"


def test_stuck_on_repeated_empty_responses_short_circuits():
    # 3 empty+no-stop-reason responses should trip stuck detection
    # instead of running until max_iterations.
    agent = _make_agent(
        [
            {"content": "", "stop_reason": "", "tool_calls": []},
            {"content": "", "stop_reason": "", "tool_calls": []},
            {"content": "", "stop_reason": "", "tool_calls": []},
        ],
        max_iterations=50,
    )
    result = agent.run("go")
    assert result.success is False
    assert "no content" in result.output.lower()
    # Critically: we stopped well before max_iterations.
    assert agent.llm_client.calls == 3


def test_tool_call_executes_and_feeds_back():
    calls = []

    def _handler(**kwargs):
        calls.append(kwargs)
        return "tool-ok"

    tool = Tool(
        name="mytool",
        description="d",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
        handler=_handler,
    )
    agent = _make_agent(
        [
            {
                "content": "",
                "stop_reason": "tool_use",
                "tool_calls": [{"id": "c1", "name": "mytool", "input": {"x": "hi"}}],
            },
            {"content": "done", "stop_reason": "end_turn", "tool_calls": []},
        ],
        tools=[tool],
    )
    result = agent.run("use tool")
    assert result.success is True
    assert calls == [{"x": "hi"}]
    assert any(entry["tool"] == "mytool" for entry in agent.tool_call_history)


def test_manual_mode_denies_tool_without_callback():
    def _handler(**_kw):
        return "should not run"

    tool = Tool(
        name="mytool",
        description="d",
        input_schema={"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]},
        handler=_handler,
    )
    agent = _make_agent(
        [
            {
                "content": "",
                "stop_reason": "tool_use",
                "tool_calls": [{"id": "c1", "name": "mytool", "input": {"x": "hi"}}],
            },
            {"content": "done-without-tool", "stop_reason": "end_turn", "tool_calls": []},
        ],
        tools=[tool],
        mode=AgentMode.MANUAL,
    )
    result = agent.run("use tool")
    assert result.success is True
    # Denial is surfaced as a tool_result; the handler was never called.
    denial = [h for h in agent.tool_call_history]
    assert denial == []  # handler wasn't invoked, so history stays empty


def test_max_iterations_default_sentinel_resolves_to_phase_default():
    # Passing max_iterations=None should pull the phase default (feasibility=8).
    registry = ToolRegistry()
    agent = _Agent(
        config=AgentConfig(
            name="a",
            description="d",
            phase="feasibility",
            system_prompt="sp",
            max_iterations=None,
        ),
        tool_registry=registry,
        llm_client=_StubLLM([]),
    )
    assert agent.config.max_iterations == 8


def test_blocked_response_returns_failure_with_partial_content():
    agent = _make_agent([
        {
            "content": "partial",
            "stop_reason": "blocked",
            "tool_calls": [],
            "error": "safety",
        },
    ])
    result = agent.run("go")
    assert result.success is False
    assert "partial" in result.output
