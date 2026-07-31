"""Tests for the DSDM Agents Console (src/gui)."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from src.agents.base_agent import AgentResult, ProgressEvent, ProgressInfo
from src.gui import api, catalog, checkpoints, workspace
from src.gui.runs import RollbackError, RunManager
from src.gui.server import create_server
from src.orchestrator.dsdm_orchestrator import DSDMPhase


# --------------------------------------------------------------------- doubles


class FakeTool:
    def __init__(self, name):
        self.name = name
        self.description = f"Description for {name}"


class FakeToolRegistry:
    def get(self, name):
        return FakeTool(name)


class FakeAgent:
    def __init__(self):
        self.progress_callback = None
        self.approval_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback


class FakeOrchestrator:
    """Stands in for DSDMOrchestrator so tests never call an LLM."""

    def __init__(self, fail_phase=None, ask_approval_in=None, writes=None, project=None):
        self.tool_registry = FakeToolRegistry()
        self.agents = {"only": FakeAgent()}
        self.design_build_agents = {}
        self.calls = []
        self.fail_phase = fail_phase
        self.ask_approval_in = ask_approval_in
        self.writes = writes  # relative path under generated/, written like a real agent would
        self.project = project  # when set, writes a per-stage doc plus a shared SUMMARY.md
        self.contexts = []
        self.approval_answers = []
        self.shutdown_called = False

    def run_phase(self, phase, user_input, context=None):
        self.calls.append(phase)
        self.contexts.append(context)
        if self.writes:
            target = Path("generated") / self.writes
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"# {phase.value}", encoding="utf-8")
        if self.project:
            docs = Path("generated") / self.project / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            (docs / f"{phase.value.upper()}.md").write_text(f"# {phase.value}", encoding="utf-8")
            (docs / "SUMMARY.md").write_text(f"latest: {phase.value}", encoding="utf-8")
        agent = self.agents["only"]
        if agent.progress_callback:
            agent.progress_callback(
                ProgressInfo(
                    event=ProgressEvent.TOOL_CALLING,
                    message=f"Working on {phase.value}",
                    agent_name="FakeAgent",
                    iteration=1,
                    max_iterations=10,
                    tool_name="write_file",
                )
            )
        if self.ask_approval_in == phase and agent.approval_callback:
            self.approval_answers.append(agent.approval_callback("write_file", {"file_path": "docs/PRD.md"}))
        success = phase != self.fail_phase
        return AgentResult(success=success, output=f"# {phase.value}\n\nDone.", artifacts={"phase": phase.value})

    def run_delivery_room(self, mission, project, template, overwrite=False):
        from src.rooms import create_delivery_room

        return create_delivery_room(mission, project, template, True)

    def shutdown_pi_bridge(self):
        self.shutdown_called = True


def wait_for(predicate, timeout=10.0, interval=0.02):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Run each test against an isolated generated/ directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "generated").mkdir()
    return tmp_path


# --------------------------------------------------------------------- catalog


def test_every_stage_id_is_a_real_phase():
    phase_values = {phase.value for phase in DSDMPhase}
    for stage in catalog.STAGES:
        assert stage["id"] in phase_values, f"{stage['id']} is not a DSDMPhase"


def test_full_delivery_matches_the_orchestrator_phase_order():
    from src.orchestrator import DSDMOrchestrator

    assert catalog.FULL_DELIVERY_STAGE_IDS == [phase.value for phase in DSDMOrchestrator.PHASE_ORDER]


def test_oversight_levels_map_onto_agent_modes():
    from src.agents.base_agent import AgentMode

    mode_values = {mode.value for mode in AgentMode}
    assert {level["id"] for level in catalog.OVERSIGHT_LEVELS} == mode_values


def test_room_templates_match_the_room_package():
    from src.rooms.room_templates import TEMPLATE_NAMES

    assert {template["id"] for template in catalog.ROOM_TEMPLATES} == TEMPLATE_NAMES


# ------------------------------------------------------------------- workspace


def test_list_projects_reports_rooms_and_file_counts(workdir):
    project = workdir / "generated" / "acme"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "PRD.md").write_text("# PRD", encoding="utf-8")
    (project / "room_state.json").write_text(
        json.dumps({"mission": "Ship it", "template": "mvp", "status": "created", "blockers": []}),
        encoding="utf-8",
    )

    projects = workspace.list_projects()
    assert [item["name"] for item in projects] == ["acme"]
    assert projects[0]["fileCount"] == 2
    assert projects[0]["room"]["mission"] == "Ship it"


def test_reading_outside_the_workspace_is_refused(workdir):
    (workdir / "secret.txt").write_text("private", encoding="utf-8")
    (workdir / "generated" / "acme").mkdir()

    with pytest.raises(workspace.WorkspaceError):
        workspace.read_file("acme", "../../secret.txt")
    with pytest.raises(workspace.WorkspaceError):
        workspace.list_entries("acme", "../..")


def test_read_file_marks_unpreviewable_types(workdir):
    project = workdir / "generated" / "acme"
    project.mkdir()
    (project / "logo.png").write_bytes(b"\x89PNG\r\n")

    result = workspace.read_file("acme", "logo.png")
    assert result["kind"] == "binary"
    assert result["content"] == ""


def test_hidden_directories_are_skipped(workdir):
    project = workdir / "generated" / "acme"
    (project / "__pycache__").mkdir(parents=True)
    (project / "__pycache__" / "x.pyc").write_bytes(b"junk")
    (project / "README.md").write_text("hi", encoding="utf-8")

    listing = workspace.list_entries("acme")
    assert [folder["name"] for folder in listing["folders"]] == []
    assert [file["name"] for file in listing["files"]] == ["README.md"]


# -------------------------------------------------------------------- api


def test_unknown_endpoint_returns_404():
    status, payload = api.dispatch("GET", "nope", {})
    assert status == 404
    assert "error" in payload


def test_starting_a_run_requires_a_real_brief(workdir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    status, payload = api.dispatch("POST", "runs", {}, {"kind": "stage", "brief": "short"})
    assert status == 400
    assert "10 characters" in payload["error"]


def test_starting_a_run_is_blocked_until_setup_is_complete(workdir, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    status, payload = api.dispatch(
        "POST", "runs", {}, {"kind": "stage", "brief": "Build a customer portal", "stages": ["feasibility"]}
    )
    assert status == 409
    assert "Setup is incomplete" in payload["error"]


def test_unknown_stage_is_rejected(workdir, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    status, payload = api.dispatch(
        "POST", "runs", {}, {"kind": "stage", "brief": "Build a customer portal", "stages": ["not_a_stage"]}
    )
    assert status == 400
    assert "not_a_stage" in payload["error"]


def test_rooms_can_be_created_and_read_back(workdir):
    status, payload = api.dispatch(
        "POST", "rooms", {}, {"mission": "Give patients online booking", "project": "clinic", "template": "mvp"}
    )
    assert status == 201
    assert payload["project"] == "clinic"

    status, detail = api.dispatch("GET", "rooms/clinic", {})
    assert status == 200
    assert detail["status"]["mission"] == "Give patients online booking"
    assert detail["agents"], "the template should assign a team"

    status, listing = api.dispatch("GET", "rooms", {})
    assert [room["project"] for room in listing["rooms"]] == ["clinic"]


def test_missing_room_returns_404(workdir):
    status, payload = api.dispatch("GET", "rooms/nothing-here", {})
    assert status == 404
    assert "delivery room" in payload["error"]


# --------------------------------------------------------------------- runs


def test_a_stage_run_records_events_outputs_and_new_documents(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(writes="portal/docs/FEASIBILITY.md")
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)

    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"])
    assert wait_for(lambda: run.status == "completed")

    assert orchestrator.calls == [DSDMPhase.FEASIBILITY]
    assert orchestrator.shutdown_called
    assert run.stages[0]["status"] == "completed"
    assert run.outputs[0]["files"] == ["portal/docs/FEASIBILITY.md"]
    assert run.project == "portal"
    assert any(event["kind"] == "agent" for event in run.events)
    assert any("Feasibility" in event["message"] for event in run.events)


def test_a_failing_stage_stops_the_run(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(fail_phase=DSDMPhase.BUSINESS_STUDY)
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)

    run = manager.start(
        kind="delivery", brief="Build a customer portal", stage_ids=["feasibility", "business_study", "design_build"]
    )
    assert wait_for(lambda: run.status == "failed")

    assert orchestrator.calls == [DSDMPhase.FEASIBILITY, DSDMPhase.BUSINESS_STUDY]
    assert run.stages[2]["status"] == "pending"


def test_an_approval_blocks_until_the_browser_answers(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(ask_approval_in=DSDMPhase.FEASIBILITY)
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)

    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"], oversight="hybrid")
    assert wait_for(lambda: run.status == "waiting" and run.approvals)

    approval = run.approvals[0]
    assert approval.tool == "write_file"
    assert approval.payload["file_path"] == "docs/PRD.md"
    assert "Description for write_file" in approval.detail

    assert manager.respond_to_approval(run.id, approval.id, True)
    assert wait_for(lambda: run.status == "completed")
    assert orchestrator.approval_answers == [True]


def test_declining_an_approval_is_reported_to_the_agent(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(ask_approval_in=DSDMPhase.FEASIBILITY)
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)

    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"], oversight="manual")
    assert wait_for(lambda: run.approvals and run.approvals[0].status == "pending")

    manager.respond_to_approval(run.id, run.approvals[0].id, False, note="Not for production")
    assert wait_for(lambda: run.status == "completed")
    assert orchestrator.approval_answers == [False]
    assert run.approvals[0].note == "Not for production"


def test_guided_runs_ask_before_each_extra_stage(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator()
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)

    run = manager.start(
        kind="stage",
        brief="Build a customer portal",
        stage_ids=["feasibility", "business_study"],
        oversight="hybrid",
    )
    assert wait_for(lambda: run.status == "waiting" and run.approvals)

    checkpoint = run.approvals[0]
    assert "Business Study" in checkpoint.title
    manager.respond_to_approval(run.id, checkpoint.id, False)

    assert wait_for(lambda: run.status == "stopped")
    assert orchestrator.calls == [DSDMPhase.FEASIBILITY]


def test_stopping_a_queued_run_cancels_it(workdir):
    manager = RunManager()
    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"])
    run.status = "queued"
    manager.stop(run.id)
    assert run.status in ("stopped", "running", "completed", "failed")


def test_events_are_returned_after_a_cursor(workdir, monkeypatch):
    manager = RunManager()
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: FakeOrchestrator())

    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"])
    assert wait_for(lambda: run.status == "completed")

    everything = run.events_since(0)
    assert everything
    later = run.events_since(everything[0]["seq"])
    assert len(later) == len(everything) - 1


def test_run_detail_is_json_serialisable(workdir, monkeypatch):
    manager = RunManager()
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: FakeOrchestrator())
    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"])
    assert wait_for(lambda: run.status == "completed")

    encoded = api.encode(run.to_detail())
    assert json.loads(encoded)["id"] == run.id


# ---------------------------------------------------------------- rollback


def _finished_run(manager, monkeypatch, stages=("feasibility", "business_study", "prd_trd")):
    orchestrator = FakeOrchestrator(project="portal")
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)
    run = manager.start(kind="delivery", brief="Build a customer portal", stage_ids=list(stages))
    assert wait_for(lambda: run.status == "completed")
    return run, orchestrator


def _docs(workdir, project="portal"):
    folder = workdir / "generated" / project / "docs"
    return sorted(item.name for item in folder.iterdir()) if folder.is_dir() else []


def test_a_restore_point_is_taken_before_every_stage(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    assert [point.index for point in run.restore_points] == [0, 1, 2]
    assert [point.label for point in run.restore_points] == [
        "Before Feasibility",
        "Before Business Study",
        "Before Requirements",
    ]
    assert run.scope == ["portal"]


def test_restore_points_are_labelled_by_how_far_back_they_are(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    points = run.restore_point_dicts()
    assert [point["stepsBack"] for point in points] == [1, 2, 3]
    assert points[0]["undoesStages"] == ["Requirements"]
    assert points[2]["undoesStages"] == ["Feasibility", "Business Study", "Requirements"]


def test_stepping_back_removes_new_documents_and_restores_changed_ones(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)
    assert _docs(workdir) == ["BUSINESS_STUDY.md", "FEASIBILITY.md", "PRD_TRD.md", "SUMMARY.md"]

    report = manager.rollback(run.id, steps=2)

    assert _docs(workdir) == ["FEASIBILITY.md", "SUMMARY.md"]
    assert (workdir / "generated" / "portal" / "docs" / "SUMMARY.md").read_text() == "latest: feasibility"
    assert report["undoneStages"] == ["Business Study", "Requirements"]
    assert report["removeCount"] == 2
    assert report["restoreCount"] == 1
    assert report["unrecoverableCount"] == 0


def test_stepping_back_resets_the_stages_it_undid(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    manager.rollback(run.id, steps=2)

    assert run.status == "rolled_back"
    assert [(stage["id"], stage["status"]) for stage in run.stages] == [
        ("feasibility", "completed"),
        ("business_study", "pending"),
        ("prd_trd", "pending"),
    ]
    assert [output["stage"] for output in run.outputs] == ["feasibility"]
    # Only the stage that still ran can be stepped back to now.
    assert [point["stepsBack"] for point in run.restore_point_dicts()] == [1]


def test_stepping_all_the_way_back_removes_a_folder_the_run_created(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    manager.rollback(run.id, steps=3)

    assert not (workdir / "generated" / "portal").exists()


def test_stepping_back_leaves_other_projects_alone(workdir, monkeypatch):
    other = workdir / "generated" / "someone-elses-project" / "docs"
    other.mkdir(parents=True)
    (other / "NOTES.md").write_text("untouched", encoding="utf-8")

    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)
    manager.rollback(run.id, steps=3)

    assert (other / "NOTES.md").read_text() == "untouched"


def test_a_step_back_can_be_undone(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    manager.rollback(run.id, steps=2)
    manager.undo_rollback(run.id)

    assert _docs(workdir) == ["BUSINESS_STUDY.md", "FEASIBILITY.md", "PRD_TRD.md", "SUMMARY.md"]
    assert (workdir / "generated" / "portal" / "docs" / "SUMMARY.md").read_text() == "latest: prd_trd"
    assert run.status == "completed"
    assert all(stage["status"] == "completed" for stage in run.stages)
    assert [output["stage"] for output in run.outputs] == ["feasibility", "business_study", "prd_trd"]
    assert run.rollback is None


def test_undo_is_only_offered_once(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    manager.rollback(run.id, steps=1)
    manager.undo_rollback(run.id)
    with pytest.raises(RollbackError):
        manager.undo_rollback(run.id)


def test_stepping_back_too_far_is_refused(workdir, monkeypatch):
    manager = RunManager()
    run, _ = _finished_run(manager, monkeypatch)

    with pytest.raises(RollbackError):
        manager.rollback(run.id, steps=9)
    with pytest.raises(RollbackError):
        manager.rollback(run.id, steps=0)


def test_a_run_in_flight_cannot_be_stepped_back(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(project="portal", ask_approval_in=DSDMPhase.FEASIBILITY)
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)
    run = manager.start(kind="stage", brief="Build a customer portal", stage_ids=["feasibility"], oversight="manual")
    assert wait_for(lambda: run.status == "waiting")

    with pytest.raises(RollbackError):
        manager.rollback(run.id, steps=1)

    manager.respond_to_approval(run.id, run.approvals[0].id, True)
    assert wait_for(lambda: run.status == "completed")


def test_the_project_name_reaches_the_agent_as_context(workdir, monkeypatch):
    manager = RunManager()
    orchestrator = FakeOrchestrator(project="portal")
    monkeypatch.setattr(manager, "_create_orchestrator", lambda run: orchestrator)
    run = manager.start(
        kind="stage", brief="Build a customer portal", stage_ids=["feasibility"], project="portal"
    )
    assert wait_for(lambda: run.status == "completed")

    assert orchestrator.contexts == [{"project_name": "portal"}]


def test_restore_points_never_touch_paths_outside_the_workspace(workdir):
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints._safe_target("../escape")
    with pytest.raises(checkpoints.CheckpointError):
        checkpoints._safe_target("")


def test_a_restore_point_is_stored_outside_the_document_folder(workdir, monkeypatch):
    manager = RunManager()
    _finished_run(manager, monkeypatch)

    assert checkpoints.checkpoint_root().exists()
    assert workspace.generated_root() not in checkpoints.checkpoint_root().parents
    assert [item["name"] for item in workspace.list_projects()] == ["portal"]


def test_the_rollback_api_reports_what_each_step_would_change(workdir, monkeypatch):
    manager = RunManager()
    monkeypatch.setattr("src.gui.api.get_run_manager", lambda: manager)
    run, _ = _finished_run(manager, monkeypatch)

    status, payload = api.dispatch("GET", f"runs/{run.id}/restore-points", {})
    assert status == 200
    assert payload["canRollback"] is True
    assert [point["stepsBack"] for point in payload["restorePoints"]] == [1, 2, 3]
    assert payload["restorePoints"][1]["preview"]["removeCount"] == 2

    status, payload = api.dispatch("POST", f"runs/{run.id}/rollback", {}, {"steps": 2})
    assert status == 200
    assert payload["undoneStages"] == ["Business Study", "Requirements"]

    status, _ = api.dispatch("POST", f"runs/{run.id}/rollback/undo", {}, {})
    assert status == 200

    status, payload = api.dispatch("POST", f"runs/{run.id}/rollback/undo", {}, {})
    assert status == 409
    assert "nothing to undo" in payload["error"].lower()


def test_the_rollback_api_rejects_an_unknown_run(workdir):
    status, _ = api.dispatch("POST", "runs/run-9999/rollback", {}, {"steps": 1})
    assert status == 404


# -------------------------------------------------------------------- server


@pytest.fixture
def server(workdir):
    instance = create_server(host="127.0.0.1", port=0).start()
    yield instance
    instance.stop()


def fetch(server, path, headers=None, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.port}{path}", data=data, headers=headers or {}, method=method
    )
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_the_console_page_and_assets_are_served(server):
    status, body = fetch(server, "/")
    assert status == 200
    assert b"DSDM Agents Console" in body
    assert fetch(server, "/app.js")[0] == 200
    assert fetch(server, "/styles.css")[0] == 200


def test_unknown_paths_fall_back_to_the_app_shell(server):
    status, body = fetch(server, "/rooms/anything")
    assert status == 200
    assert b"<title>DSDM Agents Console</title>" in body


def test_static_paths_cannot_escape_the_asset_folder(server):
    assert fetch(server, "/../../main.py")[0] in (400, 403, 404)


def test_a_foreign_host_header_is_rejected(server):
    status, _ = fetch(server, "/api/bootstrap", headers={"Host": "attacker.example.com"})
    assert status == 403


def test_a_token_is_required_when_one_is_configured(workdir):
    instance = create_server(host="127.0.0.1", port=0, token="secret-token").start()
    try:
        assert fetch(instance, "/api/bootstrap")[0] == 401
        assert fetch(instance, "/api/bootstrap", headers={"X-Console-Token": "wrong"})[0] == 401
        assert fetch(instance, "/api/bootstrap", headers={"X-Console-Token": "secret-token"})[0] == 200
        assert fetch(instance, "/api/bootstrap?token=secret-token")[0] == 200
    finally:
        instance.stop()


def test_binding_beyond_loopback_generates_a_token():
    assert create_server(host="0.0.0.0", port=0).token
    assert create_server(host="127.0.0.1", port=0).token is None


def test_malformed_json_is_reported_cleanly(server):
    request = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/rooms",
        data=b"not json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
    assert status == 400


def test_the_static_bundle_ships_with_the_package():
    static = Path(__file__).resolve().parents[1] / "src" / "gui" / "static"
    for name in ("index.html", "app.js", "styles.css"):
        assert (static / name).is_file(), f"missing {name}"
