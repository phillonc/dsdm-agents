"""Workflow runner for Autonomous Delivery Room."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..agents.base_agent import AgentResult
from ..orchestrator.dsdm_orchestrator import DSDMOrchestrator, DSDMPhase
from .delivery_room import (
    add_room_handoff,
    create_delivery_room,
    export_delivery_room,
    load_delivery_room,
    record_room_phase_result,
    set_room_phase,
)
from .room_artifacts import sync_room_artifacts
from .room_events import RoomEventType, append_room_event, export_room_events_markdown
from .room_progress import create_room_progress_callback
from .room_state import DeliveryRoomState


PHASE_HANDOFF_TARGETS = {
    DSDMPhase.FEASIBILITY: "BusinessStudyAgent",
    DSDMPhase.BUSINESS_STUDY: "ProductManagerAgent",
    DSDMPhase.PRD_TRD: "FunctionalModelAgent",
    DSDMPhase.FUNCTIONAL_MODEL: "DesignBuildAgent",
    DSDMPhase.DESIGN_BUILD: "ImplementationAgent",
}


def _phase_artifact_path(project_name: str, phase: DSDMPhase) -> str:
    """Return the actual phase output artifact path for room evidence."""
    phase_file = phase.value.upper()
    return f"generated/{project_name}/docs/{phase_file}_OUTPUT.md"


def _write_phase_artifact(
    project_name: str,
    phase: DSDMPhase,
    agent_name: str,
    result: AgentResult,
) -> str:
    """Persist phase output to a real Markdown artifact and return its path."""
    artifact_path = Path(_phase_artifact_path(project_name, phase))
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    artifact_json = json.dumps(result.artifacts or {}, indent=2, default=str)
    tool_calls_json = json.dumps(result.tool_calls or [], indent=2, default=str)
    content = (
        f"# {phase.value.replace('_', ' ').title()} Output\n\n"
        f"**Project:** {project_name}\n"
        f"**Agent:** {agent_name}\n"
        f"**Success:** {result.success}\n\n"
        "## Output\n\n"
        f"{result.output or 'No output returned.'}\n\n"
        "## Artifacts\n\n"
        f"```json\n{artifact_json}\n```\n\n"
        "## Tool Calls\n\n"
        f"```json\n{tool_calls_json}\n```\n"
    )
    artifact_path.write_text(content, encoding="utf-8")
    append_room_event(
        project_name,
        RoomEventType.ARTIFACT_CREATED,
        f"Artifact created: {artifact_path.name}",
        actor=agent_name,
        phase=phase.value,
        payload={"path": str(artifact_path)},
    )
    return str(artifact_path)


def _result_context(result: AgentResult) -> Dict[str, Any]:
    """Build compact context from an agent result for downstream phases."""
    context: Dict[str, Any] = {
        "previous_output": result.output,
        "previous_success": result.success,
    }
    if result.artifacts:
        context["previous_artifacts"] = result.artifacts
    if result.next_phase_input:
        context.update(result.next_phase_input)
    return context


def _install_room_progress_callback(orchestrator: DSDMOrchestrator, project_name: str) -> None:
    """Wrap the existing progress callback so room state tracks agent events."""
    previous_callback = getattr(orchestrator, "_progress_callback", None)
    room_callback = create_room_progress_callback(project_name, previous_callback)
    orchestrator._progress_callback = room_callback

    for agent in getattr(orchestrator, "agents", {}).values():
        agent.set_progress_callback(room_callback)
    for agent in getattr(orchestrator, "design_build_agents", {}).values():
        agent.set_progress_callback(room_callback)


def run_delivery_room(
    orchestrator: DSDMOrchestrator,
    mission: str,
    project_name: Optional[str] = None,
    template: str = "mvp",
    phases: Optional[Iterable[DSDMPhase]] = None,
    overwrite: bool = False,
) -> DeliveryRoomState:
    """Run a delivery room through selected DSDM phases."""
    room = create_delivery_room(
        mission=mission,
        project_name=project_name,
        template=template,
        overwrite=overwrite,
    )
    append_room_event(
        room.project_name,
        RoomEventType.ROOM_CREATED,
        "Delivery room workflow started",
        payload={"mission": room.mission, "template": room.template},
    )
    _install_room_progress_callback(orchestrator, room.project_name)

    selected_phases = list(phases or DSDMOrchestrator.PHASE_ORDER)
    context: Dict[str, Any] = {
        "delivery_room": {
            "project_name": room.project_name,
            "mission": room.mission,
            "template": room.template,
        }
    }

    previous_agent_name: Optional[str] = None
    previous_phase: Optional[DSDMPhase] = None
    previous_artifact_path: Optional[str] = None
    last_phase: Optional[DSDMPhase] = None
    blocked = False

    for phase in selected_phases:
        last_phase = phase
        set_room_phase(room.project_name, phase.value, "running")
        agent = orchestrator.get_agent(phase)
        agent_name = agent.name if agent else phase.value
        append_room_event(room.project_name, RoomEventType.PHASE_STARTED, f"{phase.value} started", actor=agent_name, phase=phase.value)

        phase_input = (
            f"Delivery Room Mission: {room.mission}\n"
            f"Project: {room.project_name}\n"
            f"Template: {room.template}\n\n"
            f"Run the {phase.value.replace('_', ' ')} phase. "
            "Use the delivery room context to preserve clear role ownership, blockers, decisions, and handoffs."
        )
        result = orchestrator.run_phase(phase, phase_input, context)
        artifact_path = _write_phase_artifact(room.project_name, phase, agent_name, result)
        record_room_phase_result(
            project_name=room.project_name,
            phase=phase.value,
            agent_name=agent_name,
            success=result.success,
            output=result.output,
            artifact_path=artifact_path,
        )
        append_room_event(
            room.project_name,
            RoomEventType.PHASE_COMPLETED if result.success else RoomEventType.PHASE_FAILED,
            f"{phase.value} {'completed' if result.success else 'failed'}",
            actor=agent_name,
            phase=phase.value,
            payload={"artifact_path": artifact_path},
        )

        if previous_agent_name and previous_phase:
            add_room_handoff(
                project_name=room.project_name,
                from_agent=previous_agent_name,
                to_agent=agent_name,
                summary=f"{previous_phase.value.replace('_', ' ').title()} output handed to {phase.value.replace('_', ' ').title()}.",
                acceptance_gate=f"{phase.value.replace('_', ' ').title()} agent confirms it has enough context to proceed.",
                artifact_refs=[previous_artifact_path] if previous_artifact_path else [],
            )
            append_room_event(
                room.project_name,
                RoomEventType.HANDOFF_ADDED,
                f"Handoff: {previous_agent_name} to {agent_name}",
                actor="DeliveryRoom",
                phase=phase.value,
                payload={"artifact_refs": [previous_artifact_path] if previous_artifact_path else []},
            )

        sync_room_artifacts(room.project_name)
        export_delivery_room(room.project_name)

        if not result.success:
            blocked = True
            break

        context.update(_result_context(result))
        context["previous_artifact_path"] = artifact_path
        previous_agent_name = agent_name
        previous_phase = phase
        previous_artifact_path = artifact_path

    final_status = "blocked" if blocked else "completed"
    set_room_phase(room.project_name, last_phase.value if last_phase else None, final_status)
    append_room_event(room.project_name, RoomEventType.HEALTH_UPDATED, f"Room workflow {final_status}", payload={"status": final_status})
    export_delivery_room(room.project_name)
    export_room_events_markdown(room.project_name)
    return load_delivery_room(room.project_name)
