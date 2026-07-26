"""Tests for src/orchestrator/pi_session_runner.py.

Runs run_role() against a fake `pi --mode rpc` process (tests/fake_pi_rpc.py)
that speaks just enough of the real RPC protocol to exercise the full event
loop, including a real confirm request/response round-trip — no pi.dev
binary or LLM credentials required. JSONL framing itself
(_JsonlReader/_extract_text/_extract_last_assistant_text/_resolve_provider)
is unit tested directly.
"""

import json
import os
from pathlib import Path

import pytest

import src.orchestrator.pi_session_runner as runner
from src.agents.base_agent import AgentMode, ProgressEvent
from src.agents.role_definitions import get_role

FAKE_PI = Path(__file__).resolve().parent / "fake_pi_rpc.py"


@pytest.fixture(autouse=True)
def _fake_pi_binary(monkeypatch):
    monkeypatch.setattr(runner, "PI_BIN", FAKE_PI)


@pytest.fixture
def role():
    return get_role("feasibility")


def _run(role, scenario, **kwargs):
    old = os.environ.get("FAKE_PI_SCENARIO")
    os.environ["FAKE_PI_SCENARIO"] = scenario
    try:
        return runner.run_role(role, "Build a widget", bridge_url="http://127.0.0.1:9999", **kwargs)
    finally:
        if old is None:
            os.environ.pop("FAKE_PI_SCENARIO", None)
        else:
            os.environ["FAKE_PI_SCENARIO"] = old


def test_pi_binary_missing_raises_clear_error(monkeypatch, role):
    monkeypatch.setattr(runner, "PI_BIN", Path("/nonexistent/pi"))
    with pytest.raises(runner.PiCliNotFoundError, match="npm install"):
        runner.run_role(role, "hi", bridge_url="http://127.0.0.1:9999")


def test_happy_path_maps_to_successful_result(role):
    result = _run(role, "happy_path")
    assert result.success is True
    assert result.output == "Analysis complete."
    assert result.error is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["tool"] == "analyze_requirements"
    assert result.tool_calls[0]["is_error"] is False
    assert "requirements" in result.tool_calls[0]["result"]


def test_happy_path_maps_to_agent_result(role):
    result = _run(role, "happy_path")
    agent_result = result.to_agent_result()
    assert agent_result.success is True
    assert agent_result.output == "Analysis complete."
    assert agent_result.tool_calls == result.tool_calls


def test_extension_load_error_surfaces_as_failure(role):
    result = _run(role, "extension_load_error")
    assert result.success is False
    assert "extension failed to load" in result.error


def test_confirm_approve_round_trip(role):
    approvals = []

    def approval_callback(title, payload):
        approvals.append((title, payload))
        return True

    result = _run(role, "confirm_approve", approval_callback=approval_callback)
    assert result.success is True
    assert approvals == [("DSDM approval required", {"message": "Allow 'file_write' to run?"})]


def test_confirm_deny_round_trip(role):
    result = _run(role, "confirm_deny", approval_callback=lambda title, payload: False)
    # The fake process still completes normally after a denial (mirrors a real
    # session continuing after a blocked tool call) — denial correctness is the
    # approval-gate extension's job (see pi/extensions/dsdm-approval-gate/index.test.ts).
    assert result.success is True


def test_no_approval_callback_defaults_to_denied():
    role = get_role("feasibility")
    result = _run(role, "confirm_deny")  # asserts confirmed=False inside the fake process
    assert result.success is True


def test_extension_error_event_surfaces_as_failure(role):
    result = _run(role, "extension_error_mid_run")
    assert result.success is False
    assert "dsdm-approval-gate crashed" in result.error


def test_progress_callback_receives_tool_and_lifecycle_events(role):
    events = []
    _run(role, "happy_path", progress_callback=events.append)

    event_types = [e.event for e in events]
    assert ProgressEvent.STARTED in event_types
    assert ProgressEvent.TOOL_CALLING in event_types
    assert ProgressEvent.TOOL_COMPLETED in event_types
    assert ProgressEvent.COMPLETED in event_types

    tool_calling = next(e for e in events if e.event == ProgressEvent.TOOL_CALLING)
    assert tool_calling.tool_name == "analyze_requirements"


def test_mode_env_var_reflects_effective_mode(monkeypatch, role):
    captured_env = {}
    real_popen = runner.subprocess.Popen

    def spy_popen(cmd, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", spy_popen)
    _run(role, "happy_path", mode=AgentMode.HYBRID)
    assert captured_env["DSDM_AGENT_MODE"] == "hybrid"
    assert captured_env["DSDM_PHASE"] == "feasibility"
    assert captured_env["DSDM_ROLE_ID"] == "feasibility"


def test_default_mode_falls_back_to_role_default(monkeypatch, role):
    captured_env = {}
    real_popen = runner.subprocess.Popen

    def spy_popen(cmd, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", spy_popen)
    _run(role, "happy_path")  # no mode= override
    assert captured_env["DSDM_AGENT_MODE"] == role.default_mode.value


# -- pure helpers ---------------------------------------------------------------
def test_extract_text_joins_text_blocks():
    content = [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]
    assert runner._extract_text(content) == "ab"


def test_extract_text_handles_none_and_non_list():
    assert runner._extract_text(None) == ""
    assert runner._extract_text("raw") == "raw"


def test_extract_last_assistant_text_picks_the_last_one():
    messages = [
        {"role": "assistant", "content": [{"type": "text", "text": "first"}]},
        {"role": "user", "content": [{"type": "text", "text": "ignored"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "second"}]},
    ]
    assert runner._extract_last_assistant_text(messages) == "second"


def test_resolve_provider_maps_gemini_to_google(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert runner._resolve_provider(None) == "google"


def test_resolve_provider_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert runner._resolve_provider("anthropic") == "anthropic"


def test_resolve_provider_unknown_env_returns_none(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-real-provider")
    assert runner._resolve_provider(None) is None


def test_jsonl_reader_frames_on_newline_only():
    import io

    buf = io.BytesIO(b'{"a":1}\n{"b":2}\r\n')
    assert list(runner._JsonlReader(buf)) == [{"a": 1}, {"b": 2}]
