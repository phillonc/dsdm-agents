"""Autonomous Delivery Room operations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .room_health import calculate_room_health
from .room_state import (
    DeliveryRoomState,
    RoomArtifact,
    RoomBlocker,
    RoomDecision,
    RoomHandoff,
)
from .room_templates import get_template_agents, get_template_next_actions, normalize_template


GENERATED_ROOT = Path("generated")


def slugify_project_name(value: str) -> str:
    """Create a filesystem-safe project name from user input."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:60] or "delivery-room-project"


def get_room_base_path(project_name: str) -> Path:
    """Return the base path for a project's generated artifacts."""
    return GENERATED_ROOT / slugify_project_name(project_name)


def get_room_state_path(project_name: str) -> Path:
    """Return the JSON state path for a delivery room."""
    return get_room_base_path(project_name) / "room_state.json"


def get_room_export_path(project_name: str) -> Path:
    """Return the Markdown export path for a delivery room."""
    return get_room_base_path(project_name) / "docs" / "DELIVERY_ROOM.md"


def _ensure_room_dirs(project_name: str) -> None:
    base = get_room_base_path(project_name)
    (base / "docs").mkdir(parents=True, exist_ok=True)


def _save_room(room: DeliveryRoomState) -> DeliveryRoomState:
    _ensure_room_dirs(room.project_name)
    room.touch()
    path = get_room_state_path(room.project_name)
    path.write_text(json.dumps(room.to_dict(), indent=2), encoding="utf-8")
    return room


def load_delivery_room(project_name: str) -> DeliveryRoomState:
    """Load a persisted delivery room by project name."""
    path = get_room_state_path(project_name)
    if not path.exists():
        raise FileNotFoundError(f"Delivery room not found for project: {project_name}")
    return DeliveryRoomState.from_dict(json.loads(path.read_text(encoding="utf-8")))


def create_delivery_room(
    mission: str,
    project_name: Optional[str] = None,
    template: str = "mvp",
    overwrite: bool = False,
) -> DeliveryRoomState:
    """Create a new delivery room and persist it."""
    normalized_template = normalize_template(template)
    resolved_project_name = slugify_project_name(project_name or mission)
    path = get_room_state_path(resolved_project_name)

    if path.exists() and not overwrite:
        return load_delivery_room(resolved_project_name)

    room = DeliveryRoomState(
        project_name=resolved_project_name,
        mission=mission.strip(),
        template=normalized_template,
        status="created",
        active_phase="kickoff",
        agents=get_template_agents(normalized_template),
        next_actions=get_template_next_actions(normalized_template),
    )
    room.artifacts.append(RoomArtifact(
        name="Delivery Room State",
        path=str(path),
        artifact_type="json_state",
        owner_agent="DeliveryRoom",
    ))
    _save_room(room)
    export_delivery_room(resolved_project_name)
    return room


def add_room_decision(
    project_name: str,
    title: str,
    owner_agent: str,
    context: str,
    decision: str,
    consequences: Optional[Iterable[str]] = None,
) -> DeliveryRoomState:
    """Add a decision to a delivery room."""
    room = load_delivery_room(project_name)
    decision_id = f"DEC-{len(room.decisions) + 1:03d}"
    room.decisions.append(RoomDecision(
        id=decision_id,
        title=title,
        owner_agent=owner_agent,
        context=context,
        decision=decision,
        consequences=list(consequences or []),
    ))
    return _save_room(room)


def add_room_blocker(
    project_name: str,
    title: str,
    owner_agent: str,
    severity: str,
    suggested_resolution: str,
    status: str = "open",
) -> DeliveryRoomState:
    """Add a blocker to a delivery room."""
    room = load_delivery_room(project_name)
    blocker_id = f"BLK-{len(room.blockers) + 1:03d}"
    room.blockers.append(RoomBlocker(
        id=blocker_id,
        title=title,
        owner_agent=owner_agent,
        severity=severity,
        status=status,
        suggested_resolution=suggested_resolution,
    ))
    if title not in room.next_actions:
        room.next_actions.insert(0, f"Resolve blocker: {title}")
    return _save_room(room)


