"""Tools for Autonomous Delivery Room."""

from __future__ import annotations

import json
from typing import Any, Dict

from .tool_registry import Tool, ToolRegistry
from ..rooms.delivery_room import (
    add_room_blocker,
    add_room_decision,
    add_room_handoff,
    create_delivery_room,
    export_delivery_room,
    get_delivery_room_status,
    load_delivery_room,
)
from ..rooms.room_artifacts import discover_room_artifacts, sync_room_artifacts
from ..rooms.room_events import export_room_events_markdown, filter_room_events
from ..rooms.room_health import calculate_room_health


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def register_room_tools(registry: ToolRegistry) -> None:
    """Register delivery room tools on a tool registry."""

    registry.register(Tool(
        name="room_create",
        description="Create an Autonomous Delivery Room for a project with assigned agents, mission, status, and initial next actions.",
        input_schema={
            "type": "object",
            "properties": {
                "mission": {"type": "string", "description": "Project mission or product description"},
                "project_name": {"type": "string", "description": "Optional project name"},
                "template": {"type": "string", "enum": ["mvp", "platform", "migration", "enterprise", "compliance"]},
                "overwrite": {"type": "boolean", "description": "Overwrite existing room state"},
            },
            "required": ["mission"],
        },
        handler=lambda mission, project_name=None, template="mvp", overwrite=False: _json(create_delivery_room(mission, project_name, template, overwrite).to_dict()),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_get_status",
        description="Get a compact status summary for an Autonomous Delivery Room, including health score and next actions.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]},
        handler=lambda project_name: _json(get_delivery_room_status(project_name)),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_get_health",
        description="Calculate delivery room health scores, weak points, confidence, and recommended actions.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]},
        handler=lambda project_name: _json(calculate_room_health(load_delivery_room(project_name)).to_dict()),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_discover_artifacts",
        description="Discover artifact files under generated/<project> without mutating room state.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]},
        handler=lambda project_name: _json([artifact.__dict__ for artifact in discover_room_artifacts(project_name)]),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_sync_artifacts",
        description="Discover generated project files and add missing artifacts to delivery room state.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]},
        handler=lambda project_name: _json({"project_name": project_name, "synced": True, "new_artifacts": [artifact.__dict__ for artifact in sync_room_artifacts(project_name)]}),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_list_events",
        description="List delivery room audit events with optional filters.",
        input_schema={
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "event_type": {"type": "string"},
                "actor": {"type": "string"},
                "phase": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["project_name"],
        },
        handler=lambda project_name, event_type=None, actor=None, phase=None, limit=None: _json([event.to_dict() for event in filter_room_events(project_name, event_type, actor, phase, limit)]),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_export_events",
        description="Export delivery room audit events to Markdown.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["project_name"]},
        handler=lambda project_name, limit=None: _json({"project_name": project_name, "exported": True, "path": str(export_room_events_markdown(project_name, limit))}),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_add_decision",
        description="Add a decision entry to an Autonomous Delivery Room.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}, "title": {"type": "string"}, "owner_agent": {"type": "string"}, "context": {"type": "string"}, "decision": {"type": "string"}, "consequences": {"type": "array", "items": {"type": "string"}}}, "required": ["project_name", "title", "owner_agent", "context", "decision"]},
        handler=lambda project_name, title, owner_agent, context, decision, consequences=None: _json(add_room_decision(project_name, title, owner_agent, context, decision, consequences).to_dict()),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_add_blocker",
        description="Add a blocker entry to an Autonomous Delivery Room.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}, "title": {"type": "string"}, "owner_agent": {"type": "string"}, "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]}, "status": {"type": "string"}, "suggested_resolution": {"type": "string"}}, "required": ["project_name", "title", "owner_agent", "severity", "suggested_resolution"]},
        handler=lambda project_name, title, owner_agent, severity, suggested_resolution, status="open": _json(add_room_blocker(project_name, title, owner_agent, severity, suggested_resolution, status).to_dict()),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_add_handoff",
        description="Add a handoff entry between two agents in an Autonomous Delivery Room.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}, "from_agent": {"type": "string"}, "to_agent": {"type": "string"}, "summary": {"type": "string"}, "acceptance_gate": {"type": "string"}, "artifact_refs": {"type": "array", "items": {"type": "string"}}}, "required": ["project_name", "from_agent", "to_agent", "summary", "acceptance_gate"]},
        handler=lambda project_name, from_agent, to_agent, summary, acceptance_gate, artifact_refs=None: _json(add_room_handoff(project_name, from_agent, to_agent, summary, acceptance_gate, artifact_refs).to_dict()),
        requires_approval=False,
        category="delivery_room",
    ))

    registry.register(Tool(
        name="room_export",
        description="Export an Autonomous Delivery Room dashboard to Markdown.",
        input_schema={"type": "object", "properties": {"project_name": {"type": "string"}}, "required": ["project_name"]},
        handler=lambda project_name: _json({"project_name": project_name, "exported": True, "path": str(export_delivery_room(project_name))}),
        requires_approval=False,
        category="delivery_room",
    ))
