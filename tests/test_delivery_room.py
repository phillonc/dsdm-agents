"""Tests for Autonomous Delivery Room."""

from pathlib import Path

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
