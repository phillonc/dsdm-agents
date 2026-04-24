"""Progress callback integration for Autonomous Delivery Room."""

from __future__ import annotations

from typing import Callable, Optional

from ..agents.base_agent import ProgressEvent, ProgressInfo
from .delivery_room import add_room_blocker, mark_room_agent_status

ProgressCallback = Callable[[ProgressInfo], None]


def create_room_progress_callback(
    project_name: str,
    previous_callback: Optional[ProgressCallback] = None,
) -> ProgressCallback:
    """Create a callback that mirrors agent progress into room state.

    The callback deliberately keeps room writes lightweight:
    - STARTED/THINKING/PROCESSING marks the agent as in progress
    - COMPLETED marks the agent as completed
    - ERROR marks the agent as blocked and adds a blocker

    Any previous callback is invoked first so console progress rendering remains
    unchanged when room tracking is enabled.
    """

    def callback(info: ProgressInfo) -> None:
        if previous_callback:
            previous_callback(info)

        agent_name = info.agent_name or "UnknownAgent"
        try:
            if info.event in {ProgressEvent.STARTED, ProgressEvent.THINKING, ProgressEvent.PROCESSING, ProgressEvent.ITERATION}:
                mark_room_agent_status(project_name, agent_name, "in_progress", info.message)
            elif info.event == ProgressEvent.COMPLETED:
                mark_room_agent_status(project_name, agent_name, "completed")
            elif info.event == ProgressEvent.ERROR:
                mark_room_agent_status(project_name, agent_name, "blocked", info.message)
                add_room_blocker(
                    project_name=project_name,
                    title=f"{agent_name} progress error",
                    owner_agent=agent_name,
                    severity="high",
                    suggested_resolution=info.message,
                    status="open",
                )
        except FileNotFoundError:
            # Room may not exist if callback is reused outside a room workflow.
            return

    return callback
