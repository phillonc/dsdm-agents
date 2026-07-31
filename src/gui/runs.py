"""Run manager: executes DSDM work for the console and streams it back.

The CLI runs one orchestrator in the foreground and talks to the operator over
stdin/stdout. The console needs the same work to happen in the background while
a browser watches it, so this module owns:

* a single-worker queue, so two people cannot start overlapping runs by
  accident and the captured console output stays coherent;
* an append-only event log per run, which the browser polls with a cursor;
* approvals - the GUI equivalent of the CLI's `Confirm.ask` prompt - which
  block the worker thread until someone answers in the browser or the request
  times out (an unanswered approval is declined, never auto-approved);
* a record of which files under `generated/` each stage produced.

Nothing here re-implements DSDM logic. Every run drives the same
`DSDMOrchestrator` the CLI uses.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import catalog, checkpoints

# Approvals that nobody answers are declined rather than left hanging forever.
APPROVAL_TIMEOUT_SECONDS = 900

# Events kept in memory per run. Long Design & Build runs are chatty; the cap
# keeps a browser session from being handed megabytes of history.
MAX_EVENTS_PER_RUN = 4000

MAX_CONSOLE_LINES = 2000

# Completed runs retained in memory (the console is a local, single-user tool).
MAX_RUNS = 50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStopped(Exception):
    """Raised inside an agent's progress callback to unwind a stopped run."""


class RollbackError(Exception):
    """Raised when a step-back cannot be performed, with a reason to show."""


@dataclass
class Approval:
    """A pending or answered request for human sign-off on one tool call."""

    id: str
    tool: str
    title: str
    detail: str
    payload: Dict[str, Any]
    requested_at: str = field(default_factory=_now)
    status: str = "pending"  # pending | approved | declined
    answered_at: Optional[str] = None
    note: str = ""
    event: threading.Event = field(default_factory=threading.Event, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool": self.tool,
            "title": self.title,
            "detail": self.detail,
            "payload": self.payload,
            "requestedAt": self.requested_at,
            "status": self.status,
            "answeredAt": self.answered_at,
            "note": self.note,
        }


