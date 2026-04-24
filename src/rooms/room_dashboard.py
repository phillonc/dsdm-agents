"""Filtered dashboard views for Autonomous Delivery Room."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

from .delivery_room import load_delivery_room
from .room_health import calculate_room_health
from .room_state import DeliveryRoomState, RoomAgentAssignment, RoomArtifact, RoomBlocker, RoomDecision, RoomHandoff


DASHBOARD_SECTIONS = {"summary", "health", "agents", "blockers", "decisions", "handoffs", "artifacts", "actions"}


@dataclass
class RoomDashboardFilters:
    """Filters used to build a focused room dashboard."""

    sections: Optional[Set[str]] = None
    agent: Optional[str] = None
    phase: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    artifact_type: Optional[str] = None
    include_resolved: bool = False

    @classmethod
    def from_values(
        cls,
        sections: Optional[Iterable[str]] = None,
        agent: Optional[str] = None,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        artifact_type: Optional[str] = None,
        include_resolved: bool = False,
    ) -> "RoomDashboardFilters":
        normalized_sections = None
        if sections:
            normalized_sections = {item.strip().lower() for item in sections if item.strip()}
            invalid = normalized_sections - DASHBOARD_SECTIONS
            if invalid:
                raise ValueError(f"Unknown dashboard section(s): {', '.join(sorted(invalid))}")
        return cls(
            sections=normalized_sections,
            agent=agent.lower() if agent else None,
            phase=phase.lower() if phase else None,
            status=status.lower() if status else None,
            severity=severity.lower() if severity else None,
            artifact_type=artifact_type.lower() if artifact_type else None,
            include_resolved=include_resolved,
        )

    def show(self, section: str) -> bool:
        return self.sections is None or section in self.sections


def _matches_text_filter(value: str, needle: Optional[str]) -> bool:
    if not needle:
        return True
    return needle in value.lower()


def _filter_agents(room: DeliveryRoomState, filters: RoomDashboardFilters) -> List[RoomAgentAssignment]:
    agents = room.agents
    if filters.agent:
        agents = [agent for agent in agents if _matches_text_filter(agent.agent_name, filters.agent) or _matches_text_filter(agent.role, filters.agent)]
    if filters.phase:
        agents = [agent for agent in agents if _matches_text_filter(agent.phase, filters.phase)]
    if filters.status:
        agents = [agent for agent in agents if _matches_text_filter(agent.status, filters.status)]
    return agents


def _filter_blockers(room: DeliveryRoomState, filters: RoomDashboardFilters) -> List[RoomBlocker]:
    blockers = room.blockers
    if not filters.include_resolved:
        blockers = [blocker for blocker in blockers if blocker.status != "resolved"]
    if filters.agent:
        blockers = [blocker for blocker in blockers if _matches_text_filter(blocker.owner_agent, filters.agent)]
    if filters.status:
        blockers = [blocker for blocker in blockers if _matches_text_filter(blocker.status, filters.status)]
    if filters.severity:
        blockers = [blocker for blocker in blockers if _matches_text_filter(blocker.severity, filters.severity)]
    return blockers


def _filter_decisions(room: DeliveryRoomState, filters: RoomDashboardFilters) -> List[RoomDecision]:
    decisions = room.decisions
    if filters.agent:
        decisions = [decision for decision in decisions if _matches_text_filter(decision.owner_agent, filters.agent)]
    return decisions


def _filter_handoffs(room: DeliveryRoomState, filters: RoomDashboardFilters) -> List[RoomHandoff]:
    handoffs = room.handoffs
    if filters.agent:
        handoffs = [handoff for handoff in handoffs if _matches_text_filter(handoff.from_agent, filters.agent) or _matches_text_filter(handoff.to_agent, filters.agent)]
    return handoffs


def _filter_artifacts(room: DeliveryRoomState, filters: RoomDashboardFilters) -> List[RoomArtifact]:
    artifacts = room.artifacts
    if filters.agent:
        artifacts = [artifact for artifact in artifacts if _matches_text_filter(artifact.owner_agent, filters.agent)]
    if filters.artifact_type:
        artifacts = [artifact for artifact in artifacts if _matches_text_filter(artifact.artifact_type, filters.artifact_type)]
    if filters.phase:
        artifacts = [artifact for artifact in artifacts if _matches_text_filter(artifact.path, filters.phase) or _matches_text_filter(artifact.name, filters.phase)]
    return artifacts


def build_room_dashboard_markdown(project_name: str, filters: Optional[RoomDashboardFilters] = None) -> str:
    """Build a focused Markdown dashboard for a delivery room."""
    room = load_delivery_room(project_name)
    filters = filters or RoomDashboardFilters()
    health = calculate_room_health(room)

    lines: List[str] = [f"# Delivery Room Dashboard: {room.project_name}", ""]

    if filters.show("summary"):
        lines.extend([
            "## Summary",
            "",
            f"- Mission: {room.mission}",
            f"- Template: {room.template}",
            f"- Status: {room.status}",
            f"- Active phase: {room.active_phase or 'None'}",
            f"- Updated: {room.updated_at}",
            "",
        ])

    if filters.show("health"):
        lines.extend([
            "## Health",
            "",
            f"- Overall: {health.overall}/100 ({health.status})",
            f"- Confidence: {health.confidence}/100",
            f"- Delivery: {health.delivery}/100",
            f"- Blockers: {health.blockers}/100",
            f"- Agents: {health.agents}/100",
            f"- Decisions: {health.decisions}/100",
            f"- Handoffs: {health.handoffs}/100",
            "",
        ])

    if filters.show("agents"):
        agents = _filter_agents(room, filters)
        lines.extend(["## Agents", "", "| Role | Agent | Phase | Status | Current Task |", "|---|---|---|---|---|"])
        lines.extend([f"| {item.role} | {item.agent_name} | {item.phase} | {item.status} | {item.current_task or ''} |" for item in agents] or ["| - | - | - | - | No matching agents |"])
        lines.append("")

    if filters.show("blockers"):
        blockers = _filter_blockers(room, filters)
        lines.extend(["## Blockers", "", "| ID | Title | Owner | Severity | Status | Suggested Resolution |", "|---|---|---|---|---|---|"])
        lines.extend([f"| {item.id} | {item.title} | {item.owner_agent} | {item.severity} | {item.status} | {item.suggested_resolution} |" for item in blockers] or ["| - | - | - | - | - | No matching blockers |"])
        lines.append("")

    if filters.show("decisions"):
        decisions = _filter_decisions(room, filters)
        lines.extend(["## Decisions", ""])
        if decisions:
            for item in decisions:
                lines.extend([f"### {item.id}: {item.title}", f"- Owner: {item.owner_agent}", f"- Decision: {item.decision}", f"- Context: {item.context}", ""])
        else:
            lines.extend(["No matching decisions.", ""])

    if filters.show("handoffs"):
        handoffs = _filter_handoffs(room, filters)
        lines.extend(["## Handoffs", "", "| From | To | Summary | Acceptance Gate | Artifacts |", "|---|---|---|---|---|"])
        lines.extend([f"| {item.from_agent} | {item.to_agent} | {item.summary} | {item.acceptance_gate} | {', '.join(item.artifact_refs)} |" for item in handoffs] or ["| - | - | - | - | No matching handoffs |"])
        lines.append("")

    if filters.show("artifacts"):
        artifacts = _filter_artifacts(room, filters)
        lines.extend(["## Artifacts", "", "| Name | Type | Path | Owner |", "|---|---|---|---|"])
        lines.extend([f"| {item.name} | {item.artifact_type} | `{item.path}` | {item.owner_agent} |" for item in artifacts] or ["| - | - | - | No matching artifacts |"])
        lines.append("")

    if filters.show("actions"):
        recommended = health.recommended_actions or room.next_actions
        lines.extend(["## Recommended Actions", ""])
        lines.extend([f"- {item}" for item in recommended] or ["- Continue with the next planned DSDM phase."])
        lines.append("")

    return "\n".join(lines)
