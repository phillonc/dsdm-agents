"""Requirement → PRD → TRD → TASKS workflow.

When a requirement is inputted, this package drives it through five gated
stages and emits four markdown deliverables — ``PRD.md``, ``TRD.md``,
``DEFINITION-OF-DONE.md`` and ``TASKS.md`` — the last two of which say what good
looks like and give every agent its own set of tasks measured against it.

    >>> from src.workflow import run_workflow
    >>> result = run_workflow("Merchant self-serve onboarding", write=False)
    >>> sorted(result.documents)
    ['DEFINITION-OF-DONE.md', 'PRD.md', 'TASKS.md', 'TRD.md']

Documents are written under ``generated/`` like every other agent artefact in
this repository. The pipeline is deterministic, so the orchestrator can
guarantee all four deliverables exist regardless of what the LLM-driven agents
produced alongside them.

The pipeline is specified in ``docs/WORKFLOW-PRD-TRD-TASKS.md`` (``WF-PRTT-001``),
which the ``DSDM-Agency`` and ``lhs-agents`` repositories implement identically.
"""

from .documents import (
    DOD_FILENAME,
    PRD_FILENAME,
    TASKS_FILENAME,
    TRD_FILENAME,
    render_definition_of_done,
    render_prd,
    render_tasks,
    render_trd,
)
from .intake import IntakeError, normalise_requirement, requirement_from_file
from .model import (
    DEFAULT_LANE_AGENTS,
    LANE_ROLE_IDS,
    PERSPECTIVES,
    PERSPECTIVE_SIGN_OFF,
    PERSPECTIVE_TITLES,
    DefinitionOfDone,
    DoneCriterion,
    IMPLEMENTATION_LANES,
    LANE_CODES,
    LANE_ORDER,
    LANE_TITLES,
    SPEC_ID,
    SPEC_VERSION,
    AgentTask,
    Component,
    FunctionalRequirement,
    NonFunctionalRequirement,
    PRD,
    Requirement,
    RequirementItem,
    TRD,
    TaskPlan,
    TechnicalRisk,
)
from .pipeline import (
    DOCS_SUBDIR,
    GENERATED_ROOT,
    WorkflowResult,
    document_directory,
    run_workflow,
    run_workflow_from_file,
)
from .routing import DEFAULT_LANE, LANE_KEYWORDS, lanes_for, routing_reason
from .stages import (
    BASELINE_NFRS,
    UNIVERSAL_CRITERIA,
    GateError,
    build_definition_of_done,
    build_prd,
    build_task_plan,
    build_trd,
)

__all__ = [
    # pipeline
    "run_workflow",
    "run_workflow_from_file",
    "WorkflowResult",
    "document_directory",
    "GENERATED_ROOT",
    "DOCS_SUBDIR",
    # stages
    "normalise_requirement",
    "requirement_from_file",
    "build_prd",
    "build_trd",
    "build_definition_of_done",
    "build_task_plan",
    "BASELINE_NFRS",
    "UNIVERSAL_CRITERIA",
    "GateError",
    "IntakeError",
    # rendering
    "render_prd",
    "render_trd",
    "render_definition_of_done",
    "render_tasks",
    "PRD_FILENAME",
    "DOD_FILENAME",
    "TRD_FILENAME",
    "TASKS_FILENAME",
    # routing
    "lanes_for",
    "routing_reason",
    "LANE_KEYWORDS",
    "DEFAULT_LANE",
    # model
    "Requirement",
    "RequirementItem",
    "FunctionalRequirement",
    "NonFunctionalRequirement",
    "PRD",
    "Component",
    "TechnicalRisk",
    "TRD",
    "DoneCriterion",
    "DefinitionOfDone",
    "PERSPECTIVES",
    "PERSPECTIVE_TITLES",
    "PERSPECTIVE_SIGN_OFF",
    "AgentTask",
    "TaskPlan",
    "LANE_ORDER",
    "LANE_CODES",
    "LANE_TITLES",
    "IMPLEMENTATION_LANES",
    "DEFAULT_LANE_AGENTS",
    "LANE_ROLE_IDS",
    "SPEC_ID",
    "SPEC_VERSION",
]
