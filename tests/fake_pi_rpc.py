#!/usr/bin/env python3
"""Fake `pi --mode rpc` process for testing pi_session_runner.py.

Speaks just enough of the real RPC protocol (JSONL over stdin/stdout,
newline-framed) to exercise run_role()'s event handling end-to-end,
including a real confirm request/response round-trip, without needing the
actual pi.dev binary or LLM credentials. Behavior selected via the
FAKE_PI_SCENARIO env var.
"""

import json
import os
import sys


def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def read_line():
    line = sys.stdin.readline()
    return json.loads(line) if line else None


def main():
    scenario = os.environ.get("FAKE_PI_SCENARIO", "happy_path")

    prompt_cmd = read_line()
    assert prompt_cmd is not None and prompt_cmd.get("type") == "prompt"

    if scenario == "extension_load_error":
        emit({"type": "response", "command": "prompt", "success": False, "error": "extension failed to load"})
        return

    emit({"type": "tool_execution_start", "toolCallId": "call_1", "toolName": "analyze_requirements", "args": {"requirements_text": "x"}})

    if scenario in ("confirm_approve", "confirm_deny"):
        emit({
            "type": "extension_ui_request",
            "id": "req-1",
            "method": "confirm",
            "title": "DSDM approval required",
            "message": "Allow 'file_write' to run?",
        })
        response = read_line()
        assert response is not None and response.get("type") == "extension_ui_response" and response.get("id") == "req-1"
        confirmed = response.get("confirmed", False)
        if scenario == "confirm_approve":
            assert confirmed is True
        else:
            assert confirmed is False

    if scenario == "extension_error_mid_run":
        emit({"type": "extension_error", "error": "dsdm-approval-gate crashed"})

    emit({
        "type": "tool_execution_end",
        "toolCallId": "call_1",
        "toolName": "analyze_requirements",
        "result": {"content": [{"type": "text", "text": '{"success": true, "requirements": []}'}]},
        "isError": False,
    })

    emit({
        "type": "agent_end",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "do the thing"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "Analysis complete."}]},
        ],
    })


if __name__ == "__main__":
    main()
