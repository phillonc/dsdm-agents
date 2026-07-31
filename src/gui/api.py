"""JSON API behind the console UI.

Handlers are plain functions returning `(status_code, payload)` so they can be
unit-tested without starting a server (see tests/test_gui.py). `dispatch` owns
the routing table; `server.py` only deals with HTTP mechanics.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import catalog, diagnostics, workspace
from .runs import get_run_manager

Response = Tuple[int, Dict[str, Any]]

VALID_KINDS = {"stage", "delivery", "room"}


class ApiError(Exception):
    """A handler-level failure that should become a clean JSON error."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# --- bootstrap / diagnostics ------------------------------------------------


def get_bootstrap(_query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    manager = get_run_manager()
    projects = workspace.list_projects()
    return 200, {
        "catalog": catalog.catalog(),
        "readiness": diagnostics.readiness(),
        "defaults": {
            "provider": diagnostics.default_provider(),
            "runtime": diagnostics.default_runtime(),
            "oversight": "automated",
            "template": "mvp",
        },
        "counts": {
            "projects": len(projects),
            "rooms": len([p for p in projects if p.get("room")]),
            "activeRuns": len([r for r in manager.list_runs() if r["status"] in ("queued", "running", "waiting")]),
        },
    }


def get_readiness(_query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    return 200, diagnostics.readiness()


# --- projects & documents ---------------------------------------------------


def get_projects(_query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    return 200, {"projects": workspace.list_projects(), "recent": workspace.recent_artifacts()}


def get_project_files(project: str, query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    try:
        return 200, workspace.list_entries(project, query.get("path", ""))
    except workspace.WorkspaceError as exc:
        raise ApiError(str(exc), 404) from exc


def get_project_file(project: str, query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    path = query.get("path")
    if not path:
        raise ApiError("A file path is required.")
    try:
        return 200, workspace.read_file(project, path)
    except workspace.WorkspaceError as exc:
        raise ApiError(str(exc), 404) from exc


# --- runs -------------------------------------------------------------------


def get_runs(_query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    return 200, {"runs": get_run_manager().list_runs()}


def post_runs(_query: Dict[str, str], body: Dict[str, Any]) -> Response:
    kind = str(body.get("kind") or "stage")
    if kind not in VALID_KINDS:
        raise ApiError(f"Unknown run type '{kind}'.")

    brief = str(body.get("brief") or "").strip()
    if len(brief) < 10:
        raise ApiError("Describe what you want to deliver in at least 10 characters.")

    oversight = str(body.get("oversight") or "automated")
    if oversight not in {level["id"] for level in catalog.OVERSIGHT_LEVELS}:
        raise ApiError(f"Unknown oversight level '{oversight}'.")

    runtime = str(body.get("runtime") or diagnostics.default_runtime())
    if runtime not in {item["id"] for item in catalog.RUNTIMES}:
        raise ApiError(f"Unknown execution engine '{runtime}'.")

    provider = body.get("provider") or None
    if provider and provider not in {item["id"] for item in catalog.PROVIDERS}:
        raise ApiError(f"Unknown AI provider '{provider}'.")

    if kind == "room":
        stage_ids: List[str] = []
    elif kind == "delivery":
        stage_ids = list(catalog.FULL_DELIVERY_STAGE_IDS)
    else:
        stage_ids = [str(item) for item in (body.get("stages") or [])]
        if not stage_ids:
            raise ApiError("Choose at least one stage to run.")
        unknown = [stage for stage in stage_ids if stage not in catalog.STAGE_IDS]
        if unknown:
            raise ApiError(f"Unknown stage(s): {', '.join(unknown)}.")

    readiness = diagnostics.readiness()
    if not readiness["ready"]:
        blocking = [check["label"] for check in readiness["checks"] if check["status"] == "error"]
        raise ApiError(
            "Setup is incomplete: " + ", ".join(blocking) + ". Open the Setup page for the fix.",
            409,
        )

    template = body.get("template") or "mvp"
    if template not in {item["id"] for item in catalog.ROOM_TEMPLATES}:
        raise ApiError(f"Unknown delivery template '{template}'.")

    run = get_run_manager().start(
        kind=kind,
        brief=brief,
        stage_ids=stage_ids,
        oversight=oversight,
        runtime=runtime,
        provider=provider,
        project=(str(body["project"]).strip() or None) if body.get("project") else None,
        template=template,
        title=(str(body["title"]).strip() or None) if body.get("title") else None,
    )
    return 201, run.to_detail()


def get_run(run_id: str, _query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    run = get_run_manager().get(run_id)
    if not run:
        raise ApiError("That run no longer exists.", 404)
    return 200, run.to_detail()


def get_run_events(run_id: str, query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    run = get_run_manager().get(run_id)
    if not run:
        raise ApiError("That run no longer exists.", 404)
    try:
        cursor = int(query.get("cursor", "0"))
    except ValueError:
        cursor = 0
    events = run.events_since(cursor)
    return 200, {
        "runId": run.id,
        "status": run.status,
        "cursor": events[-1]["seq"] if events else cursor,
        "events": events,
        "run": run.to_summary(),
        "approvals": [a.to_dict() for a in run.approvals if a.status == "pending"],
    }


def post_run_approval(run_id: str, approval_id: str, _query: Dict[str, str], body: Dict[str, Any]) -> Response:
    approved = bool(body.get("approved"))
    note = str(body.get("note") or "")
    if not get_run_manager().respond_to_approval(run_id, approval_id, approved, note):
        raise ApiError("That approval has already been answered.", 409)
    return 200, {"ok": True}


def post_run_stop(run_id: str, _query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    if not get_run_manager().stop(run_id):
        raise ApiError("That run has already finished.", 409)
    return 200, {"ok": True}


# --- delivery rooms ---------------------------------------------------------


def get_rooms(_query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    rooms = []
    for project in workspace.list_projects():
        room = project.get("room")
        if room:
            rooms.append({"project": project["name"], **room})
    return 200, {"rooms": rooms}


def get_room(project: str, _query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    from ..rooms import get_delivery_room_status, load_delivery_room

    try:
        status = get_delivery_room_status(project)
        room = load_delivery_room(project)
    except FileNotFoundError as exc:
        raise ApiError("No delivery room exists for that project.", 404) from exc

    return 200, {
        "status": status,
        "kickoff": room.kickoff.__dict__,
        "agents": [agent.__dict__ for agent in room.agents],
        "blockers": [blocker.__dict__ for blocker in room.blockers],
        "decisions": [decision.__dict__ for decision in room.decisions],
        "handoffs": [handoff.__dict__ for handoff in room.handoffs],
        "artifacts": [artifact.__dict__ for artifact in room.artifacts],
    }


def post_rooms(_query: Dict[str, str], body: Dict[str, Any]) -> Response:
    """Create a delivery room. No AI provider is needed for this."""
    from ..rooms import create_delivery_room, export_delivery_room

    mission = str(body.get("mission") or "").strip()
    if len(mission) < 10:
        raise ApiError("Describe the mission in at least 10 characters.")

    template = str(body.get("template") or "mvp")
    if template not in {item["id"] for item in catalog.ROOM_TEMPLATES}:
        raise ApiError(f"Unknown delivery template '{template}'.")

    project = str(body.get("project") or "").strip() or None
    overwrite = bool(body.get("overwrite"))
    try:
        room = create_delivery_room(mission, project, template, overwrite)
    except FileExistsError as exc:
        raise ApiError("A delivery room already exists for that project name.", 409) from exc
    export_delivery_room(room.project_name)
    return 201, {"project": room.project_name}


def post_room_export(project: str, _query: Dict[str, str], _body: Dict[str, Any]) -> Response:
    from ..rooms import export_delivery_room

    try:
        path = export_delivery_room(project)
    except FileNotFoundError as exc:
        raise ApiError("No delivery room exists for that project.", 404) from exc
    return 200, {"path": str(path)}


# --- routing ----------------------------------------------------------------

# (method, path segments) -> handler. A segment written as "*" matches anything
# and is passed to the handler as a positional argument.
ROUTES: List[Tuple[str, List[str], Callable[..., Response]]] = [
    ("GET", ["bootstrap"], get_bootstrap),
    ("GET", ["readiness"], get_readiness),
    ("GET", ["projects"], get_projects),
    ("GET", ["projects", "*", "files"], get_project_files),
    ("GET", ["projects", "*", "file"], get_project_file),
    ("GET", ["runs"], get_runs),
    ("POST", ["runs"], post_runs),
    ("GET", ["runs", "*"], get_run),
    ("GET", ["runs", "*", "events"], get_run_events),
    ("POST", ["runs", "*", "approvals", "*"], post_run_approval),
    ("POST", ["runs", "*", "stop"], post_run_stop),
    ("GET", ["rooms"], get_rooms),
    ("POST", ["rooms"], post_rooms),
    ("GET", ["rooms", "*"], get_room),
    ("POST", ["rooms", "*", "export"], post_room_export),
]


def dispatch(method: str, path: str, query: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> Response:
    """Route an API request. `path` is everything after `/api/`."""
    segments = [segment for segment in path.strip("/").split("/") if segment]
    for route_method, pattern, handler in ROUTES:
        if route_method != method or len(pattern) != len(segments):
            continue
        args: List[str] = []
        matched = True
        for expected, actual in zip(pattern, segments):
            if expected == "*":
                args.append(actual)
            elif expected != actual:
                matched = False
                break
        if not matched:
            continue
        try:
            return handler(*args, query, body or {})
        except ApiError as exc:
            return exc.status, {"error": exc.message}
        except FileNotFoundError as exc:
            return 404, {"error": str(exc)}
        except Exception as exc:  # pragma: no cover - defensive
            return 500, {"error": f"{type(exc).__name__}: {exc}"}

    return 404, {"error": f"No such endpoint: {method} /api/{path}"}


def encode(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, default=str).encode("utf-8")
