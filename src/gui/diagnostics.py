"""Environment readiness checks shown on the console's Setup page.

This is the GUI counterpart of `python main.py --pi-doctor` plus the provider
validation `main.py::_check_llm_provider` does before a run. The CLI exits with
an error message; the console instead renders the same findings as a checklist
with the fix next to each one, because a business user cannot be expected to
read a stack trace.

Secrets are never returned - only whether a key is present.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import catalog


def _provider_config() -> Dict[str, Any]:
    provider_id = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    for provider in catalog.PROVIDERS:
        if provider["id"] == provider_id:
            return provider
    return {"id": provider_id, "name": provider_id, "key_env": None, "unknown": True}


def _check(check_id: str, label: str, status: str, detail: str, fix: str = "") -> Dict[str, Any]:
    return {"id": check_id, "label": label, "status": status, "detail": detail, "fix": fix}


def _dependency_check() -> Dict[str, Any]:
    missing: List[str] = []
    for module, package in (("anthropic", "anthropic"), ("rich", "rich"), ("dotenv", "python-dotenv")):
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if missing:
        return _check(
            "dependencies",
            "Python packages",
            "error",
            f"Missing: {', '.join(missing)}.",
            "Run: pip install -r requirements.txt",
        )
    return _check("dependencies", "Python packages", "ok", "All required packages are installed.")


def _provider_check(provider: Dict[str, Any]) -> Dict[str, Any]:
    if provider.get("unknown"):
        return _check(
            "provider",
            "AI provider",
            "error",
            f"'{provider['id']}' is not a provider this system recognises.",
            "Set LLM_PROVIDER in .env to anthropic, openai, gemini, ollama or vllm.",
        )

    key_env = provider.get("key_env")
    if key_env and not os.environ.get(key_env):
        return _check(
            "provider",
            "AI provider",
            "error",
            f"{provider['name']} is selected but {key_env} is not set.",
            f"Add {key_env}=... to your .env file, then restart the console.",
        )
    return _check("provider", "AI provider", "ok", f"{provider['name']} is configured and ready.")


def _runtime_checks(provider: Dict[str, Any], runtime: str) -> List[Dict[str, Any]]:
    """pi.dev checks, mirroring `--pi-doctor`. Only relevant when pi is selected."""
    if runtime != "pi" and provider["id"] != "vllm":
        return [_check("runtime", "Execution engine", "ok", "Using the built-in agent engine.")]

    results: List[Dict[str, Any]] = []
    if provider["id"] == "vllm" and runtime != "pi":
        results.append(
            _check(
                "runtime",
                "Execution engine",
                "error",
                "A private vLLM model was selected, but the built-in engine cannot use it.",
                "Set AGENT_RUNTIME=pi in .env, or choose a different provider.",
            )
        )
        return results

    try:
        from ..orchestrator import pi_session_runner
    except ImportError as exc:  # pragma: no cover - only when deps are missing
        return [_check("runtime", "Execution engine", "error", f"pi.dev runtime unavailable: {exc}")]

    for check_id, label, path in (
        ("pi_cli", "pi.dev command", pi_session_runner.PI_BIN),
        ("pi_tools_bridge", "DSDM tools bridge", pi_session_runner.TOOLS_BRIDGE_EXTENSION),
        ("pi_approval_gate", "Approval gate", pi_session_runner.APPROVAL_GATE_EXTENSION),
    ):
        if Path(path).exists():
            results.append(_check(check_id, label, "ok", "Installed."))
        else:
            results.append(
                _check(
                    check_id,
                    label,
                    "error",
                    f"Not found at {path}.",
                    "Install the pi.dev workspace (see docs/category-defining-features/11-pi-agent-runtime/).",
                )
            )

    if provider["id"] == "vllm":
        missing = [var for var in ("DSDM_VLLM_BASE_URL", "DSDM_VLLM_MODEL_ID") if not os.environ.get(var)]
        if missing:
            results.append(
                _check(
                    "vllm",
                    "Private model endpoint",
                    "error",
                    f"Missing: {', '.join(missing)}.",
                    "Set both values in .env to point at your private vLLM server.",
                )
            )
        else:
            results.append(_check("vllm", "Private model endpoint", "ok", "Endpoint and model id are set."))

    return results


def _workspace_check() -> Dict[str, Any]:
    root = Path("generated")
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".console-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return _check(
            "workspace",
            "Output folder",
            "error",
            f"Cannot write to {root.resolve()}: {exc}",
            "Check folder permissions, or start the console from the project root.",
        )
    return _check("workspace", "Output folder", "ok", f"Documents are saved to {root.resolve()}.")


def _integration_checks() -> List[Dict[str, Any]]:
    """Optional integrations - reported as informational, never as failures."""
    results = []
    jira = all(os.environ.get(var) for var in ("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"))
    results.append(
        _check(
            "jira",
            "Jira",
            "ok" if jira else "optional",
            "Connected - work items can be synced." if jira else "Not configured. Optional.",
            "" if jira else "Add JIRA_URL, JIRA_EMAIL and JIRA_API_TOKEN to .env to enable syncing.",
        )
    )
    confluence = all(os.environ.get(var) for var in ("CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"))
    results.append(
        _check(
            "confluence",
            "Confluence",
            "ok" if confluence else "optional",
            "Connected - documents can be published." if confluence else "Not configured. Optional.",
            "" if confluence else "Add CONFLUENCE_URL, CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN to .env.",
        )
    )
    return results


def readiness() -> Dict[str, Any]:
    """Return the full readiness report for the Setup page."""
    provider = _provider_config()
    runtime = (os.environ.get("AGENT_RUNTIME") or "legacy").strip().lower()
    if runtime not in ("legacy", "pi"):
        runtime = "legacy"

    checks: List[Dict[str, Any]] = [
        _check(
            "python",
            "Python version",
            "ok" if sys.version_info >= (3, 10) else "error",
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.",
            "" if sys.version_info >= (3, 10) else "DSDM Agents needs Python 3.10 or newer.",
        ),
        _dependency_check(),
        _provider_check(provider),
    ]
    checks.extend(_runtime_checks(provider, runtime))
    checks.append(_workspace_check())
    checks.extend(_integration_checks())

    blocking = [check for check in checks if check["status"] == "error"]
    return {
        "ready": not blocking,
        "provider": {"id": provider["id"], "name": provider["name"]},
        "runtime": runtime,
        "workingDirectory": str(Path.cwd()),
        "checks": checks,
        "blockingCount": len(blocking),
    }


def default_provider() -> str:
    return _provider_config()["id"]


def default_runtime() -> str:
    runtime = (os.environ.get("AGENT_RUNTIME") or "legacy").strip().lower()
    return runtime if runtime in ("legacy", "pi") else "legacy"


def provider_display_name(provider_id: Optional[str]) -> str:
    for provider in catalog.PROVIDERS:
        if provider["id"] == provider_id:
            return str(provider["name"])
    return provider_id or "Unknown"
