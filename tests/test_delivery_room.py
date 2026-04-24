"""Tests for Autonomous Delivery Room."""

from pathlib import Path

from src.agents.base_agent import AgentResult
from src.orchestrator.dsdm_orchestrator import DSDMPhase
from src.rooms.delivery_room import (
    add_room_blocker,
    add_room_decision,
    add_room_handoff,
    create_delivery_room,
    export_delivery_room,
    get_delivery_room_status,
    get_room_export_path,
    get_room_state_path,
)
from src.rooms.room_runner import run_delivery_room
from src.tools.room_tools import register_room_tools
from src.tools.tool_registry import ToolRegistry


class FakeAgent:
    def __init__(self, name):
        self.name = name


class FakeOrchestrator:
    PHASE_ORDER = [DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY]

    def __init__(self, fail_phase=None):
        self.fail_phase = fail_phase
        self.calls = []

    def get_agent(self, phase):
        return FakeAgent(f"{phase.value}_agent")

    def run_phase(self, phase, user_input, context=None):
        self.calls.append((phase, user_input, context))
        success = phase != self.fail_phase
        return AgentResult(
            success=success,
            output=f"{phase.value} output" if success else f"{phase.value} failed",
            artifacts={"phase": phase.value},
            next_phase_input={f"{phase.value}_report": "ready"} if success else None,
        )


def test_create_delivery_room_persists_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    room = create_delivery_room(
        mission="Build a task management platform",
        project_name="Task Platform",
        template="mvp",
    )

    assert room.project_name == "task-platform"
    assert room.mission == "Build a task management platform"
    assert room.template == "mvp"
    assert len(room.agents) >= 8
    assert get_room_state_path("task-platform").exists()
    assert get_room_export_path("task-platform").exists()


def test_room_status_counts_decisions_blockers_and_handoffs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_delivery_room("Build a marketplace", project_name="Marketplace", template="platform")
    add_room_decision(
        project_name="marketplace",
        title="Use platform template",
        owner_agent="DeliveryRoom",
        context="The product has customer and supplier sides.",
        decision="Use platform delivery template.",
        consequences=["Add Platform Strategist role"],
    )
    add_room_blocker(
        project_name="marketplace",
        title="Supplier onboarding flow undefined",
        owner_agent="BusinessStudyAgent",
        severity="high",
        suggested_resolution="Run stakeholder and process analysis.",
    )
    add_room_handoff(
        project_name="marketplace",
        from_agent="BusinessStudyAgent",
        to_agent="ProductManagerAgent",
        summary="Prioritized platform requirements are ready for PRD.",
        acceptance_gate="PRD includes customer and supplier journeys.",
        artifact_refs=["generated/marketplace/docs/BUSINESS_STUDY.md"],
    )

    status = get_delivery_room_status("marketplace")

    assert status["template"] == "platform"
    assert status["decision_count"] == 1
    assert status["open_blocker_count"] == 1
    assert status["handoff_count"] == 1
    assert any("Resolve blocker" in action for action in status["next_actions"])


def test_export_delivery_room_writes_markdown_dashboard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    create_delivery_room("Build a compliance app", project_name="Compliance App", template="compliance")
    export_path = export_delivery_room("compliance-app")

    assert export_path == Path("generated/compliance-app/docs/DELIVERY_ROOM.md")
    content = export_path.read_text(encoding="utf-8")
    assert "# Delivery Room: compliance-app" in content
    assert "Compliance Reviewer" in content
    assert "## Agents" in content


def test_run_delivery_room_records_phase_results_and_handoffs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    room = run_delivery_room(
        orchestrator=FakeOrchestrator(),
        mission="Build a scheduling app",
        project_name="Scheduling App",
        phases=[DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY],
        overwrite=True,
    )

    assert room.project_name == "scheduling-app"
    assert room.status == "completed"
    assert room.active_phase == "business_study"
    assert len(room.handoffs) == 1
    assert any(decision.title == "Feasibility phase completed" for decision in room.decisions)
    assert get_room_export_path("scheduling-app").exists()


def test_run_delivery_room_preserves_blocked_status_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    room = run_delivery_room(
        orchestrator=FakeOrchestrator(fail_phase=DSDMPhase.BUSINESS_STUDY),
        mission="Build a scheduling app",
        project_name="Blocked App",
        phases=[DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY],
        overwrite=True,
    )

    assert room.project_name == "blocked-app"
    assert room.status == "blocked"
    assert room.active_phase == "business_study"
    assert len(room.blockers) == 1
    assert room.blockers[0].owner_agent == "business_study_agent"


def test_room_tools_register_and_execute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    registry = ToolRegistry()
    register_room_tools(registry)

    assert registry.get("room_create") is not None
    assert registry.get("room_get_status") is not None

    create_result = registry.execute(
        "room_create",
        mission="Build a room tools app",
        project_name="Room Tools App",
        template="mvp",
    )
    assert "room-tools-app" in create_result

    status_result = registry.execute("room_get_status", project_name="room-tools-app")
    assert "agent_count" in status_result
