"""Runs a DSDM role through pi.dev instead of BaseAgent.run().

Phase 3 of the Pi Agent Runtime migration
(docs/category-defining-features/11-pi-agent-runtime/TRD.md section 8,
PAR-PRD-FR-003). Spawns `pi --mode rpc` with the `dsdm-tools-bridge` and
`dsdm-approval-gate` extensions loaded, drives the RPC protocol (JSONL over
stdin/stdout, framed on ``\\n`` only per pi's own docs), and maps the result
back to an `AgentResult`-compatible shape so `DSDMOrchestrator` can use this
as a drop-in alternative to `agent.run()`.

Why RPC mode, not JSON mode: JSON mode (`--mode json`) is one-shot and
leaves `ctx.hasUI` false for the whole run, so `dsdm-approval-gate` would
always fail closed — there would be no way to actually grant an approval
headlessly. RPC mode makes `ctx.hasUI` true (pi's own docs confirm this
explicitly) via the "extension UI protocol": `ctx.ui.confirm()` calls
surface as an `extension_ui_request` on stdout that this runner answers
with an `extension_ui_response` on stdin, using the same
``approval_callback`` shape `BaseAgent`/`DSDMOrchestrator` already use for
Rich's `Confirm.ask` today.

There is no `dsdm-room-events` extension. RPC mode already streams
`tool_execution_start`/`tool_execution_end`/`agent_end` as JSON lines on
stdout; this runner forwards those directly into the same
`ProgressCallback` shape `BaseAgent` produces, so `src/rooms/room_progress.py`
needs no changes to keep working.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

from ..agents.base_agent import AgentMode, AgentResult, ProgressCallback, ProgressEvent, ProgressInfo
from ..agents.role_definitions import RoleDefinition

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PI_DIR = REPO_ROOT / "pi"
PI_BIN = PI_DIR / "node_modules" / ".bin" / "pi"
TOOLS_BRIDGE_EXTENSION = PI_DIR / "extensions" / "dsdm-tools-bridge"
APPROVAL_GATE_EXTENSION = PI_DIR / "extensions" / "dsdm-approval-gate"

# DSDM's LLM_PROVIDER values -> pi.dev's --provider names. pi.dev calls Google's
# provider "google", not "gemini" — a real naming mismatch, not a typo.
_PROVIDER_TO_PI = {
    "anthropic": "anthropic",
    "openai": "openai",
    "gemini": "google",
    "ollama": "ollama",
}

DEFAULT_TIMEOUT_SECONDS = 600


class PiCliNotFoundError(RuntimeError):
    """Raised when the pi.dev CLI isn't installed at pi/node_modules/.bin/pi."""


@dataclass
class PiSessionResult:
    """AgentResult-compatible result of running one role through pi.dev."""

    success: bool
    output: str
    session_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    requires_next_phase: bool = False
    next_phase_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_agent_result(self) -> AgentResult:
        artifacts: Dict[str, Any] = {}
        if self.session_id:
            artifacts["pi_session_id"] = self.session_id
        if self.error:
            artifacts["error"] = self.error
        return AgentResult(
            success=self.success,
            output=self.output,
            artifacts=artifacts,
            tool_calls=self.tool_calls,
            requires_next_phase=self.requires_next_phase,
            next_phase_input=self.next_phase_input,
        )


class _JsonlReader:
    """Reads newline-delimited JSON from a binary stream, framed on b"\\n" only.

    pi's own RPC docs warn against generic line readers (e.g. Node's
    readline) that also split on Unicode line separators valid inside JSON
    strings. This reads raw bytes and only ever splits on a literal b"\\n",
    stripping one trailing b"\\r" if present — the same framing the docs'
    own reference clients use.
    """

    def __init__(self, stream):
        self._stream = stream
        self._buffer = b""

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return self

    def __next__(self) -> Dict[str, Any]:
        while b"\n" not in self._buffer:
            # read1(), not read(): BufferedReader.read(n) loops the underlying raw
            # read until it accumulates n bytes or hits EOF — it does NOT return
            # early just because a partial chunk is all that's available right
            # now. That's fatal here: pi pauses mid-stream waiting for an
            # extension_ui_response (it doesn't exit), so a plain read(4096) blocks
            # forever after the first short chunk instead of returning what already
            # arrived. read1() makes at most one underlying read call and returns
            # whatever's available, matching the streaming semantics this protocol
            # actually needs (and what the Node.js reference client's chunk-based
            # stream.on("data", ...) naturally does).
            chunk = self._stream.read1(4096)
            if not chunk:
                if self._buffer.strip():
                    line, self._buffer = self._buffer, b""
                    return self._decode(line)
                raise StopIteration
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        return self._decode(line)

    @staticmethod
    def _decode(line: bytes) -> Dict[str, Any]:
        if line.endswith(b"\r"):
            line = line[:-1]
        return json.loads(line.decode("utf-8"))


