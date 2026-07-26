"""Local HTTP bridge exposing a :class:`ToolRegistry` to the pi.dev extension.

Phase 1 of the Pi Agent Runtime migration (see
``docs/category-defining-features/11-pi-agent-runtime/TRD.md`` sections 5, 6
and 13). The ``dsdm-tools-bridge`` pi.dev extension is the only intended
caller: it fetches the tool manifest once at session start and calls
``execute`` for every tool call the LLM makes, so every existing DSDM tool
handler stays in Python, unmodified.

Design notes
------------
* **Localhost only** — the service binds to ``127.0.0.1`` and refuses to
  bind anywhere else, per TRD section 13. It is not a general-purpose API;
  it exists to be reached by a pi.dev process running on the same machine.
* **No new dependencies** — built on :mod:`http.server` rather than a web
  framework, consistent with the rest of ``src/tools``.
* **Thin wrapper** — the manifest is exactly ``Tool.to_anthropic_format()``
  plus ``requires_approval``/``category``; execution delegates straight to
  ``ToolRegistry.execute()``. No tool handler logic lives here.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

_LOCALHOST = "127.0.0.1"


def build_manifest(registry: ToolRegistry) -> list[Dict[str, Any]]:
    """Describe every registered tool in the shape the bridge extension needs."""
    return [
        {
            **tool.to_anthropic_format(),
            "requires_approval": tool.requires_approval,
            "category": tool.category,
        }
        for tool in registry.get_all()
    ]


class _Handler(BaseHTTPRequestHandler):
    # Populated per-server via ThreadingHTTPServer subclass below.
    registry: ToolRegistry

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 - stdlib signature
        logger.debug("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib method name
        path = urlparse(self.path).path
        if path == "/tools":
            self._send_json(200, {"tools": build_manifest(self.registry)})
            return
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        self._send_json(404, {"error": f"Unknown path: {path}"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        path = urlparse(self.path).path
        parts = [segment for segment in path.split("/") if segment]
        if len(parts) != 3 or parts[0] != "tools" or parts[2] != "execute":
            self._send_json(404, {"error": f"Unknown path: {path}"})
            return

        tool_name = parts[1]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw_body or b"{}")
        except json.JSONDecodeError as exc:
            self._send_json(400, {"error": f"Malformed JSON body: {exc}"})
            return

        if self.registry.get(tool_name) is None:
            self._send_json(404, {"error": f"Unknown tool: {tool_name}"})
            return

        arguments = body.get("arguments") or {}
        run_context = body.get("run_context") or {}
        if not isinstance(arguments, dict):
            self._send_json(400, {"error": "'arguments' must be a JSON object"})
            return

        logger.debug(
            "executing tool=%s run_context=%s",
            tool_name,
            {k: v for k, v in run_context.items() if k != "session_id"},
        )
        result = self.registry.execute(tool_name, **arguments)
        self._send_json(200, {"result": result})


class ToolBridgeServer(ThreadingHTTPServer):
    """``ThreadingHTTPServer`` bound to a :class:`ToolRegistry`, localhost only."""

    daemon_threads = True

    def __init__(self, registry: ToolRegistry, host: str = _LOCALHOST, port: int = 0):
        if host != _LOCALHOST:
            raise ValueError(
                f"ToolBridgeServer must bind to {_LOCALHOST} only (got {host!r}); "
                "see TRD section 13 (Security and Safety)."
            )

        class _BoundHandler(_Handler):
            pass

        _BoundHandler.registry = registry
        super().__init__((host, port), _BoundHandler)
        self.registry = registry

    @property
    def base_url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://{host}:{port}"


def run_tool_service_in_background(
    registry: ToolRegistry, host: str = _LOCALHOST, port: int = 0
) -> ToolBridgeServer:
    """Start the bridge server on a background thread and return it (already serving)."""
    server = ToolBridgeServer(registry, host=host, port=port)
    thread = threading.Thread(target=server.serve_forever, name="dsdm-tool-bridge", daemon=True)
    thread.start()
    return server


def _build_registry_from_env() -> ToolRegistry:
    from .dsdm_tools import create_dsdm_tool_registry

    def _flag(name: str, default: bool) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    return create_dsdm_tool_registry(
        include_confluence=_flag("DSDM_BRIDGE_INCLUDE_CONFLUENCE", False),
        include_jira=_flag("DSDM_BRIDGE_INCLUDE_JIRA", False),
        include_devops=_flag("DSDM_BRIDGE_INCLUDE_DEVOPS", False),
        include_mcp=_flag("DSDM_BRIDGE_INCLUDE_MCP", True),
    )


def main() -> None:
    """Run the bridge in the foreground; prints the bound port for callers to capture."""
    logging.basicConfig(level=os.environ.get("DSDM_BRIDGE_LOG_LEVEL", "INFO"))
    port = int(os.environ.get("DSDM_BRIDGE_PORT", "0"))
    registry = _build_registry_from_env()
    server = ToolBridgeServer(registry, port=port)
    print(f"DSDM_TOOL_BRIDGE_PORT={server.server_address[1]}", flush=True)
    print(f"DSDM_TOOL_BRIDGE_URL={server.base_url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
