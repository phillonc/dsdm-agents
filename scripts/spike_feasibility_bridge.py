#!/usr/bin/env python3
"""Phase 0 spike harness — Pi Agent Runtime migration.

Compares the legacy Feasibility phase (``BaseAgent.run()`` via
``DSDMOrchestrator``) against the same phase run through pi.dev, loaded with
the ``dsdm-tools-bridge`` extension (``pi/extensions/dsdm-tools-bridge``).

See docs/category-defining-features/11-pi-agent-runtime/PRD.md section 12
("Phase 0 — Spike") and TRD.md section 12 ("Migration Path").

Usage
-----
    # No LLM calls, no cost — verifies the environment is wired correctly.
    python scripts/spike_feasibility_bridge.py --check

    # Runs the real comparison. Costs real LLM tokens on both paths.
    export ANTHROPIC_API_KEY=...
    python scripts/spike_feasibility_bridge.py --live \\
        --input "Build a customer feedback portal with NPS surveys and analytics."

The tool bridge (``src/tools/tool_service.py``) is started automatically for
the duration of the run and torn down afterwards; pass ``--bridge-url`` to
point at one you are already running instead.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PI_DIR = REPO_ROOT / "pi"
PI_BIN = PI_DIR / "node_modules" / ".bin" / "pi"
BRIDGE_EXTENSION = PI_DIR / "extensions" / "dsdm-tools-bridge"

# The tool set FeasibilityAgent.__init__ actually configures (src/agents/feasibility_agent.py)
# — kept in sync manually until PAR-PRD-FR-002 (unified role definitions) lands. Note this
# deliberately omits Jira/Confluence tools (excluded from the registry by _start_bridge()/
# check_readiness() below, matching --live's include_jira=False / include_confluence=False).
FEASIBILITY_TOOLS = [
    "analyze_requirements",
    "assess_technical_feasibility",
    "identify_risks",
    "project_init",
    "file_write",
    "directory_create",
]


def check_readiness() -> dict:
    """Static checks that don't spend any LLM tokens."""
    import os

    checks = {
        "pi_binary_installed": PI_BIN.exists(),
        "dsdm_tools_bridge_extension_present": (BRIDGE_EXTENSION / "index.ts").exists(),
        "dsdm_tools_bridge_package_json_present": (BRIDGE_EXTENSION / "package.json").exists(),
        "anthropic_api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
    try:
        from src.tools.dsdm_tools import create_dsdm_tool_registry

        registry = create_dsdm_tool_registry(include_jira=False, include_confluence=False, include_devops=False)
        checks["feasibility_tools_registered"] = all(registry.get(name) is not None for name in FEASIBILITY_TOOLS)
        checks["tool_registry_importable"] = True
    except Exception as exc:  # noqa: BLE001 - surfaced to the operator
        checks["tool_registry_importable"] = False
        checks["tool_registry_error"] = str(exc)
    return checks


def run_legacy(input_text: str):
    """Run Feasibility through the existing BaseAgent loop."""
    from src.orchestrator import DSDMOrchestrator
    from src.orchestrator.dsdm_orchestrator import DSDMPhase

    orchestrator = DSDMOrchestrator(include_devops=False, include_jira=False, include_confluence=False)
    return orchestrator.run_phase(DSDMPhase.FEASIBILITY, input_text)


def run_pi_bridged(input_text: str, bridge_url: str, model: str, provider: str, timeout: int = 300) -> str:
    """Run the same phase through pi.dev + dsdm-tools-bridge, using FeasibilityAgent's own system prompt."""
    from src.agents.feasibility_agent import FEASIBILITY_SYSTEM_PROMPT

    if not PI_BIN.exists():
        raise SystemExit(f"pi binary not found at {PI_BIN}. Run 'npm install' in {PI_DIR} first.")

    env = {
        **__import__("os").environ,
        "DSDM_BRIDGE_URL": bridge_url,
        "DSDM_PHASE": "feasibility",
        "PI_OFFLINE": "1",
        "PI_SKIP_VERSION_CHECK": "1",
    }
    cmd = [
        str(PI_BIN),
        "--no-context-files",
        "--no-extensions",
        "-e",
        str(BRIDGE_EXTENSION),
        "--tools",
        ",".join(FEASIBILITY_TOOLS),
        "--provider",
        provider,
        "--model",
        model,
        "--system-prompt",
        FEASIBILITY_SYSTEM_PROMPT,
        "--no-session",
        "-p",
        input_text,
    ]
    completed = subprocess.run(cmd, cwd=PI_DIR, capture_output=True, text=True, timeout=timeout, env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"pi exited {completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
    return completed.stdout


def _start_bridge():
    from src.tools.dsdm_tools import create_dsdm_tool_registry
    from src.tools.tool_service import run_tool_service_in_background

    registry = create_dsdm_tool_registry(include_jira=False, include_confluence=False, include_devops=False)
    server = run_tool_service_in_background(registry)
    return server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Readiness check only, no LLM calls.")
    parser.add_argument("--live", action="store_true", help="Run the real legacy-vs-pi comparison (costs tokens).")
    parser.add_argument("--input", default="Build a customer feedback portal with NPS surveys and analytics.")
    parser.add_argument("--bridge-url", default=None, help="Use an already-running tool bridge instead of starting one.")
    parser.add_argument("--provider", default="anthropic")
    parser.add_argument("--model", default="claude-haiku-4-5")
    args = parser.parse_args()

    if not args.check and not args.live:
        parser.error("Pass --check (free) or --live (spends LLM tokens).")

    if args.check:
        checks = check_readiness()
        width = max(len(k) for k in checks)
        ok = True
        for key, value in checks.items():
            status = "OK" if value is True else ("FAIL" if value is False else str(value))
            if value is False:
                ok = False
            print(f"{key.ljust(width)} : {status}")
        return 0 if ok else 1

    server = None
    bridge_url = args.bridge_url
    if bridge_url is None:
        server = _start_bridge()
        bridge_url = server.base_url
        print(f"Started tool bridge at {bridge_url}")
        time.sleep(0.2)

    try:
        print("=== Legacy (BaseAgent.run) ===")
        legacy_result = run_legacy(args.input)
        print(f"success={legacy_result.success}")
        print(legacy_result.output[:2000])

        print("\n=== pi.dev (dsdm-tools-bridge) ===")
        pi_output = run_pi_bridged(args.input, bridge_url, args.model, args.provider)
        print(pi_output[:2000])

        print("\n=== Diff summary ===")
        print(f"legacy output length : {len(legacy_result.output)} chars")
        print(f"pi.dev output length : {len(pi_output)} chars")
        print(f"legacy tool calls     : {len(legacy_result.tool_calls)}")
    finally:
        if server is not None:
            server.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
