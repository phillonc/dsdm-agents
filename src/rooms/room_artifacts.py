"""Artifact discovery and synchronization for Autonomous Delivery Room."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional

from .delivery_room import get_room_base_path, get_room_state_path, load_delivery_room, slugify_project_name
from .room_events import RoomEventType, append_room_event
from .room_state import RoomArtifact


DEFAULT_ARTIFACT_DIRS = ("docs", "src", "tests", "deploy", "deployment", "artifacts")
ARTIFACT_SUFFIXES = {
    ".md": "markdown",
    ".json": "json",
    ".yaml": "config",
    ".yml": "config",
    ".py": "python_source",
    ".ts": "typescript_source",
    ".tsx": "react_source",
    ".js": "javascript_source",
    ".jsx": "react_source",
    ".html": "html",
    ".css": "css",
    ".sh": "script",
}


def infer_artifact_type(path: Path) -> str:
    """Infer a useful artifact type from a path."""
    name = path.name.upper()
    if name.endswith("_OUTPUT.MD"):
        return "phase_output"
    if "TEST" in path.parts or path.name.startswith("test_") or path.name.endswith(".spec.ts"):
        return "test_artifact"
    if "DEPLOY" in name or "deployment" in [part.lower() for part in path.parts]:
        return "deployment_artifact"
    return ARTIFACT_SUFFIXES.get(path.suffix.lower(), "file")


def infer_owner_agent(path: Path) -> str:
    """Infer artifact owner from filename conventions."""
    name = path.name.upper()
    mapping = {
        "FEASIBILITY": "FeasibilityAgent",
        "BUSINESS_STUDY": "BusinessStudyAgent",
        "PRD_TRD": "ProductManagerAgent",
        "FUNCTIONAL_MODEL": "FunctionalModelAgent",
        "DESIGN_BUILD": "DesignBuildAgent",
        "IMPLEMENTATION": "ImplementationAgent",
    }
    for token, owner in mapping.items():
        if token in name:
            return owner
    if "test" in path.name.lower():
        return "AutomationTesterAgent"
    return "DeliveryRoom"


def _artifact_name(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def discover_room_artifacts(
    project_name: str,
    directories: Optional[Iterable[str]] = None,
    suffixes: Optional[Iterable[str]] = None,
) -> List[RoomArtifact]:
    """Discover artifact files under generated/<project>."""
    project_slug = slugify_project_name(project_name)
    base_path = get_room_base_path(project_slug)
    scan_dirs = tuple(directories or DEFAULT_ARTIFACT_DIRS)
    allowed_suffixes = {suffix.lower() for suffix in suffixes} if suffixes else set(ARTIFACT_SUFFIXES)
    discovered: List[RoomArtifact] = []

    for directory in scan_dirs:
        root = base_path / directory
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            if allowed_suffixes and path.suffix.lower() not in allowed_suffixes:
                continue
            discovered.append(RoomArtifact(
                name=_artifact_name(path),
                path=str(path),
                artifact_type=infer_artifact_type(path),
                owner_agent=infer_owner_agent(path),
            ))
    return discovered


def sync_room_artifacts(
    project_name: str,
    directories: Optional[Iterable[str]] = None,
    suffixes: Optional[Iterable[str]] = None,
) -> List[RoomArtifact]:
    """Discover artifacts and add missing ones to room state."""
    room = load_delivery_room(project_name)
    discovered = discover_room_artifacts(room.project_name, directories, suffixes)
    existing_paths = {artifact.path for artifact in room.artifacts}
    new_artifacts = [artifact for artifact in discovered if artifact.path not in existing_paths]

    if new_artifacts:
        room.artifacts.extend(new_artifacts)
        room.touch()
        get_room_state_path(room.project_name).write_text(json.dumps(room.to_dict(), indent=2), encoding="utf-8")
        for artifact in new_artifacts:
            append_room_event(
                room.project_name,
                RoomEventType.ARTIFACT_DISCOVERED,
                f"Artifact discovered: {artifact.name}",
                actor="DeliveryRoom",
                payload={"path": artifact.path, "artifact_type": artifact.artifact_type, "owner_agent": artifact.owner_agent},
            )
    return new_artifacts