def _extract_text(content: Any) -> str:
    """Joins the text blocks of a pi content array: [{"type": "text", "text": "..."}]."""
    if not isinstance(content, list):
        return "" if content is None else str(content)
    return "".join(block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text")


def _extract_last_assistant_text(messages: List[Dict[str, Any]]) -> str:
    for message in reversed(messages or []):
        if message.get("role") == "assistant":
            return _extract_text(message.get("content"))
    return ""


def _resolve_provider(explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    env_provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    return _PROVIDER_TO_PI.get(env_provider)


def _build_command(
    role: RoleDefinition,
    mode: AgentMode,
    provider: Optional[str],
    model: Optional[str],
    session_dir: Optional[Path],
) -> List[str]:
    cmd = [
        str(PI_BIN),
        "--no-context-files",
        "--no-extensions",
        "-e",
        str(TOOLS_BRIDGE_EXTENSION),
        "-e",
        str(APPROVAL_GATE_EXTENSION),
        "--tools",
        ",".join(role.tools),
        "--system-prompt",
        role.system_prompt,
        "--mode",
        "rpc",
    ]
    resolved_provider = _resolve_provider(provider)
    resolved_model = model or role.model
    if resolved_provider:
        cmd += ["--provider", resolved_provider]
    if resolved_model:
        cmd += ["--model", resolved_model]
    if session_dir:
        cmd += ["--session-dir", str(session_dir)]
    return cmd


def run_role(
    role: RoleDefinition,
    user_input: str,
    *,
    bridge_url: str,
    mode: Optional[AgentMode] = None,
    approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    session_dir: Optional[Path] = None,
    project: Optional[str] = None,
    context: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> PiSessionResult:
    """Run `role` on pi.dev with `user_input`, mirroring BaseAgent.run()'s contract.

    `bridge_url` must point at an already-running `tool_service.py` instance
    (see `src/tools/tool_service.py`) — this function does not start one, so
    that a caller running a multi-phase workflow can share a single bridge
    across roles rather than paying subprocess startup cost per phase.
    """
    if not PI_BIN.exists():
        raise PiCliNotFoundError(
            f"pi binary not found at {PI_BIN}. Run 'npm install' in {PI_DIR} first "
            "(see docs/category-defining-features/11-pi-agent-runtime/TRD.md section 3)."
        )

    effective_mode = mode if mode is not None else role.default_mode
    env = {
        **os.environ,
        "DSDM_BRIDGE_URL": bridge_url,
        "DSDM_PHASE": role.phase,
        "DSDM_ROLE_ID": role.role_id,
        "DSDM_AGENT_MODE": effective_mode.value,
        "PI_OFFLINE": "1",
        "PI_SKIP_VERSION_CHECK": "1",
    }
    if project:
        env["DSDM_PROJECT"] = project

    cmd = _build_command(role, effective_mode, provider, model, session_dir)
    prompt = f"Context: {context}\n\n{user_input}" if context else user_input

    if progress_callback:
        progress_callback(ProgressInfo(event=ProgressEvent.STARTED, message=f"Starting pi.dev session for {role.role_id}", agent_name=role.display_name))

    process = subprocess.Popen(cmd, cwd=PI_DIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    watchdog = threading.Timer(timeout, process.kill)
    watchdog.daemon = True
    watchdog.start()

    session_id: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []
    final_text = ""
    error: Optional[str] = None
    saw_agent_end = False

    try:
        process.stdin.write((json.dumps({"type": "prompt", "message": prompt}) + "\n").encode("utf-8"))
        process.stdin.flush()

        for event in _JsonlReader(process.stdout):
            etype = event.get("type")

            if etype == "session":
                session_id = event.get("id")

            elif etype == "response" and event.get("command") == "prompt" and event.get("success") is False:
                error = event.get("error", "pi rejected the prompt command")
                break

            elif etype == "tool_execution_start":
                tool_name = event.get("toolName")
                if progress_callback:
                    progress_callback(ProgressInfo(
                        event=ProgressEvent.TOOL_CALLING,
                        message=f"Calling {tool_name}",
                        agent_name=role.display_name,
                        tool_name=tool_name,
                        tool_input=event.get("args"),
                    ))

            elif etype == "tool_execution_end":
                tool_name = event.get("toolName")
                result_text = _extract_text((event.get("result") or {}).get("content"))
                is_error = bool(event.get("isError"))
                tool_calls.append({
                    "tool": tool_name,
                    "input": event.get("args"),
                    "result": result_text,
                    "is_error": is_error,
                })
                if progress_callback:
                    progress_callback(ProgressInfo(
                        event=ProgressEvent.TOOL_COMPLETED,
                        message=f"{tool_name} {'failed' if is_error else 'completed'}",
                        agent_name=role.display_name,
                        tool_name=tool_name,
                        tool_result=result_text,
                        details={"is_error": is_error},
                    ))

            elif etype == "extension_ui_request" and event.get("method") == "confirm":
                approved = False
                if approval_callback:
                    approved = bool(approval_callback(event.get("title", ""), {"message": event.get("message", "")}))
                response = {"type": "extension_ui_response", "id": event["id"], "confirmed": approved}
                process.stdin.write((json.dumps(response) + "\n").encode("utf-8"))
                process.stdin.flush()

            elif etype == "extension_ui_request":
                # Fire-and-forget methods (notify/setStatus/setWidget/setTitle/set_editor_text)
                # expect no response; nothing to do here.
                pass

            elif etype == "extension_error":
                error = event.get("error") or event.get("message") or "pi.dev extension error"

            elif etype == "agent_end":
                final_text = _extract_last_assistant_text(event.get("messages", []))
                saw_agent_end = True
                break

    except (BrokenPipeError, OSError) as exc:
        error = f"pi.dev process communication failed: {exc}"
    finally:
        watchdog.cancel()
        try:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    if error is None and not saw_agent_end:
        stderr_tail = ""
        try:
            stderr_tail = process.stderr.read().decode("utf-8", errors="replace")[-2000:]
        except Exception:  # noqa: BLE001 - best-effort diagnostics
            pass
        error = "pi.dev session ended without an agent_end event" + (f": {stderr_tail}" if stderr_tail else "")

    success = error is None
    if progress_callback:
        progress_callback(ProgressInfo(
            event=ProgressEvent.COMPLETED if success else ProgressEvent.ERROR,
            message=error or "pi.dev session completed",
            agent_name=role.display_name,
        ))

    return PiSessionResult(
        success=success,
        output=final_text,
        session_id=session_id,
        tool_calls=tool_calls,
        error=error,
    )
