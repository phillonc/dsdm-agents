"""Read-only view over `generated/` for the console.

Every agent writes its output under `generated/<project>/` (AGENTS.md
convention #1), so that directory is the workspace the console browses. All
access goes through `_safe_path`, which refuses to resolve outside the
generated root - the console must never become a way to read arbitrary files
off the machine it runs on.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Extensions the console will render inline. Anything else is offered as a
# download-free "not previewable" entry rather than being decoded as text.
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".sh", ".bash",
    ".sql", ".env-example", ".gitignore", ".dockerfile", ".tf", ".xml", ".csv",
}

# Directories that are noise in a business-facing file browser.
HIDDEN_DIR_NAMES = {"__pycache__", ".git", "node_modules", ".venv", "env", ".pytest_cache"}

MAX_PREVIEW_BYTES = 400_000


class WorkspaceError(Exception):
    """Raised when a requested path is missing or outside the workspace."""


def generated_root() -> Path:
    """Return the absolute generated/ root, creating nothing.

    `src.rooms.delivery_room.GENERATED_ROOT` is the authority, but it is
    imported lazily: `src.rooms` and `src.orchestrator` import each other, so
    pulling either in at console-import time makes the order they are first
    imported in decide whether the process starts.
    """
    try:
        from ..rooms.delivery_room import GENERATED_ROOT

        root = GENERATED_ROOT
    except ImportError:  # pragma: no cover - agent deps not installed
        root = Path("generated")
    return root.resolve()


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _safe_path(project: str, relative: str = "") -> Path:
    """Resolve `generated/<project>/<relative>`, refusing to escape the root."""
    root = generated_root()
    candidate = (root / project / relative.lstrip("/")).resolve() if relative else (root / project).resolve()
    if candidate != root and root not in candidate.parents:
        raise WorkspaceError("Path is outside the workspace")
    return candidate


def _is_hidden(path: Path) -> bool:
    return path.name.startswith(".") or path.name in HIDDEN_DIR_NAMES


def _count_files(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not any(part in HIDDEN_DIR_NAMES for part in item.parts):
            total += 1
    return total


def _latest_mtime(path: Path) -> float:
    latest = path.stat().st_mtime
    for item in path.rglob("*"):
        if item.is_file():
            latest = max(latest, item.stat().st_mtime)
    return latest


def _room_summary(project_dir: Path) -> Optional[Dict[str, Any]]:
    """Return the delivery-room headline for a project, if it has a room."""
    state_path = project_dir / "room_state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "mission": data.get("mission", ""),
        "template": data.get("template", ""),
        "status": data.get("status", ""),
        "activePhase": data.get("active_phase"),
        "updatedAt": data.get("updated_at"),
        "openBlockers": len([b for b in data.get("blockers", []) if b.get("status") != "resolved"]),
    }


def list_projects() -> List[Dict[str, Any]]:
    """List every project folder under generated/, newest activity first."""
    root = generated_root()
    if not root.exists():
        return []

    projects: List[Dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or _is_hidden(entry):
            continue
        try:
            modified = _latest_mtime(entry)
            file_count = _count_files(entry)
        except OSError:
            continue
        projects.append(
            {
                "name": entry.name,
                "fileCount": file_count,
                "modifiedAt": _iso(modified),
                "room": _room_summary(entry),
            }
        )

    projects.sort(key=lambda item: item["modifiedAt"], reverse=True)
    return projects


def list_entries(project: str, relative: str = "") -> Dict[str, Any]:
    """List the folders and files directly inside `generated/<project>/<relative>`."""
    target = _safe_path(project, relative)
    if not target.exists():
        raise WorkspaceError(f"Not found: {project}/{relative}".rstrip("/"))
    if not target.is_dir():
        raise WorkspaceError("Not a folder")

    folders: List[Dict[str, Any]] = []
    files: List[Dict[str, Any]] = []
    for item in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        if _is_hidden(item):
            continue
        rel = str(item.relative_to(_safe_path(project)))
        try:
            stat = item.stat()
        except OSError:
            continue
        if item.is_dir():
            folders.append({"name": item.name, "path": rel, "modifiedAt": _iso(stat.st_mtime)})
        else:
            files.append(
                {
                    "name": item.name,
                    "path": rel,
                    "size": stat.st_size,
                    "modifiedAt": _iso(stat.st_mtime),
                    "previewable": item.suffix.lower() in TEXT_SUFFIXES,
                    "kind": "markdown" if item.suffix.lower() in (".md", ".markdown") else "text",
                }
            )

    return {
        "project": project,
        "path": relative.strip("/"),
        "folders": folders,
        "files": files,
    }


def read_file(project: str, relative: str) -> Dict[str, Any]:
    """Return the text content of a file for inline preview."""
    target = _safe_path(project, relative)
    if not target.exists() or not target.is_file():
        raise WorkspaceError(f"File not found: {relative}")

    stat = target.stat()
    suffix = target.suffix.lower()
    if suffix not in TEXT_SUFFIXES:
        return {
            "project": project,
            "path": relative,
            "kind": "binary",
            "size": stat.st_size,
            "modifiedAt": _iso(stat.st_mtime),
            "content": "",
            "truncated": False,
        }

    raw = target.read_bytes()
    truncated = len(raw) > MAX_PREVIEW_BYTES
    text = raw[:MAX_PREVIEW_BYTES].decode("utf-8", errors="replace")
    return {
        "project": project,
        "path": relative,
        "kind": "markdown" if suffix in (".md", ".markdown") else "text",
        "size": stat.st_size,
        "modifiedAt": _iso(stat.st_mtime),
        "content": text,
        "truncated": truncated,
    }


def recent_artifacts(limit: int = 12) -> List[Dict[str, Any]]:
    """Return the most recently written documents across every project."""
    root = generated_root()
    if not root.exists():
        return []

    found: List[Dict[str, Any]] = []
    for project_dir in root.iterdir():
        if not project_dir.is_dir() or _is_hidden(project_dir):
            continue
        for item in project_dir.rglob("*.md"):
            if any(part in HIDDEN_DIR_NAMES for part in item.parts):
                continue
            try:
                stat = item.stat()
            except OSError:
                continue
            found.append(
                {
                    "project": project_dir.name,
                    "name": item.name,
                    "path": str(item.relative_to(project_dir)),
                    "modifiedAt": _iso(stat.st_mtime),
                }
            )

    found.sort(key=lambda item: item["modifiedAt"], reverse=True)
    return found[:limit]
