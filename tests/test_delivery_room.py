"""Tests for Autonomous Delivery Room."""

from pathlib import Path

from src.agents.base_agent import AgentResult, ProgressEvent, ProgressInfo
from src.orchestrator import DSDMOrchestrator
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
    load_delivery_room,
)
from src.rooms.room_health import calculate_room_health
from src.rooms.room_progress import create_room_progress_callback
from src.rooms.room_runner import run_delivery_room
from src.tools.room_tools import register_room_tools
from src.tools.tool_registry import ToolRegistry


class FakeAgent:
    def __init__(self, name):
        self.name = name

    def set_progress_callback(self, callback):
        self.progress_callback = callback


class FakeOrchestrator:
    PHASE_ORDER = [DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY]

    def __init__(self, fail_phase=None):
        self.fail_phase = fail_phase
        self.calls = []
        self.agents = {}
        self.design_build_agents = {}
        self._progress_callback = None

    def get_agent(self, phase):
        return FakeAgent(f"{phase.value}_agent")

    def run_phase(self, phase, user_input, context=None):
        self.calls.append((phase, user_input, context))
        success = phase != self.fail_phase
        return AgentResult(
            success=success,
            output=f"{phase.value} output" if success else f"{phase.value} issue",
            artifacts={"phase": phase.value},
            next_phase_input={f"{phase.value}_report": "ready"} if success else None,
        )


def test_create_delivery_room_persists_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = create_delivery_room("Build a task management platform", project_name="Task Platform", template="mvp")
    assert room.project_name == "task-platform"
    assert room.template == "mvp"
    assert len(room.agents) >= 8
    assert get_room_state_path("task-platform").exists()
    assert get_room_export_path("task-platform").exists()


def test_room_status_counts_decisions_blockers_and_handoffs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_delivery_room("Build a marketplace", project_name="Marketplace", template="platform")
    add_room_decision("marketplace", "Use platform template", "DeliveryRoom", "Two-sided product", "Use platform delivery template.")
    add_room_blocker("marketplace", "Supplier flow undefined", "BusinessStudyAgent", "high", "Run stakeholder analysis.")
    add_room_handoff("marketplace", "BusinessStudyAgent", "ProductManagerAgent", "Requirements ready", "PRD includes journeys")
    status = get_delivery_room_status("marketplace")
    assert status["template"] == "platform"
    assert status["decision_count"] == 1
    assert status["open_blocker_count"] == 1
    assert status["handoff_count"] == 1
    assert "health" in status


def test_export_delivery_room_writes_markdown_dashboard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    create_delivery_room("Build a compliance app", project_name="Compliance App", template="compliance")
    export_path = export_delivery_room("compliance-app")
    assert export_path == Path("generated/compliance-app/docs/DELIVERY_ROOM.md")
    content = export_path.read_text(encoding="utf-8")
    assert "# Delivery Room: compliance-app" in content
    assert "Compliance Reviewer" in content
    assert "## Health" in content


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


def test_run_delivery_room_preserves_blocked_status_on_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = run_delivery_room(
        orchestrator=FakeOrchestrator(fail_phase=DSDMPhase.BUSINESS_STUDY),
        mission="Build a scheduling app",
        project_name="Blocked App",
        phases=[DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY],
        overwrite=True,
    )
    assert room.status == "blocked"
    assert room.active_phase == "business_study"
    assert len(room.blockers) == 1


def test_room_tools_register_and_execute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    registry = ToolRegistry()
    register_room_tools(registry)
    assert registry.get("room_create") is not None
    assert registry.get("room_get_status") is not None
    assert registry.get("room_get_health") is not None
    create_result = registry.execute("room_create", mission="Build a room tools app", project_name="Room Tools App", template="mvp")
    assert "room-tools-app" in create_result
    assert "health" in registry.execute("room_get_status", project_name="room-tools-app")
    assert "overall" in registry.execute("room_get_health", project_name="room-tools-app")


def test_room_health_identifies_open_issues(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = create_delivery_room("Build health app", project_name="Health App")
    add_room_blocker(room.project_name, "Dependency choice open", "DevLeadAgent", "critical", "Choose replacement dependency.")
    health = calculate_room_health(load_delivery_room(room.project_name))
    assert health.weak_points
    assert health.recommended_actions


def test_room_progress_callback_updates_agent_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    room = create_delivery_room("Build progress app", project_name="Progress App")
    callback = create_room_progress_callback(room.project_name)
    callback(ProgressInfo(event=ProgressEvent.STARTED, message="Starting", agent_name="ProductManagerAgent"))
    room = load_delivery_room(room.project_name)
    assert any(agent.agent_name == "ProductManagerAgent" and agent.status == "in_progress" for agent in room.agents)
    callback(ProgressInfo(event=ProgressEvent.COMPLETED, message="Done", agent_name="ProductManagerAgent"))
    room = load_delivery_room(room.project_name)
    assert any(agent.agent_name == "ProductManagerAgent" and agent.status == "completed" for agent in room.agents)


def test_orchestrator_extension_registers_room_tools():
    orchestrator = DSDMOrchestrator(show_progress=False, include_devops=False, include_jira=False, include_confluence=False)
    assert orchestrator.tool_registry.get("room_create") is not None
    assert orchestrator.tool_registry.get("room_get_health") is not None
    assert hasattr(orchestrator, "run_delivery_room")
