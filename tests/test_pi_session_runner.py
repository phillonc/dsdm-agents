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


def test_resolve_provider_unrecognized_value_passes_through_raw(monkeypatch):
    # Not in _PROVIDER_TO_PI -> assumed to be a raw pi.dev provider name the
    # caller wants passed straight through (PAR-PRD-FR-004: "any provider
    # pi-ai supports"), not silently dropped to None.
    monkeypatch.setenv("LLM_PROVIDER", "some-raw-pi-provider")
    assert runner._resolve_provider(None) == "some-raw-pi-provider"


def test_resolve_provider_no_value_anywhere_returns_none(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert runner._resolve_provider(None) is None


def test_resolve_provider_explicit_vllm_maps_to_dsdm_vllm(monkeypatch):
    # Regression test: an earlier version returned an explicit `provider=`
    # argument unmapped, so "vllm"/"gemini" passed explicitly silently skipped
    # the DSDM -> pi.dev name translation the env-var path applied correctly.
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert runner._resolve_provider("vllm") == runner.VLLM_PROVIDER_NAME
    assert runner._resolve_provider("gemini") == "google"


def test_jsonl_reader_frames_on_newline_only():
    import io

    buf = io.BytesIO(b'{"a":1}\n{"b":2}\r\n')
    assert list(runner._JsonlReader(buf)) == [{"a": 1}, {"b": 2}]


# -- private vLLM provider (TRD section 22) --------------------------------------
def test_write_vllm_models_config_requires_base_url(tmp_path, monkeypatch):
    monkeypatch.delenv("DSDM_VLLM_BASE_URL", raising=False)
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "meta-llama/Llama-3.1-70B-Instruct")
    with pytest.raises(runner.VllmConfigurationError, match="DSDM_VLLM_BASE_URL"):
        runner._write_vllm_models_config(tmp_path)


def test_write_vllm_models_config_requires_model_id(tmp_path, monkeypatch):
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.delenv("DSDM_VLLM_MODEL_ID", raising=False)
    with pytest.raises(runner.VllmConfigurationError, match="DSDM_VLLM_MODEL_ID"):
        runner._write_vllm_models_config(tmp_path)


def test_write_vllm_models_config_matches_documented_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "meta-llama/Llama-3.1-70B-Instruct")
    monkeypatch.delenv("DSDM_VLLM_API_KEY", raising=False)

    runner._write_vllm_models_config(tmp_path)
    config = json.loads((tmp_path / "models.json").read_text())

    provider = config["providers"][runner.VLLM_PROVIDER_NAME]
    assert provider["baseUrl"] == "http://vllm.internal.example:8000/v1"
    assert provider["api"] == "openai-completions"
    assert provider["apiKey"]  # some non-empty placeholder when unset
    assert provider["compat"] == {"supportsDeveloperRole": False}
    assert provider["models"] == [{"id": "meta-llama/Llama-3.1-70B-Instruct"}]


def test_write_vllm_models_config_uses_real_api_key_when_set(tmp_path, monkeypatch):
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "qwen2.5-coder:32b")
    monkeypatch.setenv("DSDM_VLLM_API_KEY", "internal-proxy-token")

    runner._write_vllm_models_config(tmp_path)
    config = json.loads((tmp_path / "models.json").read_text())
    assert config["providers"][runner.VLLM_PROVIDER_NAME]["apiKey"] == "internal-proxy-token"


def test_write_vllm_models_config_model_id_param_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "env-default-model")

    runner._write_vllm_models_config(tmp_path, model_id="explicit-override-model")
    config = json.loads((tmp_path / "models.json").read_text())
    assert config["providers"][runner.VLLM_PROVIDER_NAME]["models"] == [{"id": "explicit-override-model"}]


def test_run_role_with_vllm_provider_missing_config_raises(role, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "vllm")
    monkeypatch.delenv("DSDM_VLLM_BASE_URL", raising=False)
    with pytest.raises(runner.VllmConfigurationError):
        _run(role, "happy_path")


def test_run_role_with_vllm_provider_wires_config_dir_and_cleans_up(role, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "vllm")
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "meta-llama/Llama-3.1-70B-Instruct")

    captured_env = {}
    real_popen = runner.subprocess.Popen

    def spy_popen(cmd, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", spy_popen)
    result = _run(role, "happy_path")

    assert result.success is True
    config_dir = captured_env.get("PI_CODING_AGENT_DIR")
    assert config_dir, "PI_CODING_AGENT_DIR should be set for the vllm provider"
    assert "--provider" in runner._build_command(role, "dsdm-vllm", None, None)
    # the temp config directory is cleaned up once the subprocess call completes
    assert not Path(config_dir).exists()


def test_run_role_with_vllm_provider_generates_correct_models_json(role, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "vllm")
    monkeypatch.setenv("DSDM_VLLM_BASE_URL", "http://vllm.internal.example:8000/v1")
    monkeypatch.setenv("DSDM_VLLM_MODEL_ID", "meta-llama/Llama-3.1-70B-Instruct")

    seen_config = {}
    real_popen = runner.subprocess.Popen

    def spy_popen(cmd, **kwargs):
        config_dir = (kwargs.get("env") or {}).get("PI_CODING_AGENT_DIR")
        if config_dir:
            seen_config.update(json.loads((Path(config_dir) / "models.json").read_text()))
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", spy_popen)
    _run(role, "happy_path")

    provider = seen_config["providers"][runner.VLLM_PROVIDER_NAME]
    assert provider["baseUrl"] == "http://vllm.internal.example:8000/v1"
    assert provider["models"] == [{"id": "meta-llama/Llama-3.1-70B-Instruct"}]


def test_run_role_without_vllm_provider_does_not_set_config_dir(role, monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    captured_env = {}
    real_popen = runner.subprocess.Popen

    def spy_popen(cmd, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        return real_popen(cmd, **kwargs)

    monkeypatch.setattr(runner.subprocess, "Popen", spy_popen)
    _run(role, "happy_path")
    assert "PI_CODING_AGENT_DIR" not in captured_env