@dataclass
class Run:
    """One unit of work started from the console."""

    id: str
    kind: str  # stage | delivery | room
    title: str
    brief: str
    stage_ids: List[str]
    oversight: str
    runtime: str
    provider: Optional[str] = None
    project: Optional[str] = None
    template: Optional[str] = None
    status: str = "queued"  # queued | running | waiting | completed | failed | stopped | rolled_back
    created_at: str = field(default_factory=_now)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    current_stage: Optional[str] = None
    error: Optional[str] = None
    summary: str = ""

    stages: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    approvals: List[Approval] = field(default_factory=list)
    console: List[str] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    # Project folders under generated/ this run has written to. Restore points
    # are scoped to these, so rolling back never touches anyone else's work.
    scope: List[str] = field(default_factory=list)
    restore_points: List[Any] = field(default_factory=list)
    rollback: Optional[Dict[str, Any]] = None  # user-facing report of the last step back
    undo_point: Optional[Any] = None  # workspace copy taken just before it
    undo_state: Optional[Dict[str, Any]] = None  # the run's own bookkeeping, to match

    _seq: int = 0
    _stop: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # -- serialisation ------------------------------------------------------

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "brief": self.brief,
            "status": self.status,
            "project": self.project,
            "oversight": self.oversight,
            "runtime": self.runtime,
            "createdAt": self.created_at,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "currentStage": self.current_stage,
            "stages": self.stages,
            "pendingApprovals": len([a for a in self.approvals if a.status == "pending"]),
            "error": self.error,
        }

    def to_detail(self) -> Dict[str, Any]:
        detail = self.to_summary()
        detail.update(
            {
                "summary": self.summary,
                "approvals": [a.to_dict() for a in self.approvals],
                "outputs": self.outputs,
                "console": self.console[-400:],
                "eventCount": self._seq,
                "scope": list(self.scope),
                "restorePoints": self.restore_point_dicts(),
                "rollback": self.rollback,
                "canUndoRollback": self.undo_point is not None,
                "canRollback": self.status not in ("queued", "running", "waiting"),
            }
        )
        return detail

    def restore_point_dicts(self) -> List[Dict[str, Any]]:
        """Restore points, newest first, each labelled with how far back it is.

        "Steps back" is counted in stages that actually ran: the newest point
        is one step back, the one before it two, and so on.
        """
        ran = [point for point in self.restore_points if self.stage_ran(point.stage_id)]
        payload = []
        for steps, point in enumerate(reversed(ran), start=1):
            item = point.to_dict(steps_back=steps)
            item["undoesStages"] = [
                catalog.stage_name(stage_id)
                for stage_id in self.stage_ids[point.index:]
                if self.stage_ran(stage_id)
            ]
            payload.append(item)
        return payload

    def stage_ran(self, stage_id: Optional[str]) -> bool:
        for stage in self.stages:
            if stage["id"] == stage_id:
                return stage["status"] in ("running", "completed", "failed")
        return False

    def note_scope(self, files: Iterable[str]) -> None:
        """Record the project folders a stage just wrote into."""
        for name in sorted(checkpoints.load_owned_from_files(files)):
            if name not in self.scope:
                self.scope.append(name)

    # -- event log ----------------------------------------------------------

    def emit(
        self,
        kind: str,
        message: str,
        *,
        level: str = "info",
        stage: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            self._seq += 1
            self.events.append(
                {
                    "seq": self._seq,
                    "at": _now(),
                    "kind": kind,
                    "level": level,
                    "message": message,
                    "stage": stage or self.current_stage,
                    "data": data or {},
                }
            )
            if len(self.events) > MAX_EVENTS_PER_RUN:
                del self.events[: len(self.events) - MAX_EVENTS_PER_RUN]

    def events_since(self, cursor: int) -> List[Dict[str, Any]]:
        with self._lock:
            return [event for event in self.events if event["seq"] > cursor]

    def write_console(self, text: str) -> None:
        with self._lock:
            for line in text.splitlines():
                self.console.append(line)
            if len(self.console) > MAX_CONSOLE_LINES:
                del self.console[: len(self.console) - MAX_CONSOLE_LINES]

    # -- lifecycle ----------------------------------------------------------

    def request_stop(self) -> None:
        self._stop = True
        for approval in self.approvals:
            if approval.status == "pending":
                approval.status = "declined"
                approval.note = "Declined automatically because the run was stopped."
                approval.answered_at = _now()
                approval.event.set()

    @property
    def stop_requested(self) -> bool:
        return self._stop

    def set_stage_status(self, stage_id: str, status: str, **extra: Any) -> None:
        for stage in self.stages:
            if stage["id"] == stage_id:
                stage["status"] = status
                stage.update(extra)
                return


class _ConsoleTee:
    """Mirror stdout into the active run so the browser can show the raw log."""

    def __init__(self, original: Any, run: Run) -> None:
        self._original = original
        self._run = run

    def write(self, text: str) -> int:
        self._run.write_console(text)
        try:
            return self._original.write(text)
        except Exception:  # pragma: no cover - stdout can vanish under a service
            return len(text)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:  # pragma: no cover
            pass

    def isatty(self) -> bool:
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class RunManager:
    """Owns every console run, past and present."""

    def __init__(self) -> None:
        self._runs: Dict[str, Run] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._counter = 0
        # Runs live in memory only, so any restore points left by a previous
        # process can never be applied. Start from a clean store.
        checkpoints.purge_all()
        self._worker = threading.Thread(target=self._worker_loop, name="dsdm-console-runs", daemon=True)
        self._worker.start()

    # -- public API ---------------------------------------------------------

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [self._runs[run_id].to_summary() for run_id in reversed(self._order)]

    def get(self, run_id: str) -> Optional[Run]:
        with self._lock:
            return self._runs.get(run_id)

    def active_run(self) -> Optional[Run]:
        with self._lock:
            for run_id in reversed(self._order):
                run = self._runs[run_id]
                if run.status in ("queued", "running", "waiting"):
                    return run
        return None

    def start(
        self,
        *,
        kind: str,
        brief: str,
        stage_ids: List[str],
        oversight: str = "automated",
        runtime: str = "legacy",
        provider: Optional[str] = None,
        project: Optional[str] = None,
        template: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Run:
        """Queue a run. Returns immediately; work happens on the worker thread."""
        with self._lock:
            self._counter += 1
            run_id = f"run-{self._counter:04d}"
            run = Run(
                id=run_id,
                kind=kind,
                title=title or self._default_title(kind, stage_ids),
                brief=brief.strip(),
                stage_ids=list(stage_ids),
                oversight=oversight,
                runtime=runtime,
                provider=provider,
                project=project,
                template=template,
            )
            run.stages = [
                {
                    "id": stage_id,
                    "name": catalog.stage_name(stage_id),
                    "status": "pending",
                    "startedAt": None,
                    "finishedAt": None,
                    "fileCount": 0,
                }
                for stage_id in stage_ids
            ]
            if run.project:
                run.scope.append(run.project)
            self._runs[run_id] = run
            self._order.append(run_id)
            self._trim_locked()

        run.emit("run", "Queued and waiting to start.")
        self._queue.put(run_id)
        return run

    def respond_to_approval(self, run_id: str, approval_id: str, approved: bool, note: str = "") -> bool:
        run = self.get(run_id)
        if not run:
            return False
        for approval in run.approvals:
            if approval.id == approval_id and approval.status == "pending":
                approval.status = "approved" if approved else "declined"
                approval.note = note
                approval.answered_at = _now()
                approval.event.set()
                run.emit(
                    "approval",
                    f"{'Approved' if approved else 'Declined'}: {approval.title}",
                    level="info" if approved else "warn",
                    data={"approvalId": approval.id, "status": approval.status},
                )
                return True
        return False

    def stop(self, run_id: str) -> bool:
        run = self.get(run_id)
        if not run or run.status in ("completed", "failed", "stopped"):
            return False
        run.request_stop()
        run.emit("run", "Stop requested. The step in progress will finish first.", level="warn")
        if run.status == "queued":
            run.status = "stopped"
            run.finished_at = _now()
            run.emit("run", "Run cancelled before it started.", level="warn")
        return True

    def rollback(self, run_id: str, steps: Optional[int] = None, checkpoint_id: Optional[str] = None):
        """Step the workspace back to an earlier restore point.

        Either `steps` (1 = undo the most recent stage) or an explicit
        `checkpoint_id`. The run must not be in flight: rolling files back
        underneath a working agent would corrupt both.
        """
        run = self.get(run_id)
        if run is None:
            raise LookupError("That run no longer exists.")
        if run.status in ("queued", "running", "waiting"):
            raise RollbackError("Stop the run before stepping back.")

        point = self._resolve_restore_point(run, steps, checkpoint_id)
        if point.skipped:
            raise RollbackError(point.reason or "No copy was kept for that point.")

        # A safety copy of the current state, so one level of undo is possible.
        run.undo_point = checkpoints.create(
            run.id, -1, "Before stepping back", None, run.scope
        )

        try:
            report = checkpoints.restore(point, run.scope)
        except checkpoints.CheckpointError as exc:
            run.undo_point = None
            raise RollbackError(str(exc)) from exc

        undone = self._reset_stages_from(run, point)
        report.update({"toLabel": point.label, "undoneStages": undone, "steps": len(undone)})
        run.rollback = report
        run.status = "rolled_back"
        run.summary = (
            f"Stepped back {len(undone)} stage(s) to \"{point.label.lower()}\"."
            if undone
            else f"Stepped back to \"{point.label.lower()}\"."
        )
        run.emit(
            "rollback",
            f"Stepped back to {point.label.lower()} - "
            f"{report['removeCount']} document(s) removed, {report['restoreCount']} restored.",
            level="warn",
            data={"checkpointId": point.id, "undoneStages": undone},
        )
        if report["unrecoverableCount"]:
            run.emit(
                "rollback",
                f"{report['unrecoverableCount']} file(s) changed outside this run's project "
                "folders and were left as they are.",
                level="warn",
            )
        return report

    def undo_rollback(self, run_id: str):
        """Put back the state that the most recent step-back replaced."""
        run = self.get(run_id)
        if run is None:
            raise LookupError("That run no longer exists.")
        if run.undo_point is None:
            raise RollbackError("There is nothing to undo.")
        if run.status in ("queued", "running", "waiting"):
            raise RollbackError("Stop the run before undoing a step back.")

        try:
            report = checkpoints.restore(run.undo_point, run.scope)
        except checkpoints.CheckpointError as exc:
            raise RollbackError(str(exc)) from exc

        state = run.undo_state or {}
        for stage in run.stages:
            saved = state.get("stages", {}).get(stage["id"])
            if saved:
                stage.update(saved)
        run.outputs = state.get("outputs", run.outputs)
        run.status = state.get("status", "completed")
        run.summary = "The step back was undone; the documents are as they were."
        run.rollback = None
        run.undo_point = None
        run.undo_state = None
        run.emit("rollback", "Step back undone - the documents are back as they were.")
        return report

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _resolve_restore_point(run: Run, steps: Optional[int], checkpoint_id: Optional[str]):
        available = [point for point in run.restore_points if run.stage_ran(point.stage_id)]
        if not available:
            raise RollbackError("This run has no restore points to step back to.")
        if checkpoint_id:
            for point in available:
                if point.id == checkpoint_id:
                    return point
            raise RollbackError("That restore point is no longer available.")
        if steps is None:
            steps = 1
        if steps < 1 or steps > len(available):
            raise RollbackError(
                f"Choose between 1 and {len(available)} step(s) back."
            )
        return available[len(available) - steps]

    @staticmethod
    def _reset_stages_from(run: Run, point) -> List[str]:
        """Mark the rolled-back stages pending again and drop their outputs."""
        rolled_back_ids = run.stage_ids[point.index:]
        undone = [
            catalog.stage_name(stage["id"])
            for stage in run.stages
            if stage["id"] in rolled_back_ids and stage["status"] != "pending"
        ]
        # Kept so undo_rollback can put the run's own bookkeeping back too.
        run.undo_state = {
            "stages": {stage["id"]: dict(stage) for stage in run.stages},
            "outputs": list(run.outputs),
            "status": run.status,
        }

        for stage in run.stages:
            if stage["id"] in rolled_back_ids:
                stage.update({"status": "pending", "startedAt": None, "finishedAt": None, "fileCount": 0})
        run.outputs = [output for output in run.outputs if output["stage"] not in rolled_back_ids]
        run.current_stage = None
        return undone

    @staticmethod
    def _default_title(kind: str, stage_ids: List[str]) -> str:
        if kind == "delivery":
            return "Full delivery"
        if kind == "room":
            return "Delivery room"
        if not stage_ids:
            return "Delivery"
        if len(stage_ids) <= 3:
            names = [catalog.stage_name(stage_id) for stage_id in stage_ids]
            return " + ".join(names)
        return f"{len(stage_ids)} stages"

    def _trim_locked(self) -> None:
        while len(self._order) > MAX_RUNS:
            oldest = self._order[0]
            run = self._runs.get(oldest)
            if run and run.status in ("queued", "running", "waiting"):
                break
            self._order.pop(0)
            self._runs.pop(oldest, None)
            checkpoints.discard_run(oldest)

    def _worker_loop(self) -> None:  # pragma: no cover - exercised via integration use
        while True:
            run_id = self._queue.get()
            run = self.get(run_id)
            if run is None or run.status == "stopped":
                self._queue.task_done()
                continue
            try:
                self._execute(run)
            except Exception:
                run.status = "failed"
                run.error = traceback.format_exc(limit=4)
                run.finished_at = _now()
                run.emit("error", "The run stopped unexpectedly.", level="error", data={"detail": run.error})
            finally:
                self._queue.task_done()

    # -- execution ----------------------------------------------------------

    def _execute(self, run: Run) -> None:
        run.status = "running"
        run.started_at = _now()
        run.emit("run", f"Starting {run.title.lower()}.")

        original_stdout = sys.stdout
        previous_env = {
            "LLM_PROVIDER": os.environ.get("LLM_PROVIDER"),
            "AGENT_RUNTIME": os.environ.get("AGENT_RUNTIME"),
        }
        if run.provider:
            os.environ["LLM_PROVIDER"] = run.provider
        os.environ["AGENT_RUNTIME"] = run.runtime

        orchestrator = None
        sys.stdout = _ConsoleTee(original_stdout, run)
        try:
            orchestrator = self._build_orchestrator(run)
            if run.kind == "room":
                self._execute_room(run, orchestrator)
            else:
                self._execute_stages(run, orchestrator)
        except RunStopped:
            run.status = "stopped"
            run.summary = "Stopped at your request."
            run.emit("run", "Run stopped.", level="warn")
        except Exception as exc:
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}"
            run.summary = "The run could not be completed."
            run.emit("error", self._humanise_error(exc), level="error", data={"detail": run.error})
        finally:
            sys.stdout = original_stdout
            if orchestrator is not None:
                try:
                    orchestrator.shutdown_pi_bridge()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            if run.status in ("running", "waiting"):
                run.status = "completed"
            run.finished_at = _now()
            run.current_stage = None
            run.emit("run", f"Run {run.status}.", level="info" if run.status == "completed" else "warn")

    def _build_orchestrator(self, run: Run):
        """Build a `DSDMOrchestrator` and point its callbacks at this run."""
        orchestrator = self._create_orchestrator(run)
        progress = self._make_progress_callback(run)
        approval = self._make_approval_callback(run, orchestrator)
        for agent in list(orchestrator.agents.values()) + list(orchestrator.design_build_agents.values()):
            agent.set_progress_callback(progress)
            agent.approval_callback = approval
        return orchestrator

    def _create_orchestrator(self, run: Run):
        """Construct the orchestrator the CLI would build for these settings.

        Imported lazily so the console still starts (and can show the setup
        page) on a machine where the agent dependencies are not installed yet.
        """
        from ..agents import (
            BusinessStudyAgent,
            DesignBuildAgent,
            FeasibilityAgent,
            FunctionalModelAgent,
            ImplementationAgent,
            ProductManagerAgent,
        )
        from ..agents.base_agent import AgentMode
        from ..agents.devops_agent import DevOpsAgent
        from ..orchestrator import DSDMOrchestrator, DSDMPhase, OrchestratorConfig, PhaseConfig

        mode = AgentMode(run.oversight)
        # Implementation and DevOps deliberately keep the stricter default the
        # CLI uses when the operator asked for "hands-off": deployment and
        # pipeline changes are the two places where silent automation hurts.
        implementation_mode = AgentMode.MANUAL if run.oversight == "automated" else mode
        devops_mode = AgentMode.HYBRID if run.oversight == "automated" else mode

        config = OrchestratorConfig(
            phases=[
                PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, mode),
                PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, mode),
                PhaseConfig(DSDMPhase.PRD_TRD, ProductManagerAgent, mode),
                PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, mode),
                PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, mode),
                PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, implementation_mode),
                PhaseConfig(DSDMPhase.DEVOPS, DevOpsAgent, devops_mode),
            ],
            # Never interactive: the orchestrator's own prompts read stdin, which
            # no browser can answer. Approvals are re-attached below instead.
            interactive=False,
            auto_advance=False,
        )
        orchestrator = DSDMOrchestrator(
            config,
            include_devops=True,
            include_jira=False,
            include_confluence=False,
            agent_runtime=run.runtime,
        )

        return orchestrator

    def _execute_stages(self, run: Run, orchestrator) -> None:
        from ..orchestrator import DSDMPhase

        completed = 0
        for index, stage_id in enumerate(run.stage_ids):
            if run.stop_requested:
                raise RunStopped()

            if index > 0 and run.oversight != "automated":
                if not self._checkpoint(run, stage_id):
                    run.status = "stopped"
                    run.summary = f"Stopped before {catalog.stage_name(stage_id)} at your request."
                    run.emit("run", "Remaining stages skipped.", level="warn")
                    return

            run.current_stage = stage_id
            self._take_restore_point(run, index, stage_id)
            run.set_stage_status(stage_id, "running", startedAt=_now())
            run.emit("stage", f"{catalog.stage_name(stage_id)} started.", stage=stage_id)

            before = _snapshot_generated()
            # The project name is passed as context so the agent writes into the
            # folder the operator named in the console, rather than inventing one.
            context = {"project_name": run.project} if run.project else None
            result = orchestrator.run_phase(DSDMPhase(stage_id), run.brief, context)
            new_files = _new_files(before)
            run.note_scope(new_files)

            run.set_stage_status(
                stage_id,
                "completed" if result.success else "failed",
                finishedAt=_now(),
                fileCount=len(new_files),
            )
            run.outputs.append(
                {
                    "stage": stage_id,
                    "stageName": catalog.stage_name(stage_id),
                    "success": bool(result.success),
                    "output": (result.output or "")[:20000],
                    "artifacts": _jsonable(result.artifacts or {}),
                    "files": new_files,
                }
            )
            if new_files and run.project is None:
                run.project = new_files[0].split("/")[0]

            if result.success:
                completed += 1
                run.emit(
                    "stage",
                    f"{catalog.stage_name(stage_id)} finished - {len(new_files)} document(s) produced.",
                    stage=stage_id,
                    data={"files": new_files},
                )
            else:
                run.status = "failed"
                run.summary = f"{catalog.stage_name(stage_id)} did not complete."
                run.emit("stage", f"{catalog.stage_name(stage_id)} did not complete.", level="error", stage=stage_id)
                return

        run.status = "completed"
        run.summary = (
            f"{completed} of {len(run.stage_ids)} stage(s) completed."
            if len(run.stage_ids) > 1
            else f"{catalog.stage_name(run.stage_ids[0])} completed."
        )

    def _take_restore_point(self, run: Run, index: int, stage_id: str) -> None:
        """Save the workspace before `stage_id` runs, so it can be undone."""
        label = f"Before {catalog.stage_name(stage_id)}"
        try:
            point = checkpoints.create(run.id, index, label, stage_id, run.scope)
        except Exception as exc:  # a failed restore point must not fail the run
            run.emit("run", f"Could not save a restore point: {exc}", level="warn")
            return
        run.restore_points.append(point)
        if point.skipped:
            run.emit("run", f"Restore point skipped - {point.reason}", level="warn")

    def _execute_room(self, run: Run, orchestrator) -> None:
        from ..rooms import export_delivery_room, get_delivery_room_status

        run.emit("run", "Setting up the delivery room.")
        room = orchestrator.run_delivery_room(
            run.brief,
            run.project,
            run.template or "mvp",
            overwrite=True,
        )
        run.project = room.project_name
        export_path = export_delivery_room(room.project_name)
        status = get_delivery_room_status(room.project_name)
        run.status = "completed"
        run.summary = (
            f"Delivery room '{room.project_name}' is at "
            f"{status.get('health', {}).get('overall', 0)}/100 health."
        )
        run.outputs.append(
            {
                "stage": "delivery_room",
                "stageName": "Delivery room",
                "success": True,
                "output": f"Dashboard exported to {export_path}",
                "artifacts": _jsonable(status),
                "files": [],
            }
        )
        run.emit("run", f"Delivery room ready: {room.project_name}.", data={"project": room.project_name})

    # -- callbacks ----------------------------------------------------------

    def _make_progress_callback(self, run: Run):
        def callback(info) -> None:
            if run.stop_requested:
                raise RunStopped()
            event = getattr(info.event, "value", str(info.event))
            label = catalog.EVENT_LABELS.get(event, event.replace("_", " ").title())
            data: Dict[str, Any] = {"event": event, "agent": info.agent_name, "label": label}
            if info.iteration:
                data["iteration"] = info.iteration
                data["maxIterations"] = info.max_iterations
            if info.tool_name:
                data["tool"] = info.tool_name
            level = "error" if event == "error" else "info"
            run.emit("agent", info.message, level=level, data=data)

        return callback

    def _make_approval_callback(self, run: Run, orchestrator):
        def callback(tool_name: str, tool_input: Dict[str, Any]) -> bool:
            if run.stop_requested:
                return False

            tool = orchestrator.tool_registry.get(tool_name)
            detail = tool.description if tool else "No description available for this action."
            approval = Approval(
                id=f"{run.id}-approval-{len(run.approvals) + 1}",
                tool=tool_name,
                title=_friendly_tool_title(tool_name),
                detail=detail,
                payload=_trim_payload(tool_input),
            )
            run.approvals.append(approval)
            previous_status = run.status
            run.status = "waiting"
            run.emit(
                "approval",
                f"Approval needed: {approval.title}",
                level="warn",
                data={"approvalId": approval.id},
            )

            answered = approval.event.wait(timeout=APPROVAL_TIMEOUT_SECONDS)
            if not answered and approval.status == "pending":
                approval.status = "declined"
                approval.note = "No response within 15 minutes, so the action was declined."
                approval.answered_at = _now()
                run.emit("approval", f"Approval timed out: {approval.title}", level="warn")

            run.status = previous_status if previous_status != "waiting" else "running"
            return approval.status == "approved"

        return callback

    def _checkpoint(self, run: Run, next_stage_id: str) -> bool:
        """Ask the browser for permission to move on to the next stage."""
        approval = Approval(
            id=f"{run.id}-checkpoint-{len(run.approvals) + 1}",
            tool="stage_checkpoint",
            title=f"Continue to {catalog.stage_name(next_stage_id)}?",
            detail=(
                catalog.stage_by_id(next_stage_id) or {}
            ).get("summary", "Continue with the next stage of delivery."),
            payload={"stage": next_stage_id},
        )
        run.approvals.append(approval)
        run.status = "waiting"
        run.emit(
            "approval",
            f"Waiting for you to continue to {catalog.stage_name(next_stage_id)}.",
            level="warn",
            data={"approvalId": approval.id},
        )
        answered = approval.event.wait(timeout=APPROVAL_TIMEOUT_SECONDS)
        if not answered and approval.status == "pending":
            approval.status = "declined"
            approval.note = "No response within 15 minutes, so the run was paused."
            approval.answered_at = _now()
        run.status = "running"
        return approval.status == "approved"

    @staticmethod
    def _humanise_error(exc: Exception) -> str:
        text = str(exc)
        lowered = text.lower()
        if "api_key" in lowered or "api key" in lowered:
            return "The AI provider rejected the request - check the API key on the Setup page."
        if "connection" in lowered or "timed out" in lowered:
            return "Could not reach the AI provider. Check the network connection and try again."
        return f"The run could not be completed: {text}"