def add_room_handoff(
    project_name: str,
    from_agent: str,
    to_agent: str,
    summary: str,
    acceptance_gate: str,
    artifact_refs: Optional[Iterable[str]] = None,
) -> DeliveryRoomState:
    """Add a handoff to a delivery room."""
    room = load_delivery_room(project_name)
    room.handoffs.append(RoomHandoff(
        from_agent=from_agent,
        to_agent=to_agent,
        artifact_refs=list(artifact_refs or []),
        summary=summary,
        acceptance_gate=acceptance_gate,
    ))
    return _save_room(room)


def set_room_phase(project_name: str, phase: Optional[str], status: Optional[str] = None) -> DeliveryRoomState:
    """Update the active phase and optional status for a delivery room."""
    room = load_delivery_room(project_name)
    room.active_phase = phase
    if status:
        room.status = status
    return _save_room(room)


def mark_room_agent_status(
    project_name: str,
    agent_name: str,
    status: str,
    current_task: Optional[str] = None,
) -> DeliveryRoomState:
    """Update the status for all room assignments using a given agent name."""
    room = load_delivery_room(project_name)
    for agent in room.agents:
        if agent.agent_name == agent_name:
            agent.status = status
            agent.current_task = current_task
    return _save_room(room)


def record_room_phase_result(
    project_name: str,
    phase: str,
    agent_name: str,
    success: bool,
    output: str,
    artifact_path: Optional[str] = None,
) -> DeliveryRoomState:
    """Record the result of a DSDM phase in the delivery room."""
    room = load_delivery_room(project_name)
    status = "completed" if success else "blocked"
    for agent in room.agents:
        if agent.agent_name == agent_name or agent.phase == phase:
            agent.status = status
            agent.current_task = None

    if artifact_path:
        artifact_name = f"{phase.replace('_', ' ').title()} Output"
        if not any(artifact.path == artifact_path for artifact in room.artifacts):
            room.artifacts.append(RoomArtifact(
                name=artifact_name,
                path=artifact_path,
                artifact_type="phase_output",
                owner_agent=agent_name,
            ))

    if success:
        room.decisions.append(RoomDecision(
            id=f"DEC-{len(room.decisions) + 1:03d}",
            title=f"{phase.replace('_', ' ').title()} phase completed",
            owner_agent=agent_name,
            context=f"Agent completed {phase} as part of the delivery room workflow.",
            decision="Proceed to the next planned delivery phase when dependencies are satisfied.",
            consequences=["Room state updated", "Phase output available for downstream agents"],
        ))
    else:
        summary = output.strip().splitlines()[0] if output.strip() else f"{phase} failed"
        room.blockers.append(RoomBlocker(
            id=f"BLK-{len(room.blockers) + 1:03d}",
            title=f"{phase.replace('_', ' ').title()} phase failed",
            owner_agent=agent_name,
            severity="high",
            status="open",
            suggested_resolution=summary[:240],
        ))
        room.next_actions.insert(0, f"Resolve failed phase: {phase}")

    room.active_phase = phase
    room.status = "running" if success else "blocked"
    return _save_room(room)


def get_delivery_room_status(project_name: str) -> Dict[str, Any]:
    """Return a compact room status dictionary."""
    room = load_delivery_room(project_name)
    open_blockers = [blocker for blocker in room.blockers if blocker.status != "resolved"]
    completed_agents = [agent for agent in room.agents if agent.status == "completed"]
    health = calculate_room_health(room)
    return {
        "project_name": room.project_name,
        "mission": room.mission,
        "template": room.template,
        "status": room.status,
        "active_phase": room.active_phase,
        "agent_count": len(room.agents),
        "completed_agent_count": len(completed_agents),
        "decision_count": len(room.decisions),
        "open_blocker_count": len(open_blockers),
        "handoff_count": len(room.handoffs),
        "health": health.to_dict(),
        "next_actions": room.next_actions,
        "updated_at": room.updated_at,
    }


