"""Data model for the Requirement → PRD → TRD → TASKS workflow.

This module is the vocabulary shared by every stage of the pipeline. It is
deliberately free of rendering and of I/O: stages build these objects, the
renderers in :mod:`src.workflow.documents` turn them into markdown, and
:mod:`src.workflow.pipeline` writes them out.

See ``docs/WORKFLOW-PRD-TRD-TASKS.md`` (spec ``WF-PRTT-001``) — the same
document ships in the ``DSDM-Agency`` and ``lhs-agents`` repositories, whose
implementations mirror this one.

Unlike the LLM-driven ``generate_product_requirements_document`` /
``generate_technical_requirements_document`` tools, everything here is
deterministic: the same requirement always produces the same documents, which
is what lets the orchestrator guarantee the four deliverables exist whatever
the model did.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

SPEC_ID = "WF-PRTT-001"
SPEC_VERSION = "1.1.0"

# -- lanes ------------------------------------------------------------------
# A *lane* is a unit of delivery responsibility. The workflow is defined over
# lanes rather than over role names so that each repository can map its own
# agents onto the same pipeline (spec §7).

PRODUCT = "product"
ARCHITECTURE = "architecture"
DATA = "data"
BACKEND = "backend"
FRONTEND = "frontend"
SECURITY = "security"
QA = "qa"
DEVOPS = "devops"
DELIVERY = "delivery"

#: The single source of ordering for every document the workflow emits (spec §6).
LANE_ORDER: Tuple[str, ...] = (
    PRODUCT,
    ARCHITECTURE,
    DATA,
    BACKEND,
    FRONTEND,
    SECURITY,
    QA,
    DEVOPS,
    DELIVERY,
)

#: Short code embedded in task IDs, e.g. ``TASK-BE-001`` (spec §5).
LANE_CODES: Dict[str, str] = {
    PRODUCT: "PRD",
    ARCHITECTURE: "ARC",
    DATA: "DATA",
    BACKEND: "BE",
    FRONTEND: "FE",
    SECURITY: "SEC",
    QA: "QA",
    DEVOPS: "OPS",
    DELIVERY: "DEL",
}

LANE_TITLES: Dict[str, str] = {
    PRODUCT: "Product",
    ARCHITECTURE: "Architecture",
    DATA: "Data",
    BACKEND: "Backend",
    FRONTEND: "Frontend",
    SECURITY: "Security",
    QA: "Quality Assurance",
    DEVOPS: "DevOps",
    DELIVERY: "Delivery",
}

#: Which DSDM role owns each lane in *this* repository (spec §7). Callers can
#: override per run; the lane set may not change, only who answers for it.
DEFAULT_LANE_AGENTS: Dict[str, str] = {
    PRODUCT: "Product Manager Agent",
    ARCHITECTURE: "Dev Lead Agent",
    DATA: "Backend Developer Agent",
    BACKEND: "Backend Developer Agent",
    FRONTEND: "Frontend Developer Agent",
    SECURITY: "Pen Tester Agent",
    QA: "Automation Tester Agent",
    DEVOPS: "DevOps Agent",
    DELIVERY: "Implementation Agent",
}

#: ``role_definitions.py`` role IDs for the agents above, so a task can be
#: handed to the agent that actually runs it.
LANE_ROLE_IDS: Dict[str, str] = {
    PRODUCT: "product-manager",
    ARCHITECTURE: "dev-lead",
    DATA: "backend-developer",
    BACKEND: "backend-developer",
    FRONTEND: "frontend-developer",
    SECURITY: "pen-tester",
    QA: "automation-tester",
    DEVOPS: "devops",
    DELIVERY: "implementation",
}

#: Lanes that carry implementation work routed from requirements. ``product``,
#: ``architecture`` and ``delivery`` own documents and governance instead, and
#: reach TASKS.md through the cross-cutting tasks in spec §5.
IMPLEMENTATION_LANES: Tuple[str, ...] = (DATA, BACKEND, FRONTEND, SECURITY, QA, DEVOPS)

#: The three lenses every Definition of Done is written through (spec §5).
PERSPECTIVES: Tuple[str, ...] = ("user", "business", "technical")

PERSPECTIVE_TITLES: Dict[str, str] = {
    "user": "User",
    "business": "Business",
    "technical": "Technical",
}

#: Which lane answers for each perspective when the DoD is signed off.
PERSPECTIVE_SIGN_OFF: Dict[str, str] = {
    "user": PRODUCT,
    "business": DELIVERY,
    "technical": ARCHITECTURE,
}

MOSCOW_LABELS = {"M": "Must Have", "S": "Should Have", "C": "Could Have", "W": "Won't Have"}
_PRIORITY_ALIASES = {
    "M": "M", "MUST": "M",
    "S": "S", "SHOULD": "S",
    "C": "C", "COULD": "C",
    "W": "W", "WONT": "W", "WON'T": "W", "WILLNOT": "W",
}


def canonical_priority(value: Any, default: str = "S") -> str:
    """Normalise a MoSCoW priority to one of ``M``/``S``/``C``/``W``."""
    if value is None:
        return default
    key = str(value).strip().upper().replace(" ", "").replace("-", "")
    if key in _PRIORITY_ALIASES:
        return _PRIORITY_ALIASES[key]
    if key[:1] in {"M", "S", "C", "W"}:
        return key[:1]
    raise ValueError(f"unrecognised MoSCoW priority: {value!r}")


def slugify(text: str) -> str:
    """Lowercase, hyphen-separated slug used to name the output directory."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    if not slug:
        raise ValueError("cannot slugify an empty title")
    return slug