# --- helpers ---------------------------------------------------------------


def _friendly_tool_title(tool_name: str) -> str:
    return tool_name.replace("_", " ").capitalize()


def _trim_payload(payload: Dict[str, Any], limit: int = 1200) -> Dict[str, Any]:
    trimmed: Dict[str, Any] = {}
    for key, value in (payload or {}).items():
        text = value if isinstance(value, str) else repr(value)
        trimmed[key] = text if len(text) <= limit else f"{text[:limit]}... [truncated]"
    return trimmed


def _jsonable(value: Any) -> Any:
    """Coerce agent artefacts into something `json.dumps` will accept."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _snapshot_generated() -> Dict[str, float]:
    root = Path("generated")
    if not root.exists():
        return {}
    snapshot: Dict[str, float] = {}
    for item in root.rglob("*"):
        if item.is_file():
            try:
                snapshot[str(item.relative_to(root))] = item.stat().st_mtime
            except OSError:
                continue
    return snapshot


def _new_files(before: Dict[str, float], limit: int = 60) -> List[str]:
    """Return files under generated/ that appeared or changed since `before`."""
    after = _snapshot_generated()
    changed = [path for path, mtime in after.items() if before.get(path) != mtime]
    changed.sort()
    return changed[:limit]


_manager: Optional[RunManager] = None
_manager_lock = threading.Lock()


def get_run_manager() -> RunManager:
    """Return the process-wide run manager, creating it on first use."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = RunManager()
    return _manager