def format_delivery_room_markdown(room: DeliveryRoomState) -> str:
    """Format delivery room state as Markdown."""
    health = calculate_room_health(room)
    lines = [
        f"# Delivery Room: {room.project_name}",
        "",
        f"**Mission:** {room.mission}",
        f"**Template:** {room.template}",
        f"**Status:** {room.status}",
        f"**Active phase:** {room.active_phase or 'None'}",
        f"**Updated:** {room.updated_at}",
        "",
        "## Health",
        "",
        f"**Overall:** {health.overall}/100 ({health.status})",
        f"**Confidence:** {health.confidence}/100",
        "",
        "| Dimension | Score |",
        "|---|---:|",
        f"| Delivery | {health.delivery} |",
        f"| Blockers | {health.blockers} |",
        f"| Agents | {health.agents} |",
        f"| Decisions | {health.decisions} |",
        f"| Handoffs | {health.handoffs} |",
        "",
        "### Weak Points",
        "",
    ]
    lines.extend([f"- {item}" for item in health.weak_points] or ["- No weak points detected from current room data."])
    lines.extend(["", "### Recommended Actions", ""])
    lines.extend([f"- {item}" for item in health.recommended_actions] or ["- Continue with the next planned DSDM phase."])
    lines.extend([
        "",
        "## Agents",
        "",
        "| Role | Agent | Phase | Status | Responsibilities |",
        "|---|---|---|---|---|",
    ])
    for agent in room.agents:
        responsibilities = "<br>".join(agent.responsibilities)
        lines.append(
            f"| {agent.role} | {agent.agent_name} | {agent.phase} | {agent.status} | {responsibilities} |"
        )

    lines.extend(["", "## Decisions", ""])
    if room.decisions:
        for decision in room.decisions:
            lines.extend([
                f"### {decision.id}: {decision.title}",
                f"- Owner: {decision.owner_agent}",
                f"- Context: {decision.context}",
                f"- Decision: {decision.decision}",
                f"- Consequences: {', '.join(decision.consequences) if decision.consequences else 'None recorded'}",
                "",
            ])
    else:
        lines.append("No decisions recorded yet.")

    lines.extend(["", "## Blockers", ""])
    if room.blockers:
        lines.extend(["| ID | Title | Owner | Severity | Status | Suggested Resolution |", "|---|---|---|---|---|---|"])
        for blocker in room.blockers:
            lines.append(
                f"| {blocker.id} | {blocker.title} | {blocker.owner_agent} | {blocker.severity} | {blocker.status} | {blocker.suggested_resolution} |"
            )
    else:
        lines.append("No blockers recorded yet.")

    lines.extend(["", "## Handoffs", ""])
    if room.handoffs:
        lines.extend(["| From | To | Summary | Acceptance Gate | Artifacts |", "|---|---|---|---|---|"])
        for handoff in room.handoffs:
            lines.append(
                f"| {handoff.from_agent} | {handoff.to_agent} | {handoff.summary} | {handoff.acceptance_gate} | {', '.join(handoff.artifact_refs)} |"
            )
    else:
        lines.append("No handoffs recorded yet.")

    lines.extend(["", "## Next Actions", ""])
    if room.next_actions:
        lines.extend([f"- {action}" for action in room.next_actions])
    else:
        lines.append("No next actions recorded.")

    lines.extend(["", "## Artifacts", ""])
    if room.artifacts:
        lines.extend(["| Name | Type | Path | Owner |", "|---|---|---|---|"])
        for artifact in room.artifacts:
            lines.append(
                f"| {artifact.name} | {artifact.artifact_type} | `{artifact.path}` | {artifact.owner_agent} |"
            )
    else:
        lines.append("No artifacts recorded yet.")

    return "\n".join(lines) + "\n"


def export_delivery_room(project_name: str) -> Path:
    """Export a delivery room dashboard to Markdown."""
    room = load_delivery_room(project_name)
    path = get_room_export_path(room.project_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_delivery_room_markdown(room), encoding="utf-8")
    return path
