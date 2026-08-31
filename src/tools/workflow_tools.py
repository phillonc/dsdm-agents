"""Requirement workflow tools — PRD, TRD and per-agent TASKS.

These register the deterministic Requirement → PRD → TRD → TASKS pipeline
(:mod:`src.workflow`) with the DSDM tool registry, so an agent can run it the
same way it runs any other tool.

They sit alongside ``generate_product_requirements_document`` and
``generate_technical_requirements_document`` rather than replacing them: those
tools help an agent *structure its thinking* before it writes narrative
documents, while these produce the three deliverables the workflow spec
guarantees — including ``TASKS.md``, which gives every agent its own task list.

Parameter names avoid ``ToolRegistry.PARAMETER_ALIASES`` (``project``, ``name``,
``text``, ``path``, …), which would otherwise be rewritten before the handler
sees them.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..workflow import LANE_ROLE_IDS, LANE_TITLES, SPEC_ID, SPEC_VERSION
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
                    "traces_to": list(by_id[task_id].traces_prd) + list(by_id[task_id].traces_trd),
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
        "tasks": len(result.plan.tasks),
        "assignments": _assignments(result),
    })


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
            "Run the full Requirement -> PRD -> TRD -> TASKS workflow over an inputted "
            "requirement and write PRD.md, TRD.md and TASKS.md under generated/. "
            "TASKS.md assigns every task to a named agent, traced back to the TRD "
            "component and PRD requirement it came from. Deterministic: the same "
            "requirement always produces the same documents. Either all three "
            "documents are written or none are."
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