@dataclass(frozen=True)
class RequirementItem:
    """One atomic requirement extracted from the inputted text (spec §2)."""

    id: str
    text: str
    priority: str = "S"
    effort: float = 1.0


@dataclass
class Requirement:
    """The normalised requirement that enters the pipeline."""

    title: str
    description: str = ""
    id: str = ""
    requester: str = ""
    priority: str = "S"
    effort: float = 1.0
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    acceptance: List[str] = field(default_factory=list)
    out_of_scope: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    stakeholders: List[str] = field(default_factory=list)
    items: List[RequirementItem] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return slugify(self.title)

    @property
    def reference(self) -> str:
        """The identifier the documents cite — the supplied ID, else the slug."""
        return self.id or self.slug


@dataclass(frozen=True)
class FunctionalRequirement:
    """A ``PRD-FR-00N`` row: one intake item, restated as a requirement."""

    id: str
    text: str
    priority: str
    effort: float
    source: str  # the REQ-00N item it came from


@dataclass(frozen=True)
class NonFunctionalRequirement:
    """A ``PRD-NFR-00N`` row."""

    id: str
    category: str
    text: str


@dataclass
class PRD:
    """The product of stage 1."""

    requirement: Requirement
    functional: List[FunctionalRequirement]
    non_functional: List[NonFunctionalRequirement]

    def functional_by_id(self, fr_id: str) -> Optional[FunctionalRequirement]:
        return next((fr for fr in self.functional if fr.id == fr_id), None)


@dataclass(frozen=True)
class Component:
    """A ``TRD-C-00N`` block: one delivery lane's share of the solution."""

    id: str
    name: str
    lane: str
    satisfies: Tuple[str, ...]  # PRD-FR ids
    responsibility: str
    interfaces: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TechnicalRisk:
    id: str
    description: str
    mitigation: str


@dataclass
class TRD:
    """The product of stage 2."""

    requirement: Requirement
    components: List[Component]
    constraints: List[str]
    risks: List[TechnicalRisk]

    def components_for(self, fr_id: str) -> List[Component]:
        return [c for c in self.components if fr_id in c.satisfies]


