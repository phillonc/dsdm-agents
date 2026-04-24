"""Orchestrator extension hooks for Autonomous Delivery Room.

The core orchestrator can remain focused on DSDM phase execution while this
module installs the delivery-room integration points:

- delivery-room tools are registered on every orchestrator tool registry
- DSDMOrchestrator gets a formal run_delivery_room(...) method
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..orchestrator.dsdm_orchestrator import DSDMOrchestrator, DSDMPhase
from ..tools.room_tools import register_room_tools
from .room_state import DeliveryRoomState


_INSTALLED = False


def install_delivery_room_extensions() -> None:
    """Install delivery-room integrations onto DSDMOrchestrator once."""
    global _INSTALLED
    if _INSTALLED:
        return

    original_init = DSDMOrchestrator.__init__

    def __init_with_room_tools__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        register_room_tools(self.tool_registry)

    def run_delivery_room_method(
        self,
        mission: str,
        project_name: Optional[str] = None,
        template: str = "mvp",
        phases: Optional[Iterable[DSDMPhase]] = None,
        overwrite: bool = False,
    ) -> DeliveryRoomState:
        """Run an Autonomous Delivery Room with this orchestrator."""
        from .room_runner import run_delivery_room

        return run_delivery_room(
            orchestrator=self,
            mission=mission,
            project_name=project_name,
            template=template,
            phases=phases,
            overwrite=overwrite,
        )

    DSDMOrchestrator.__init__ = __init_with_room_tools__
    DSDMOrchestrator.run_delivery_room = run_delivery_room_method
    _INSTALLED = True
