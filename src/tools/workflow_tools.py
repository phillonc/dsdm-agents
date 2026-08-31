"""Requirement workflow tools — PRD, TRD, Definition of Done and per-agent TASKS.

These register the deterministic Requirement → PRD → TRD → TASKS pipeline
(:mod:`src.workflow`) with the DSDM tool registry, so an agent can run it the
same way it runs any other tool.

They sit alongside ``generate_product_requirements_document`` and
``generate_technical_requirements_document`` rather than replacing them: those
tools help an agent *structure its thinking* before it writes narrative
documents, while these produce the three deliverables the workflow spec
guarantees — including ``DEFINITION-OF-DONE.md``, which says what good looks
like for each feature, and ``TASKS.md``, which gives every agent its own task
list measured against it.

Parameter names avoid ``ToolRegistry.PARAMETER_ALIASES`` (``project``, ``name``,
``text``, ``path``, …), which would otherwise be rewritten before the handler
sees them.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..workflow import (
    LANE_ORDER,
    LANE_ROLE_IDS,
    LANE_TITLES,
    PERSPECTIVE_TITLES,
    SPEC_ID,
    SPEC_VERSION,
)
from ..workflow.pipeline import run_workflow
from .tool_registry import Tool, ToolRegistry


def _assignments(result) -> Dict[str, Any]:
    """Per-agent view of a run: who owns what, and why.

    Built on ``TaskPlan.assignments()``, which merges the lanes a single agent
    owns — several roles here cover more than one lane.
    """
    plan = result.plan
    by_id = {task.id: task for task in plan.tasks}
    detailed: Dict[str, Any] = {}
    for agent, entry in plan.assignments().items():
        detailed[agent] = {
            "lanes": [LANE_TITLES[lane] for lane in entry["lanes"]],
            "role_ids": list(dict.fromkeys(LANE_ROLE_IDS[lane] for lane in entry["lanes"] if lane in LANE_ROLE_IDS)),
            "task_count": entry["task_count"],
            "tasks": [
                {
                    "id": task_id,
                    "title": by_id[task_id].title,
                    "priority": by_id[task_id].priority,
                    "effort": by_id[task_id].effort,
                    "traces_to": (
                        list(by_id[task_id].traces_prd)
                        + list(by_id[task_id].traces_trd)
                        + list(by_id[task_id].traces_dod)
                    ),
                    "depends_on": list(by_id[task_id].depends_on),
                }
                for task_id in entry["task_ids"]
            ],
        }
    return detailed


def _handle_run_requirement_workflow(
    requirement: str,
    project_name: Optional[str] = None,
    output_root: Optional[str] = None,
) -> str:
    try:
        result = run_workflow(requirement, project=project_name, output_root=output_root)
    except (ValueError, RuntimeError, TypeError) as exc:
        # A gate failure is a real answer, not a crash: say which stage refused
        # and write nothing (spec section 8).
        return json.dumps({
            "success": False,
            "error": str(exc),
            "documents_written": [],
        })

    return json.dumps({
        "success": True,
        "spec": f"{SPEC_ID} v{SPEC_VERSION}",
        "requirement": result.requirement.title,
        "output_directory": result.output_dir,
        "documents": result.written,
        "functional_requirements": len(result.prd.functional),
        "components": len(result.trd.components),
        "done_criteria": len(result.dod.all_criteria()),
        "tasks": len(result.plan.tasks),
        "assignments": _assignments(result),
    })


def _handle_definition_of_done(requirement: str, include_markdown: bool = False) -> str:
    try:
        result = run_workflow(requirement, write=False)
    except (ValueError, RuntimeError, TypeError) as exc:
        return json.dumps({"success": False, "error": str(exc)})

    dod = result.dod
    payload: Dict[str, Any] = {
        "success": True,
        "requirement": result.requirement.title,
        "criteria": len(dod.all_criteria()),
        "universal": [
            {
                "id": c.id,
                "perspective": PERSPECTIVE_TITLES[c.perspective],
                "criterion": c.text,
                "evidence": c.evidence,
                "owner": LANE_TITLES[c.owner_lane] if c.applies else None,
                "applies": c.applies,
                "not_applicable_reason": c.not_applicable_reason,
            }
            for c in dod.universal
        ],
        "by_feature": {
            fr.id: [
                {
                    "id": c.id,
                    "perspective": PERSPECTIVE_TITLES[c.perspective],
                    "criterion": c.text,
                    "evidence": c.evidence,
                    "owner": LANE_TITLES[c.owner_lane],
                }
                for c in dod.for_feature(fr.id)
            ]
            for fr in result.prd.functional
        },
        "by_owner": {
            LANE_TITLES[lane]: [c.id for c in dod.for_lane(lane)]
            for lane in LANE_ORDER
            if dod.for_lane(lane)
        },
    }
    if include_markdown:
        payload["definition_of_done_markdown"] = result.documents["DEFINITION-OF-DONE.md"]
    return json.dumps(payload)


def _handle_generate_task_breakdown(
    requirement: str,
    include_markdown: bool = False,
) -> str:
    try:
        result = run_workflow(requirement, write=False)
    except (ValueError, RuntimeError, TypeError) as exc:
        return json.dumps({"success": False, "error": str(exc)})

    payload: Dict[str, Any] = {
        "success": True,
        "requirement": result.requirement.title,
        "task_count": len(result.plan.tasks),
        "assignments": _assignments(result),
    }
    if include_markdown:
        payload["tasks_markdown"] = result.documents["TASKS.md"]
    return json.dumps(payload)


def register_requirement_workflow_tools(registry: ToolRegistry) -> None:
    """Register the workflow tools on ``registry``."""

    registry.register(Tool(
        name="run_requirement_workflow",
        description=(
            "Run the full Requirement -> PRD -> TRD -> DONE -> TASKS workflow over an "
            "inputted requirement and write PRD.md, TRD.md, DEFINITION-OF-DONE.md and "
            "TASKS.md under generated/. "
            "TASKS.md assigns every task to a named agent, traced back to the TRD "
            "component and PRD requirement it came from, and closing with a check against "
            "the Definition of Done. Deterministic: the same requirement always produces "
            "the same documents. Either all four documents are written or none are."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": (
                        "The inputted requirement. A leading '# Title' names it; each "
                        "markdown bullet becomes one numbered requirement item."
                    ),
                },
                "project_name": {
                    "type": "string",
                    "description": (
                        "Project folder under generated/. Omit to treat the requirement "
                        "as its own project."
                    ),
                },
                "output_root": {
                    "type": "string",
                    "description": "Override the output location entirely (rarely needed).",
                },
            },
            "required": ["requirement"],
        },
        handler=_handle_run_requirement_workflow,
        requires_approval=False,
        category="prd_trd",
    ))

    registry.register(Tool(
        name="define_what_done_means",
        description=(
            "State what good looks like for an inputted requirement, per feature, from the "
            "user, business and technical perspectives. Returns every criterion with the "
            "evidence that would show it has been met and the single agent accountable for "
            "it. Criteria the requirement cannot meet -- an accessibility bar with no "
            "interface, say -- are returned marked not applicable rather than reassigned."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": "The inputted requirement, as markdown or plain text.",
                },
                "include_markdown": {
                    "type": "boolean",
                    "description": "Also return the rendered DEFINITION-OF-DONE.md content.",
                },
            },
            "required": ["requirement"],
        },
        handler=_handle_definition_of_done,
        requires_approval=False,
        category="prd_trd",
    ))

    registry.register(Tool(
        name="generate_task_breakdown",
        description=(
            "Break an inputted requirement down into one task list per agent, without "
            "writing any files. Returns each agent's tasks with their priorities, "
            "efforts, dependencies and traceability. Use this to preview or reason "
            "about the split; use run_requirement_workflow to produce the documents."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "requirement": {
                    "type": "string",
                    "description": "The inputted requirement, as markdown or plain text.",
                },
                "include_markdown": {
                    "type": "boolean",
                    "description": "Also return the rendered TASKS.md content.",
                },
            },
            "required": ["requirement"],
        },
        handler=_handle_generate_task_breakdown,
        requires_approval=False,
        category="prd_trd",
    ))
