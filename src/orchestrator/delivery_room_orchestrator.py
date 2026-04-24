"""DSDM orchestrator with native Autonomous Delivery Room support.

This module provides the public DSDMOrchestrator class exported by
`src.orchestrator`. It extends the core DSDM phase orchestrator with room tools
and a first-class `run_delivery_room(...)` method without monkey-patching the
core class at import time.
"""

from __future__ import annotations

from typing import Iterable, Optional

from .dsdm_orchestrator import DSDMOrchestrator as BaseDSDMOrchestrator
from .dsdm_orchestrator import DSDMPhase, OrchestratorConfig
from ..rooms.room_runner import run_delivery_room as run_delivery_room_workflow
from ..rooms.room_state import DeliveryRoomState
from ..tools.room_tools import register_room_tools


class DSDMOrchestrator(BaseDSDMOrchestrator):
    """DSDM orchestrator with native delivery-room workflow support."""

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        include_devops: bool = True,
        include_confluence: bool = True,
        include_jira: bool = True,
        show_progress: bool = True,
        include_delivery_room: bool = True,
    ):
        super().__init__(
            config=config,
            include_devops=include_devops,
            include_confluence=include_confluence,
            include_jira=include_jira,
            show_progress=show_progress,
        )
        self.include_delivery_room = include_delivery_room
        if include_delivery_room:
            register_room_tools(self.tool_registry)

    def run_delivery_room(
        self,
        mission: str,
        project_name: Optional[str] = None,
        template: str = "mvp",
        phases: Optional[Iterable[DSDMPhase]] = None,
        overwrite: bool = False,
    ) -> DeliveryRoomState:
        """Run an Autonomous Delivery Room using this orchestrator instance.

        Args:
            mission: Product or project mission for the delivery room.
            project_name: Optional stable project name. If omitted, the mission is slugified.
            template: Room template: mvp, platform, migration, enterprise, or compliance.
            phases: Optional subset of DSDM phases to execute.
            overwrite: Whether to replace existing room state.

        Returns:
            The final persisted DeliveryRoomState.
        """
        return run_delivery_room_workflow(
            orchestrator=self,
            mission=mission,
            project_name=project_name,
            template=template,
            phases=phases,
            overwrite=overwrite,
        )
