"""State models for Autonomous Delivery Room."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


ROOM_STATE_VERSION = "0.1.0"


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoomAgentAssignment:
    """Role assignment for an agent in a delivery room."""

    role: str
    agent_name: str
    phase: str
    responsibilities: List[str]
    status: str = "assigned"
    current_task: Optional[str] = None


@dataclass
class RoomDecision:
    """Decision captured by the delivery room."""

    id: str
    title: str
    owner_agent: str
    context: str
    decision: str
    consequences: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class RoomBlocker:
    """Blocker captured by the delivery room."""

    id: str
    title: str
    owner_agent: str
    severity: str
    status: str
    suggested_resolution: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class RoomHandoff:
    """Handoff between two agents or phases."""

    from_agent: str
    to_agent: str
    artifact_refs: List[str]
    summary: str
    acceptance_gate: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class RoomArtifact:
    """Artifact produced or referenced by a delivery room."""

    name: str
    path: str
    artifact_type: str
    owner_agent: str
    created_at: str = field(default_factory=utc_now_iso)


@dataclass
class DeliveryRoomState:
    """Persisted state for an Autonomous Delivery Room."""

    project_name: str
    mission: str
    template: str
    status: str = "created"
    active_phase: Optional[str] = None
    agents: List[RoomAgentAssignment] = field(default_factory=list)
    decisions: List[RoomDecision] = field(default_factory=list)
    blockers: List[RoomBlocker] = field(default_factory=list)
    handoffs: List[RoomHandoff] = field(default_factory=list)
    artifacts: List[RoomArtifact] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    version: str = ROOM_STATE_VERSION

    def touch(self) -> None:
        """Refresh the update timestamp."""
        self.updated_at = utc_now_iso()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the room state to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeliveryRoomState":
        """Deserialize room state from a dictionary."""
        return cls(
            project_name=data["project_name"],
            mission=data.get("mission", ""),
            template=data.get("template", "mvp"),
            status=data.get("status", "created"),
            active_phase=data.get("active_phase"),
            agents=[RoomAgentAssignment(**item) for item in data.get("agents", [])],
            decisions=[RoomDecision(**item) for item in data.get("decisions", [])],
            blockers=[RoomBlocker(**item) for item in data.get("blockers", [])],
            handoffs=[RoomHandoff(**item) for item in data.get("handoffs", [])],
            artifacts=[RoomArtifact(**item) for item in data.get("artifacts", [])],
            next_actions=list(data.get("next_actions", [])),
            created_at=data.get("created_at", utc_now_iso()),
            updated_at=data.get("updated_at", utc_now_iso()),
            version=data.get("version", ROOM_STATE_VERSION),
        )
