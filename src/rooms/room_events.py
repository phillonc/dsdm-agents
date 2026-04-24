"""Event audit trail for Autonomous Delivery Room."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .room_state import utc_now_iso
from .delivery_room import get_room_base_path, slugify_project_name


class RoomEventType(str, Enum):
    """Supported delivery room event types."""

    ROOM_CREATED = "room_created"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    BLOCKER_ADDED = "blocker_added"
    DECISION_ADDED = "decision_added"
    HANDOFF_ADDED = "handoff_added"
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_DISCOVERED = "artifact_discovered"
    HEALTH_UPDATED = "health_updated"
    AGENT_STATUS_CHANGED = "agent_status_changed"
    DASHBOARD_EXPORTED = "dashboard_exported"


@dataclass
class RoomEvent:
    """Single immutable event in the delivery room audit trail."""

    id: str
    project_name: str
    event_type: str
    title: str
    actor: str = "DeliveryRoom"
    phase: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoomEvent":
        return cls(
            id=data["id"],
            project_name=data["project_name"],
            event_type=data["event_type"],
            title=data["title"],
            actor=data.get("actor", "DeliveryRoom"),
            phase=data.get("phase"),
            payload=dict(data.get("payload", {})),
            created_at=data.get("created_at", utc_now_iso()),
        )


def get_room_events_path(project_name: str) -> Path:
    """Return the event store path for a project."""
    return get_room_base_path(project_name) / "room_events.jsonl"


def load_room_events(project_name: str) -> List[RoomEvent]:
    """Load all room events from JSONL."""
    path = get_room_events_path(project_name)
    if not path.exists():
        return []
    events: List[RoomEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(RoomEvent.from_dict(json.loads(line)))
    return events


def append_room_event(
    project_name: str,
    event_type: RoomEventType | str,
    title: str,
    actor: str = "DeliveryRoom",
    phase: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> RoomEvent:
    """Append an event to the room audit trail."""
    normalized_project = slugify_project_name(project_name)
    path = get_room_events_path(normalized_project)
    path.parent.mkdir(parents=True, exist_ok=True)
    event_value = event_type.value if isinstance(event_type, RoomEventType) else str(event_type)
    event = RoomEvent(
        id=f"EVT-{len(load_room_events(normalized_project)) + 1:05d}",
        project_name=normalized_project,
        event_type=event_value,
        title=title,
        actor=actor,
        phase=phase,
        payload=payload or {},
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.to_dict(), default=str) + "\n")
    return event


def filter_room_events(
    project_name: str,
    event_type: Optional[str] = None,
    actor: Optional[str] = None,
    phase: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[RoomEvent]:
    """Filter room events by type, actor, phase, and optional limit."""
    events = load_room_events(project_name)
    if event_type:
        needle = event_type.lower()
        events = [event for event in events if needle in event.event_type.lower()]
    if actor:
        needle = actor.lower()
        events = [event for event in events if needle in event.actor.lower()]
    if phase:
        needle = phase.lower()
        events = [event for event in events if event.phase and needle in event.phase.lower()]
    if limit is not None:
        events = events[-limit:]
    return events


def export_room_events_markdown(project_name: str, limit: Optional[int] = None) -> Path:
    """Export room events to Markdown for review."""
    events = filter_room_events(project_name, limit=limit)
    output_path = get_room_base_path(project_name) / "docs" / "ROOM_EVENTS.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# Room Events: {slugify_project_name(project_name)}", "", "| ID | Type | Actor | Phase | Title | Created |", "|---|---|---|---|---|---|"]
    for event in events:
        lines.append(f"| {event.id} | {event.event_type} | {event.actor} | {event.phase or ''} | {event.title} | {event.created_at} |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
