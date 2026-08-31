"""Markdown renderers for the three workflow deliverables.

Renderers are **pure functions** of their inputs (spec §8/§9.4): no clocks, no
random identifiers, no environment lookups. The same requirement therefore
produces byte-identical documents on every run and in every repository, which
is what makes the output diffable and the tests meaningful.

These are the workflow's own deliverables and are written alongside — not in
place of — the narrative documents an agent may author with ``file_write``.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .model import (
    LANE_TITLES,
    MOSCOW_LABELS,
    SPEC_ID,
    SPEC_VERSION,
    PRD,
    Requirement,
    TRD,
    TaskPlan,
)

PRD_FILENAME = "PRD.md"
TRD_FILENAME = "TRD.md"
TASKS_FILENAME = "TASKS.md"


# -- markdown helpers -------------------------------------------------------

def _escape(value: object) -> str:
    """Make a value safe to drop into a markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(_escape(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def _bullets(items: Sequence[str], empty: str) -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {empty}"


def _effort(value: float) -> str:
    """Render an effort estimate without a trailing ``.0`` on whole numbers."""
    return str(int(value)) if float(value).is_integer() else f"{float(value):g}"


def _metadata(requirement: Requirement, stage: str, derives_from: str = "") -> str:
    rows = [
        ("Requirement", requirement.title),
        ("Requirement ID", requirement.reference),
        ("Stage", stage),
        ("Priority", f"{requirement.priority} — {MOSCOW_LABELS[requirement.priority]}"),
        ("Requester", requirement.requester or "Not recorded"),
        ("Workflow spec", f"`{SPEC_ID}` v{SPEC_VERSION}"),
    ]
    if derives_from:
        rows.insert(3, ("Derives from", derives_from))
    return _table(["Field", "Value"], rows)


# -- PRD --------------------------------------------------------------------

def render_prd(prd: PRD) -> str:
    """Render ``PRD.md`` (spec §3)."""
    requirement = prd.requirement
    parts: List[str] = [
        f"# Product Requirements Document — {requirement.title}",
        "",
        _metadata(requirement, "1 — PRD"),
        "",
        "## 1. Overview",
        "",
        requirement.description.strip()
        or f"This document restates the requirement *{requirement.title}* as numbered "
           "product requirements so the technical and delivery lanes can work from one source.",
        "",
        "## 2. Problem Statement",
        "",
        f"*{requirement.title}* is not currently supported. Until it is, the outcomes in "
        "section 3 cannot be met, and the requirements in section 5 have no owner.",
        "",
        "## 3. Goals and Success Metrics",
        "",
        _bullets(
            requirement.goals,
            "Deliver every Must Have requirement in section 5 within the agreed timebox.",
        ),
        "",
        "## 4. Users and Stakeholders",
        "",
        _bullets(
            requirement.stakeholders,
            f"Requester: {requirement.requester or 'not recorded'} — "
            "confirm the full stakeholder list before the PRD is signed off.",
        ),
        "",
        "## 5. Functional Requirements",
        "",
        _table(
            ["ID", "Requirement", "Priority", "Effort", "Source"],
            [
                (fr.id, fr.text, f"{fr.priority} ({MOSCOW_LABELS[fr.priority]})", _effort(fr.effort), fr.source)
                for fr in prd.functional
            ],
        ),
        "",
        "## 6. Non-Functional Requirements",
        "",
        _table(
            ["ID", "Category", "Requirement"],
            [(nfr.id, nfr.category, nfr.text) for nfr in prd.non_functional],
        ),
        "",
        "## 7. Out of Scope",
        "",
        _bullets(
            requirement.out_of_scope,
            "Anything not listed in section 5 is out of scope for this requirement.",
        ),
        "",
        "## 8. Assumptions and Constraints",
        "",
        _bullets(
            requirement.assumptions + requirement.constraints,
            "No assumptions or constraints were supplied with the requirement.",
        ),
        "",
        "## 9. Acceptance Criteria",
        "",
        _bullets(
            requirement.acceptance,
            "Every Must Have requirement in section 5 is demonstrable and covered by a test.",
        ),
        "",
        "## 10. Traceability",
        "",
        _table(
            ["Requirement item", "Product requirement"],
            [(fr.source, fr.id) for fr in prd.functional],
        ),
        "",
    ]
    return "\n".join(parts)


# -- TRD --------------------------------------------------------------------

def render_trd(trd: TRD, prd: PRD) -> str:
    """Render ``TRD.md`` (spec §4)."""
    requirement = trd.requirement
    parts: List[str] = [
        f"# Technical Requirements Document — {requirement.title}",
        "",
        _metadata(requirement, "2 — TRD", derives_from=f"[{PRD_FILENAME}](./{PRD_FILENAME})"),
        "",
        "## 1. Overview",
        "",
        f"This document turns the {len(prd.functional)} functional requirement(s) in "
        f"[{PRD_FILENAME}](./{PRD_FILENAME}) into {len(trd.components)} technical component(s). "
        "Every product requirement is routed to at least one component, and every component "
        "records what it satisfies, so the breakdown in "
        f"[{TASKS_FILENAME}](./{TASKS_FILENAME}) can be generated rather than guessed.",
        "",
        "## 2. Architecture Summary",
        "",
        _table(
            ["Component", "Name", "Lane", "Satisfies"],
            [
                (c.id, c.name, LANE_TITLES[c.lane], ", ".join(c.satisfies))
                for c in trd.components
            ],
        ),
        "",
        "## 3. Components",
        "",
    ]

    for component in trd.components:
        parts.extend([
            f"### {component.id} — {component.name}",
            "",
            f"**Lane:** {LANE_TITLES[component.lane]}",
            "",
            component.responsibility,
            "",
            "**Satisfies**",
            "",
        ])
        for fr_id in component.satisfies:
            fr = prd.functional_by_id(fr_id)
            parts.append(f"- `{fr_id}` — {fr.text if fr else 'unknown requirement'}")
        parts.extend(["", "**Interfaces**", "", _bullets(list(component.interfaces), "No external interface."), ""])

    parts.extend([
        "## 4. Data and Interfaces",
        "",
        "Every interface listed against a component in section 3 is a contract: a change to "
        "it is a change to this document, and to the tasks that depend on it.",
        "",
        _table(
            ["Component", "Interfaces"],
            [(c.id, "; ".join(c.interfaces) or "None") for c in trd.components],
        ),
        "",
        "## 5. Non-Functional and Technical Constraints",
        "",
        _bullets(trd.constraints, "No constraints recorded."),
        "",
        "## 6. Testing Strategy",
        "",
        "- Every functional requirement is verified by the Verification Harness component; "
        "a requirement with no test is not done.",
        "- Implementation tasks are accepted only once their verification task passes.",
        "- The traceability table in section 8 is the checklist for coverage.",
        "",
        "## 7. Risks",
        "",
        _table(
            ["ID", "Risk", "Mitigation"],
            [(r.id, r.description, r.mitigation) for r in trd.risks],
        ),
        "",
        "## 8. Traceability",
        "",
        _table(
            ["Product requirement", "Components"],
            [
                (fr.id, ", ".join(c.id for c in trd.components_for(fr.id)))
                for fr in prd.functional
            ],
        ),
        "",
    ])
    return "\n".join(parts)


# -- TASKS ------------------------------------------------------------------

def render_tasks(plan: TaskPlan, trd: TRD) -> str:
    """Render ``TASKS.md`` — one section per agent (spec §5)."""
    requirement = plan.requirement
    lanes = plan.lanes()

    parts: List[str] = [
        f"# Task Breakdown — {requirement.title}",
        "",
        _metadata(requirement, "3 — TASKS", derives_from=f"[{TRD_FILENAME}](./{TRD_FILENAME})"),
        "",
        "Each section below belongs to one agent. An agent completes its own checklist and "
        "nothing else; the dependencies name what has to land first.",
        "",
        "## 1. Assignment Summary",
        "",
        _table(
            ["Agent", "Lane", "Tasks", "Effort"],
            [
                (
                    plan.lane_agents[lane],
                    LANE_TITLES[lane],
                    len(plan.for_lane(lane)),
                    _effort(sum(t.effort for t in plan.for_lane(lane))),
                )
                for lane in lanes
            ],
        ),
        "",
        "## 2. Execution Order",
        "",
        " → ".join(LANE_TITLES[lane] for lane in lanes),
        "",
        "## 3. Tasks by Agent",
        "",
    ]

    for index, lane in enumerate(lanes, start=1):
        parts.extend([
            f"### 3.{index} {plan.lane_agents[lane]} — `{lane}`",
            "",
        ])
        for task in plan.for_lane(lane):
            traces = ", ".join(f"`{ref}`" for ref in task.traces_prd + task.traces_trd)
            depends = ", ".join(f"`{ref}`" for ref in task.depends_on) or "None"
            parts.extend([
                f"- [ ] **{task.id}** — {task.title}",
                f"  - Traces to: {traces}",
                f"  - Priority: {task.priority} ({MOSCOW_LABELS[task.priority]}) · "
                f"Effort: {_effort(task.effort)} · Depends on: {depends}",
                f"  - Acceptance: {task.acceptance}",
            ])
        parts.append("")

    parts.extend([
        "## 4. Traceability",
        "",
        _table(
            ["Component", "Tasks"],
            [
                (c.id, ", ".join(t.id for t in plan.tasks_for_component(c.id)))
                for c in trd.components
            ],
        ),
        "",
    ])
    return "\n".join(parts)
