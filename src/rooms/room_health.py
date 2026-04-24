"""Health scoring for Autonomous Delivery Room."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .room_state import DeliveryRoomState


@dataclass
class RoomHealthScore:
    """Calculated health score for a delivery room."""

    overall: float
    delivery: float
    blockers: float
    decisions: float
    handoffs: float
    agents: float
    confidence: float
    status: str
    weak_points: List[str]
    recommended_actions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the health score."""
        return asdict(self)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 1)))


def calculate_room_health(room: DeliveryRoomState) -> RoomHealthScore:
    """Calculate a pragmatic health score from room state.

    The scoring is intentionally transparent and deterministic. It should be
    treated as decision support, not an absolute delivery guarantee.
    """
    weak_points: List[str] = []
    recommended_actions: List[str] = []

    open_blockers = [blocker for blocker in room.blockers if blocker.status != "resolved"]
    critical_blockers = [blocker for blocker in open_blockers if blocker.severity == "critical"]
    high_blockers = [blocker for blocker in open_blockers if blocker.severity == "high"]

    completed_agents = [agent for agent in room.agents if agent.status == "completed"]
    blocked_agents = [agent for agent in room.agents if agent.status == "blocked"]

    blocker_score = 100.0 - (len(open_blockers) * 18.0) - (len(high_blockers) * 12.0) - (len(critical_blockers) * 25.0)
    if open_blockers:
        weak_points.append(f"{len(open_blockers)} open blocker(s) need resolution")
        recommended_actions.append("Resolve or reassign open blockers before advancing the room")

    agent_score = 100.0
    if room.agents:
        agent_score = (len(completed_agents) / len(room.agents)) * 100.0
    if blocked_agents:
        agent_score -= len(blocked_agents) * 15.0
        weak_points.append(f"{len(blocked_agents)} agent assignment(s) are blocked")
        recommended_actions.append("Review blocked agent assignments and update ownership")

    decision_score = 60.0 if not room.decisions else min(100.0, 70.0 + len(room.decisions) * 6.0)
    if not room.decisions:
        weak_points.append("No decisions have been recorded yet")
        recommended_actions.append("Capture key delivery decisions with owner and consequences")

    handoff_score = 55.0 if not room.handoffs else min(100.0, 70.0 + len(room.handoffs) * 8.0)
    if room.active_phase not in (None, "kickoff") and not room.handoffs:
        weak_points.append("No handoffs have been recorded between agents or phases")
        recommended_actions.append("Record phase handoffs and acceptance gates")

    delivery_score = 75.0
    if room.status == "completed":
        delivery_score = 95.0
    elif room.status == "blocked":
        delivery_score = 35.0
        weak_points.append("Delivery room is blocked")
    elif room.status == "running":
        delivery_score = 70.0
    elif room.status == "created":
        delivery_score = 55.0
        recommended_actions.append("Start the first DSDM phase or confirm kickoff readiness")

    overall = _clamp(
        (_clamp(delivery_score) * 0.30)
        + (_clamp(blocker_score) * 0.25)
        + (_clamp(agent_score) * 0.20)
        + (_clamp(decision_score) * 0.15)
        + (_clamp(handoff_score) * 0.10)
    )

    if overall >= 80:
        status = "healthy"
    elif overall >= 60:
        status = "watch"
    elif overall >= 40:
        status = "at_risk"
    else:
        status = "critical"

    evidence_points = sum([
        bool(room.agents),
        bool(room.decisions),
        bool(room.blockers),
        bool(room.handoffs),
        bool(room.artifacts),
    ])
    confidence = _clamp(35.0 + evidence_points * 13.0)

    if not recommended_actions and room.next_actions:
        recommended_actions.extend(room.next_actions[:3])

    return RoomHealthScore(
        overall=overall,
        delivery=_clamp(delivery_score),
        blockers=_clamp(blocker_score),
        decisions=_clamp(decision_score),
        handoffs=_clamp(handoff_score),
        agents=_clamp(agent_score),
        confidence=confidence,
        status=status,
        weak_points=weak_points,
        recommended_actions=recommended_actions[:5],
    )