@dataclass(frozen=True)
class DoneCriterion:
    """One statement of what *good* looks like, and how you would know.

    Every criterion names the lane accountable for it, so nothing in the
    Definition of Done is everybody's job and therefore nobody's.
    """

    id: str
    perspective: str      # one of PERSPECTIVES
    text: str             # what must be true
    evidence: str         # how you would know it is true
    owner_lane: str       # the lane that answers for it
    applies_to: Tuple[str, ...] = ()  # PRD-FR ids; empty means the whole requirement
    applies: bool = True  # False when the requirement cannot satisfy it
    not_applicable_reason: str = ""


@dataclass
class DefinitionOfDone:
    """The product of stage 3 — what good looks like for this requirement."""

    requirement: Requirement
    universal: List[DoneCriterion]
    by_feature: Dict[str, List[DoneCriterion]]  # PRD-FR id -> its criteria

    def all_criteria(self) -> List[DoneCriterion]:
        criteria = list(self.universal)
        for fr_id in sorted(self.by_feature):
            criteria.extend(self.by_feature[fr_id])
        return criteria

    def for_feature(self, fr_id: str) -> List[DoneCriterion]:
        return list(self.by_feature.get(fr_id, ()))

    def for_lane(self, lane: str) -> List[DoneCriterion]:
        """Every *applicable* criterion this lane answers for.

        Criteria marked not-applicable stay in the document — a reader can see
        they were considered — but they are never attached to a Done check.
        Ticking a box that cannot mean anything teaches people to tick boxes.
        """
        return [c for c in self.all_criteria() if c.applies and c.owner_lane == lane]

    def by_perspective(self, perspective: str) -> List[DoneCriterion]:
        return [c for c in self.universal if c.perspective == perspective]


@dataclass(frozen=True)
class AgentTask:
    """A ``TASK-<LANE>-00N`` entry — one agent's unit of work."""

    id: str
    lane: str
    agent: str
    title: str
    acceptance: str
    priority: str
    effort: float
    traces_prd: Tuple[str, ...] = ()
    traces_trd: Tuple[str, ...] = ()
    traces_dod: Tuple[str, ...] = ()
    depends_on: Tuple[str, ...] = ()


@dataclass
class TaskPlan:
    """The product of stage 3: every agent's own set of tasks."""

    requirement: Requirement
    tasks: List[AgentTask]
    lane_agents: Dict[str, str]

    def lanes(self) -> List[str]:
        """Lanes that have work, in the canonical lane order."""
        present = {t.lane for t in self.tasks}
        return [lane for lane in LANE_ORDER if lane in present]

    def for_lane(self, lane: str) -> List[AgentTask]:
        return [t for t in self.tasks if t.lane == lane]

    def tasks_for_component(self, component_id: str) -> List[AgentTask]:
        return [t for t in self.tasks if component_id in t.traces_trd]

    def assignments(self) -> Dict[str, Dict[str, Any]]:
        """Agent → the lanes and tasks they own.

        An agent may own several lanes, so entries **merge**: keying a dict on
        the agent name without accumulating silently reports only that agent's
        last lane.
        """
        merged: Dict[str, Dict[str, Any]] = {}
        for lane in self.lanes():
            entry = merged.setdefault(
                self.lane_agents[lane],
                {"lanes": [], "task_count": 0, "task_ids": []},
            )
            lane_tasks = self.for_lane(lane)
            entry["lanes"].append(lane)
            entry["task_count"] += len(lane_tasks)
            entry["task_ids"].extend(task.id for task in lane_tasks)
        return merged



RawRequirement = Union[str, Dict[str, Any], Requirement]


def numbered(prefix: str, index: int) -> str:
    """``numbered("PRD-FR", 3) -> "PRD-FR-003"``."""
    return f"{prefix}-{index:03d}"


def sequence_of(values: Sequence[Any]) -> List[str]:
    """Coerce a scalar-or-sequence field into a clean list of strings."""
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [str(v).strip() for v in values if str(v).strip()]
