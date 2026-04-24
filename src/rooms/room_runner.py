"""Workflow runner for Autonomous Delivery Room."""

from __future__ import annotations

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
from .room_state import DeliveryRoomState


PHASE_HANDOFF_TARGETS = {
    DSDMPhase.FEASIBILITY: "BusinessStudyAgent",
    DSDMPhase.BUSINESS_STUDY: "ProductManagerAgent",
    DSDMPhase.PRD_TRD: "FunctionalModelAgent",
    DSDMPhase.FUNCTIONAL_MODEL: "DesignBuildAgent",
    DSDMPhase.DESIGN_BUILD: "ImplementationAgent",
}


def _phase_artifact_path(project_name: str, phase: DSDMPhase) -> str:
    """Return a conventional phase artifact path for room evidence."""
    phase_file = phase.value.upper()
    return f"generated/{project_name}/docs/{phase_file}_OUTPUT.md"


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


def run_delivery_room(
    orchestrator: DSDMOrchestrator,
    mission: str,
    project_name: Optional[str] = None,
    template: str = "mvp",
    phases: Optional[Iterable[DSDMPhase]] = None,
    overwrite: bool = False,
) -> DeliveryRoomState:
    """Run a delivery room through selected DSDM phases.

    This is intentionally a light orchestration layer above the existing
    DSDMOrchestrator. It keeps the core phase execution unchanged while adding
    room state, handoffs, decisions, blockers, and dashboard export.
    """
    room = create_delivery_room(
        mission=mission,
        project_name=project_name,
        template=template,
        overwrite=overwrite,
    )
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

    for phase in selected_phases:
        set_room_phase(room.project_name, phase.value, "running")
        agent = orchestrator.get_agent(phase)
        agent_name = agent.name if agent else phase.value

        phase_input = (
            f"Delivery Room Mission: {room.mission}\n"
            f"Project: {room.project_name}\n"
            f"Template: {room.template}\n\n"
            f"Run the {phase.value.replace('_', ' ')} phase. "
            "Use the delivery room context to preserve clear role ownership, blockers, decisions, and handoffs."
        )
        result = orchestrator.run_phase(phase, phase_input, context)
        artifact_path = _phase_artifact_path(room.project_name, phase)
        record_room_phase_result(
            project_name=room.project_name,
            phase=phase.value,
            agent_name=agent_name,
            success=result.success,
            output=result.output,
            artifact_path=artifact_path,
        )

        if previous_agent_name and previous_phase:
            add_room_handoff(
                project_name=room.project_name,
                from_agent=previous_agent_name,
                to_agent=agent_name,
                summary=f"{previous_phase.value.replace('_', ' ').title()} output handed to {phase.value.replace('_', ' ').title()}.",
                acceptance_gate=f"{phase.value.replace('_', ' ').title()} agent confirms it has enough context to proceed.",
                artifact_refs=[_phase_artifact_path(room.project_name, previous_phase)],
            )

        export_delivery_room(room.project_name)

        if not result.success:
            break

        context.update(_result_context(result))
        previous_agent_name = agent_name
        previous_phase = phase

    set_room_phase(room.project_name, selected_phases[-1].value if selected_phases else None, "completed")
    export_delivery_room(room.project_name)
    return load_delivery_room(room.project_name)
