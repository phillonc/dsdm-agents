"""The four pipeline stages, as pure functions over the model.

Each stage is a hard gate (spec §1): calling one without the previous stage's
product raises :class:`GateError` rather than emitting an empty document.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .model import (
    ARCHITECTURE,
    LANE_TITLES,
    BACKEND,
    DATA,
    DELIVERY,
    DEVOPS,
    FRONTEND,
    IMPLEMENTATION_LANES,
    LANE_CODES,
    LANE_ORDER,
    PRODUCT,
    QA,
    SECURITY,
    DEFAULT_LANE_AGENTS,
    PERSPECTIVE_SIGN_OFF,
    AgentTask,
    DefinitionOfDone,
    DoneCriterion,
    Component,
    FunctionalRequirement,
    NonFunctionalRequirement,
    PRD,
    Requirement,
    TRD,
    TaskPlan,
    TechnicalRisk,
    numbered,
)
from .routing import lanes_for


class GateError(RuntimeError):
    """A stage was entered without the product the previous stage owes it."""


# -- stage 1: PRD -----------------------------------------------------------

#: Always present so no PRD ships without non-functional requirements (spec §3).
BASELINE_NFRS: Tuple[Tuple[str, str], ...] = (
    ("Performance", "User-facing operations respond within 2 seconds at the expected load."),
    ("Security", "Access is authenticated and authorised; no secret or personal data is logged."),
    ("Accessibility", "User-facing surfaces meet WCAG 2.2 AAA."),
    ("Observability", "Every failure path emits a structured, traceable log record."),
    ("Maintainability", "Delivered work carries automated tests and is documented in this repository."),
)


def build_prd(requirement: Requirement) -> PRD:
    """Stage 1 — restate the intake items as numbered product requirements."""
    if not requirement.items:
        raise GateError(
            "PRD stage requires a normalised requirement with at least one item; "
            "run intake.normalise_requirement first"
        )

    functional = [
        FunctionalRequirement(
            id=numbered("PRD-FR", index),
            text=item.text,
            priority=item.priority,
            effort=item.effort,
            source=item.id,
        )
        for index, item in enumerate(requirement.items, start=1)
    ]

    non_functional: List[NonFunctionalRequirement] = [
        NonFunctionalRequirement(numbered("PRD-NFR", index), category, text)
        for index, (category, text) in enumerate(BASELINE_NFRS, start=1)
    ]
    for offset, constraint in enumerate(requirement.constraints, start=len(BASELINE_NFRS) + 1):
        non_functional.append(
            NonFunctionalRequirement(numbered("PRD-NFR", offset), "Constraint", constraint)
        )

    return PRD(requirement=requirement, functional=functional, non_functional=non_functional)


# -- stage 2: TRD -----------------------------------------------------------

#: lane -> (component name, responsibility, interfaces)
_LANE_COMPONENTS: Dict[str, Tuple[str, str, Tuple[str, ...]]] = {
    DATA: (
        "Data and Persistence",
        "Owns the schema, migrations and query paths behind the requirements it satisfies.",
        ("Repository interfaces consumed by the application services",),
    ),
    BACKEND: (
        "Application Services",
        "Implements the business logic and the server-side API surface.",
        ("HTTP/RPC endpoints published to clients", "Repository interfaces from the data component"),
    ),
    FRONTEND: (
        "User Interface",
        "Delivers the screens, flows and client-side state users interact with.",
        ("The API surface published by the application services",),
    ),
    SECURITY: (
        "Access Control and Data Protection",
        "Enforces authentication, authorisation and data-handling rules across the solution.",
        ("Identity provider", "Audit log sink"),
    ),
    QA: (
        "Verification Harness",
        "Provides automated coverage for every functional requirement in this document.",
        ("Test fixtures and seed data", "CI test reporter"),
    ),
    DEVOPS: (
        "Build, Release and Observability",
        "Carries the solution into an environment and keeps it observable there.",
        ("CI/CD pipeline", "Metrics, logs and alerting"),
    ),
}


def _risks_for(components: List[Component], prd: PRD) -> List[TechnicalRisk]:
    """Derive the risk register from what the TRD actually contains."""
    lanes = {c.lane for c in components}
    risks: List[Tuple[str, str]] = [
        (
            "Scope drift between the PRD and the delivered solution.",
            "The traceability table in section 8 is generated, not hand-maintained; "
            "a requirement with no component fails the TRD gate.",
        )
    ]
    if SECURITY in lanes:
        risks.append((
            "The requirement touches identity or sensitive data, so a defect here is a disclosure, not a bug.",
            "Security review task is mandatory before the implementation tasks are accepted.",
        ))
    if DATA in lanes:
        risks.append((
            "Schema changes are hard to reverse once data exists behind them.",
            "Ship migrations forward-only with a tested rollback path before the release task closes.",
        ))
    if FRONTEND in lanes and BACKEND in lanes:
        risks.append((
            "The client and the service can drift apart across the API boundary.",
            "The interface listed on the application services component is the contract; "
            "the verification harness covers it from both sides.",
        ))

    must_effort = sum(fr.effort for fr in prd.functional if fr.priority == "M")
    delivered = sum(fr.effort for fr in prd.functional if fr.priority != "W")
    if delivered and (must_effort / delivered) > 0.6:
        risks.append((
            "Must Have work exceeds 60% of delivered effort, leaving no contingency in the timebox.",
            "The delivery lane re-confirms MoSCoW before the timebox is committed.",
        ))

    return [
        TechnicalRisk(numbered("TRD-R", index), description, mitigation)
        for index, (description, mitigation) in enumerate(risks, start=1)
    ]


def build_trd(prd: PRD) -> TRD:
    """Stage 2 — route every functional requirement onto technical components."""
    if not prd.functional:
        raise GateError("TRD stage requires a PRD with at least one functional requirement")

    routed: Dict[str, List[str]] = {lane: [] for lane in IMPLEMENTATION_LANES}
    for fr in prd.functional:
        for lane in lanes_for(fr.text):
            if lane in routed:
                routed[lane].append(fr.id)
        # QA is never keyword-routed: everything gets a verification owner (spec §4.1).
        routed[QA].append(fr.id)

    components: List[Component] = []
    for lane in LANE_ORDER:
        satisfied = routed.get(lane) or []
        if not satisfied:
            continue
        name, responsibility, interfaces = _LANE_COMPONENTS[lane]
        components.append(
            Component(
                id=numbered("TRD-C", len(components) + 1),
                name=name,
                lane=lane,
                satisfies=tuple(satisfied),
                responsibility=responsibility,
                interfaces=interfaces,
            )
        )

    constraints = [nfr.text for nfr in prd.non_functional]
    return TRD(
        requirement=prd.requirement,
        components=components,
        constraints=constraints,
        risks=_risks_for(components, prd),
    )


# -- stage 3: DEFINITION OF DONE --------------------------------------------

#: Criteria that hold for every requirement, whatever it contains (spec §5).
#: Each is (perspective, owning lane, statement, evidence, requires_lane).
#:
#: The owning lane is what makes a criterion someone's job rather than a
#: slogan. ``requires_lane`` is a different question — whether the criterion
#: *applies at all*: a requirement with no interface cannot meaningfully meet
#: an accessibility bar, and reassigning that check to whoever is available
#: would produce a tick that means nothing. Where it is empty, the criterion
#: always applies and only its owner may fall back.
UNIVERSAL_CRITERIA: Tuple[Tuple[str, str, str, str, Optional[str]], ...] = (
    (
        "user", FRONTEND,
        "User-facing surfaces meet WCAG 2.2 AAA: 7:1 contrast, enhanced focus indicators, "
        "full keyboard navigation, 44x44px minimum target size, and screen-reader verified.",
        "An automated axe-core run plus a recorded manual screen-reader pass. "
        "Any exception is listed here with its justification.",
        FRONTEND,
    ),
    (
        "user", FRONTEND,
        "The journey can be completed unaided: the happy path, error states, empty states "
        "and loading states are all specified and handled.",
        "One end-to-end test per state, named in the QA plan.",
        FRONTEND,
    ),
    (
        "user", QA,
        "Existing users are not regressed: prior behaviour still works, or was migrated "
        "deliberately and announced.",
        "The regression suite is green on the release candidate.",
        None,
    ),
    (
        "business", PRODUCT,
        "A named Business Ambassador has seen the feature working and accepted it.",
        "Their name and the date, recorded against the PRD's acceptance criteria.",
        None,
    ),
    (
        "business", PRODUCT,
        "Every success metric in section 3 of the PRD is instrumented and readable in production.",
        "A link to the dashboard or query that returns the metric.",
        None,
    ),
    (
        "business", DELIVERY,
        "Must Have scope is complete, or the shortfall has been re-negotiated and recorded.",
        "MoSCoW re-confirmed by the delivery lane before release.",
        None,
    ),
    (
        "technical", QA,
        "Unit test coverage on changed code is at least 80%, and every acceptance criterion "
        "has a test.",
        "The coverage report from the pipeline.",
        None,
    ),
    (
        "technical", DEVOPS,
        "CI is green on the merge commit: build, lint, type-check and the full test suite.",
        "The pipeline run for that commit.",
        None,
    ),
    (
        "technical", DEVOPS,
        "A rollback plan is documented and has been rehearsed.",
        "The plan itself, plus a note of when it was rehearsed.",
        None,
    ),
    (
        "technical", ARCHITECTURE,
        "Reviewed and merged: at least one reviewer, and no unresolved review threads.",
        "The approval record on the pull request.",
        None,
    ),
    (
        "technical", BACKEND,
        "Every failure path emits a structured, traceable log record.",
        "A log sample, or a test asserting the record is written.",
        None,
    ),
)

#: Extra criteria a feature earns from the lanes it routes to.
#: lane -> (perspective, owning lane, statement template, evidence)
_LANE_CRITERIA: Dict[str, Tuple[Tuple[str, str, str, str], ...]] = {
    FRONTEND: ((
        "user", FRONTEND,
        "The interface for {fr} is responsive across every supported breakpoint and has been "
        "through design review.",
        "Screenshots at each breakpoint, and the reviewer's name.",
    ),),
    BACKEND: ((
        "technical", BACKEND,
        "The interface serving {fr} has a documented contract, validates its inputs, and "
        "defines its error responses.",
        "The published contract, plus tests for the rejection paths.",
    ),),
    DATA: ((
        "technical", DATA,
        "Schema changes behind {fr} ship forward-only with a tested rollback path, and no "
        "personal data reaches the logs.",
        "The migration, its rollback rehearsal, and a log inspection.",
    ),),
    SECURITY: (
        (
            "technical", SECURITY,
            "Access to {fr} is authorised as well as authenticated, and every attempt leaves "
            "an audit record.",
            "Tests covering an authorised call, an unauthorised call, and the audit record.",
        ),
        (
            "business", SECURITY,
            "Where {fr} handles personal data, the lawful basis and the consent path are recorded.",
            "The record of the lawful basis, reviewed by whoever owns data protection.",
        ),
    ),
    DEVOPS: ((
        "technical", DEVOPS,
        "{fr} is deployed through the pipeline, is monitored, and has an alert that fires on "
        "its actual failure mode.",
        "The alert definition, and evidence it fired in a test.",
    ),),
}


def build_definition_of_done(
    prd: PRD,
    trd: TRD,
) -> DefinitionOfDone:
    """Stage 3 — state what good looks like, per feature and overall.

    Universal criteria hold for everything. Per-feature criteria are derived
    from the same lane routing that built the TRD, so a data feature is held to
    data standards and a user-facing one to user-facing standards, without
    anybody hand-maintaining the mapping.

    Every feature gets at least one criterion from each of the three
    perspectives, so no feature can be called done on technical grounds alone.
    """
    if not prd.functional:
        raise GateError("DONE stage requires a PRD with at least one functional requirement")
    if not trd.components:
        raise GateError("DONE stage requires a TRD with at least one component")

    present_lanes = {c.lane for c in trd.components}

    # Lanes that always have an owner, because they always have tasks.
    governance_lanes = (PRODUCT, ARCHITECTURE, DELIVERY, QA)

    universal: List[DoneCriterion] = []
    for index, (perspective, owner, text, evidence, requires) in enumerate(UNIVERSAL_CRITERIA, start=1):
        applies = requires is None or requires in present_lanes
        reason = (
            ""
            if applies
            else f"No {LANE_TITLES[requires].lower()} work in this requirement, "
                 "so there is nothing here to hold to this bar."
        )
        # A criterion owned by a lane this requirement does not use still needs
        # somebody to answer for it: it falls to the lane that signs off its
        # perspective, not to whoever happens to be free.
        lane = owner if owner in present_lanes or owner in governance_lanes else PERSPECTIVE_SIGN_OFF[perspective]
        universal.append(
            DoneCriterion(
                id=f"DOD-U-{index:03d}",
                perspective=perspective,
                text=text,
                evidence=evidence,
                owner_lane=lane,
                applies=applies,
                not_applicable_reason=reason,
            )
        )

    by_feature: Dict[str, List[DoneCriterion]] = {}
    for position, fr in enumerate(prd.functional, start=1):
        prefix = f"DOD-F{position:03d}"
        drafted: List[Tuple[str, str, str, str]] = [
            (
                "user", QA,
                f"{fr.id} is demonstrable end to end — someone can watch it happen, not just "
                "read that it was built.",
                "A demonstration to the Business Ambassador, or a recording of one.",
            ),
            (
                "technical", QA,
                f"Automated tests cover {fr.id} at the right level and fail when it regresses.",
                "The tests named against this requirement in the QA plan.",
            ),
        ]
        if fr.priority == "M":
            drafted.append((
                "business", DELIVERY,
                f"{fr.id} is a Must Have: it carries no known open defects at Done.",
                "An empty open-defect list for this requirement.",
            ))
        else:
            drafted.append((
                "business", DELIVERY,
                f"Any known defect in {fr.id} is logged, triaged, and accepted by the "
                "Business Ambassador.",
                "The triage record and their acceptance.",
            ))

        for lane in LANE_ORDER:
            if lane not in present_lanes:
                continue
            component = next((c for c in trd.components if c.lane == lane), None)
            if component is None or fr.id not in component.satisfies:
                continue
            for perspective, owner, template, evidence in _LANE_CRITERIA.get(lane, ()):
                drafted.append((perspective, owner, template.format(fr=fr.id), evidence))

        by_feature[fr.id] = [
            DoneCriterion(
                id=f"{prefix}-{offset:03d}",
                perspective=perspective,
                text=text,
                evidence=evidence,
                owner_lane=owner,
                applies_to=(fr.id,),
            )
            for offset, (perspective, owner, text, evidence) in enumerate(drafted, start=1)
        ]

    return DefinitionOfDone(requirement=prd.requirement, universal=universal, by_feature=by_feature)


# -- stage 4: TASKS ---------------------------------------------------------

#: Governance work that happens on every requirement, whatever it contains (spec §5).
_CROSS_CUTTING: Dict[str, Tuple[str, str]] = {
    PRODUCT: (
        "Confirm the PRD with stakeholders and freeze scope",
        "Every functional requirement is signed off or moved to Out of Scope.",
    ),
    ARCHITECTURE: (
        "Sign off the TRD and publish the component boundaries",
        "Every PRD-FR maps to at least one component and the interfaces are agreed.",
    ),
    SECURITY: (
        "Security review of the TRD",
        "Auth, data handling and audit are assessed against the non-functional requirements; findings are logged.",
    ),
    QA: (
        "Author the test plan covering every functional requirement",
        "The plan names at least one test per PRD-FR and is agreed with the product lane.",
    ),
    DEVOPS: (
        "Confirm pipeline and deployment readiness",
        "The change builds, tests and deploys through the pipeline with monitoring in place.",
    ),
    DELIVERY: (
        "Produce the timebox plan and confirm the MoSCoW balance",
        "Work fits the agreed capacity and Must Have effort stays within the 60% guideline.",
    ),
}

_IMPLEMENTATION_VERBS: Dict[str, str] = {
    DATA: "Model and persist",
    BACKEND: "Implement",
    FRONTEND: "Build the user interface for",
    SECURITY: "Enforce access control and data protection for",
    QA: "Verify",
    DEVOPS: "Operationalise",
}


def _acceptance_for(lane: str, fr: FunctionalRequirement) -> str:
    if lane == QA:
        return f"Automated tests cover {fr.id} and fail when the behaviour regresses."
    if lane == SECURITY:
        return f"{fr.id} is reachable only by authorised callers and leaves an audit record."
    if lane == DEVOPS:
        return f"{fr.id} is deployed through the pipeline and observable in the target environment."
    return f"{fr.id} behaves as stated in the PRD and is covered by the tests named in the QA plan."


def build_task_plan(
    prd: PRD,
    trd: TRD,
    dod: DefinitionOfDone,
    lane_agents: Optional[Dict[str, str]] = None,
) -> TaskPlan:
    """Stage 4 — give every agent its own set of tasks.

    Each component yields one implementation task per functional requirement it
    satisfies, on top of the cross-cutting tasks every run carries. Each lane
    then closes with a Done check against the criteria it owns in the
    Definition of Done, so "done" is measured against a written bar rather than
    against whoever is asked.
    """
    if not trd.components:
        raise GateError("TASKS stage requires a TRD with at least one component")
    if not dod.all_criteria():
        raise GateError("TASKS stage requires a Definition of Done with at least one criterion")

    agents = dict(DEFAULT_LANE_AGENTS)
    agents.update(lane_agents or {})

    components_by_lane = {c.lane: c for c in trd.components}
    fr_by_id = {fr.id: fr for fr in prd.functional}

    # Pass 1 — draft every task in lane order and assign its ID.
    drafts: List[Dict[str, object]] = []
    for lane in LANE_ORDER:
        counter = 0
        cross_cutting = _CROSS_CUTTING.get(lane)
        component = components_by_lane.get(lane)
        if cross_cutting is None and component is None:
            continue

        if cross_cutting is not None:
            counter += 1
            title, acceptance = cross_cutting
            drafts.append({
                "id": f"TASK-{LANE_CODES[lane]}-{counter:03d}",
                "lane": lane,
                "title": title,
                "acceptance": acceptance,
                "priority": "M",
                "effort": 1.0,
                "traces_prd": tuple(fr.id for fr in prd.functional),
                "traces_trd": (component.id,) if component else (),
            })

        if component is not None:
            for fr_id in component.satisfies:
                fr = fr_by_id[fr_id]
                counter += 1
                drafts.append({
                    "id": f"TASK-{LANE_CODES[lane]}-{counter:03d}",
                    "lane": lane,
                    "title": f"{_IMPLEMENTATION_VERBS[lane]}: {fr.text}",
                    "acceptance": _acceptance_for(lane, fr),
                    "priority": fr.priority,
                    "effort": fr.effort,
                    "traces_prd": (fr.id,),
                    "traces_trd": (component.id,),
                })

        # Every lane closes with a Done check against the criteria it owns.
        owned = dod.for_lane(lane)
        if owned:
            counter += 1
            drafts.append({
                "id": f"TASK-{LANE_CODES[lane]}-{counter:03d}",
                "lane": lane,
                "title": "Verify this lane's work against the Definition of Done",
                "acceptance": (
                    "Every criterion this lane owns is met and its evidence recorded: "
                    + ", ".join(c.id for c in owned)
                    + "."
                ),
                "priority": "M",
                "effort": 1.0,
                "traces_prd": tuple(
                    dict.fromkeys(ref for c in owned for ref in c.applies_to)
                ),
                "traces_trd": (component.id,) if component else (),
                "traces_dod": tuple(c.id for c in owned),
                "is_done_check": True,
            })

    # Pass 2 — wire dependencies now that every ID exists.
    architecture_gate = next(
        (d["id"] for d in drafts if d["lane"] == ARCHITECTURE), None
    )
    build_lanes = (DATA, BACKEND, FRONTEND, SECURITY, DEVOPS)

    tasks: List[AgentTask] = []
    for draft in drafts:
        lane = draft["lane"]
        depends: List[str] = []
        if architecture_gate and draft["id"] != architecture_gate:
            depends.append(architecture_gate)
        if draft.get("is_done_check"):
            # You cannot check work against the bar before the work exists.
            depends.extend(
                other["id"] for other in drafts
                if other["lane"] == lane and other["id"] != draft["id"]
            )
        if lane == QA and draft["traces_trd"] and not draft.get("is_done_check"):
            # A verification task waits on whoever builds the thing it verifies.
            covered = set(draft["traces_prd"])
            depends.extend(
                other["id"]
                for other in drafts
                if other["lane"] in build_lanes and covered & set(other["traces_prd"])
            )
        tasks.append(
            AgentTask(
                id=draft["id"],
                lane=lane,
                agent=agents[lane],
                title=draft["title"],
                acceptance=draft["acceptance"],
                priority=draft["priority"],
                effort=draft["effort"],
                traces_prd=draft["traces_prd"],
                traces_trd=draft["traces_trd"],
                traces_dod=draft.get("traces_dod", ()),
                depends_on=tuple(dict.fromkeys(depends)),
            )
        )

    return TaskPlan(requirement=prd.requirement, tasks=tasks, lane_agents=agents)
