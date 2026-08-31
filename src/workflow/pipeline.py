"""The end-to-end Requirement → PRD → TRD → TASKS run.

``run_workflow`` is the entry point the orchestrator and the DSDM tool registry
call. It builds all three documents *before* writing any of them, so a gate
failure leaves the output directory untouched rather than half-written
(spec §8).

All output lands under ``generated/`` — the project output folder every agent
in this repository writes to.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from .documents import (
    PRD_FILENAME,
    TASKS_FILENAME,
    TRD_FILENAME,
    render_prd,
    render_tasks,
    render_trd,
)
from .intake import normalise_requirement, requirement_from_file
from .model import PRD, RawRequirement, Requirement, TRD, TaskPlan, slugify
from .stages import GateError, build_prd, build_task_plan, build_trd

#: Every agent in this repository writes under ``generated/`` (spec §8).
GENERATED_ROOT = "generated"
DOCS_SUBDIR = "docs"


def document_directory(
    requirement_slug: str,
    project: Optional[str] = None,
    output_root: Optional[str] = None,
) -> str:
    """Where a requirement's three documents belong.

    * ``output_root`` given  -> ``<output_root>/<requirement-slug>/``
    * ``project`` given      -> ``generated/<project>/docs/<requirement-slug>/``
    * neither                -> ``generated/<requirement-slug>/docs/``

    The last case is the common one: a requirement inputted on its own *is* the
    project, so nesting its slug twice would only add noise.
    """
    if output_root:
        return os.path.join(output_root, requirement_slug)
    if project:
        return os.path.join(GENERATED_ROOT, slugify(project), DOCS_SUBDIR, requirement_slug)
    return os.path.join(GENERATED_ROOT, requirement_slug, DOCS_SUBDIR)


@dataclass
class WorkflowResult:
    """Everything one run produced."""

    requirement: Requirement
    prd: PRD
    trd: TRD
    plan: TaskPlan
    documents: Dict[str, str] = field(default_factory=dict)
    output_dir: Optional[str] = None

    @property
    def written(self) -> Dict[str, str]:
        """Filename → path on disk, empty when the run did not write."""
        if not self.output_dir:
            return {}
        return {name: os.path.join(self.output_dir, name) for name in self.documents}

    def summary(self) -> Dict[str, object]:
        """A compact, JSON-friendly view of the run."""
        assignments = self.plan.assignments()
        return {
            "requirement": self.requirement.title,
            "slug": self.requirement.slug,
            "functional_requirements": len(self.prd.functional),
            "components": len(self.trd.components),
            "tasks": len(self.plan.tasks),
            "agents": {agent: entry["task_count"] for agent, entry in assignments.items()},
            "documents": self.written or list(self.documents),
        }


def run_workflow(
    requirement: RawRequirement,
    project: Optional[str] = None,
    output_root: Optional[str] = None,
    lane_agents: Optional[Dict[str, str]] = None,
    write: bool = True,
) -> WorkflowResult:
    """Run all four stages over ``requirement``.

    ``project`` names the folder under ``generated/`` the documents belong to;
    ``output_root`` overrides the location outright. Pass ``write=False`` to
    render without touching the filesystem — useful in tests and when the
    caller wants to place the output itself.
    """
    normalised = normalise_requirement(requirement)
    prd = build_prd(normalised)
    trd = build_trd(prd)
    plan = build_task_plan(prd, trd, lane_agents=lane_agents)

    documents = {
        PRD_FILENAME: render_prd(prd),
        TRD_FILENAME: render_trd(trd, prd),
        TASKS_FILENAME: render_tasks(plan, trd),
    }

    output_dir: Optional[str] = None
    if write:
        output_dir = document_directory(normalised.slug, project=project, output_root=output_root)
        os.makedirs(output_dir, exist_ok=True)
        for name, body in documents.items():
            with open(os.path.join(output_dir, name), "w", encoding="utf-8") as handle:
                handle.write(body)

    return WorkflowResult(
        requirement=normalised,
        prd=prd,
        trd=trd,
        plan=plan,
        documents=documents,
        output_dir=output_dir,
    )


def run_workflow_from_file(
    path: str,
    project: Optional[str] = None,
    output_root: Optional[str] = None,
    lane_agents: Optional[Dict[str, str]] = None,
    write: bool = True,
) -> WorkflowResult:
    """Read a markdown/text requirement from ``path`` and run the workflow."""
    return run_workflow(
        requirement_from_file(path),
        project=project,
        output_root=output_root,
        lane_agents=lane_agents,
        write=write,
    )


__all__ = [
    "GENERATED_ROOT",
    "DOCS_SUBDIR",
    "document_directory",
    "GateError",
    "WorkflowResult",
    "run_workflow",
    "run_workflow_from_file",
]
