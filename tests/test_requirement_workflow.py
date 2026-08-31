"""Tests for the Requirement → PRD → TRD → TASKS workflow (spec WF-PRTT-001).

The invariants here are the ones section 9 of the spec requires *every*
implementation of the workflow to hold — the DSDM-Agency and lhs-agents
repositories assert the same ones against their own ports.
"""

import json

import pytest

from src.tools.dsdm_tools import create_dsdm_tool_registry
from src.workflow import (
    DOD_FILENAME,
    LANE_ORDER,
    LANE_ROLE_IDS,
    PERSPECTIVES,
    PRD_FILENAME,
    TASKS_FILENAME,
    TRD_FILENAME,
    GateError,
    IntakeError,
    build_definition_of_done,
    build_prd,
    build_task_plan,
    build_trd,
    document_directory,
    lanes_for,
    normalise_requirement,
    render_definition_of_done,
    render_prd,
    render_tasks,
    render_trd,
    run_workflow,
)
from src.workflow.model import PRD, Requirement, TRD

REQUIREMENT = """# Merchant self-serve onboarding

Merchants should be able to join without raising a support ticket.

- Merchants can register an account and log in with email
- The onboarding UI shows progress across four steps
- Store merchant profile data and make it searchable
- Deploy the flow behind the existing CI pipeline
"""


@pytest.fixture
def prd():
    return build_prd(normalise_requirement(REQUIREMENT))


@pytest.fixture
def trd(prd):
    return build_trd(prd)


@pytest.fixture
def dod(prd, trd):
    return build_definition_of_done(prd, trd)


# -- stage 0: intake --------------------------------------------------------

def test_every_bullet_becomes_one_requirement_item():
    requirement = normalise_requirement(REQUIREMENT)
    assert requirement.title == "Merchant self-serve onboarding"
    assert [item.id for item in requirement.items] == ["REQ-001", "REQ-002", "REQ-003", "REQ-004"]


def test_description_without_bullets_becomes_a_single_item():
    requirement = normalise_requirement("Add a refund button\nUsers need to refund an order.")
    assert [item.text for item in requirement.items] == ["Users need to refund an order."]


def test_inline_priority_marker_overrides_the_default():
    requirement = normalise_requirement("Checkout\n- Apply a discount code (Must)\n- Save the basket")
    assert requirement.items[0].priority == "M"
    assert requirement.items[0].text == "Apply a discount code"
    assert requirement.items[1].priority == "S"


def test_intake_rejects_a_requirement_without_a_title():
    with pytest.raises(IntakeError):
        normalise_requirement("   ")


# -- routing ----------------------------------------------------------------

def test_keywords_match_at_a_word_boundary_not_mid_word():
    # "build" and "requirement" both contain "ui"; neither is frontend work.
    assert "frontend" not in lanes_for("Build the stated requirement")
    assert "frontend" in lanes_for("The UI shows progress")


def test_unmatched_requirement_falls_to_the_default_lane():
    assert lanes_for("Something entirely unrelated") == ("backend",)


# -- stages -----------------------------------------------------------------

def test_prd_numbers_requirements_in_intake_order(prd):
    assert [fr.id for fr in prd.functional] == [
        "PRD-FR-001", "PRD-FR-002", "PRD-FR-003", "PRD-FR-004",
    ]


def test_prd_always_carries_baseline_non_functional_requirements(prd):
    assert {"Performance", "Security", "Accessibility"} <= {n.category for n in prd.non_functional}


def test_every_functional_requirement_reaches_a_component(prd, trd, dod):
    for fr in prd.functional:
        assert trd.components_for(fr.id), f"{fr.id} has no component"


def test_qa_component_covers_every_functional_requirement(prd, trd, dod):
    qa = next(c for c in trd.components if c.lane == "qa")
    assert set(qa.satisfies) == {fr.id for fr in prd.functional}


def test_components_are_numbered_in_lane_order(trd):
    lanes = [c.lane for c in trd.components]
    assert lanes == sorted(lanes, key=LANE_ORDER.index)


def test_every_component_reaches_at_least_one_task(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    for component in trd.components:
        assert plan.tasks_for_component(component.id), f"{component.id} has no task"


def test_each_agent_gets_its_own_task_list(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    for lane in plan.lanes():
        assert all(task.agent == plan.lane_agents[lane] for task in plan.for_lane(lane))


def test_qa_lane_always_has_tasks(prd, trd, dod):
    assert build_task_plan(prd, trd, dod).for_lane("qa")


def test_everything_waits_on_the_architecture_sign_off(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    gate = plan.for_lane("architecture")[0]
    assert all(gate.id in t.depends_on for t in plan.tasks if t.id != gate.id)


def test_assignments_merge_the_lanes_one_agent_owns(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    # The Backend Developer Agent owns both the data and backend lanes; keying
    # on the agent name without merging would report only the last of them.
    backend = plan.assignments()["Backend Developer Agent"]
    assert set(backend["lanes"]) == {"data", "backend"}
    assert backend["task_count"] == len(plan.for_lane("data")) + len(plan.for_lane("backend"))


def test_every_lane_maps_to_a_role_definition_id():
    assert set(LANE_ROLE_IDS) == set(LANE_ORDER)


# -- gates ------------------------------------------------------------------

def test_prd_stage_is_gated():
    with pytest.raises(GateError):
        build_prd(Requirement(title="No items were extracted"))


def test_trd_stage_is_gated():
    with pytest.raises(GateError):
        build_trd(PRD(requirement=Requirement(title="Empty"), functional=[], non_functional=[]))


def test_tasks_stage_is_gated(prd, dod):
    with pytest.raises(GateError):
        build_task_plan(prd, TRD(requirement=prd.requirement, components=[], constraints=[], risks=[]), dod)


# -- documents --------------------------------------------------------------

def test_documents_carry_the_specified_headings(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    assert "## 5. Functional Requirements" in render_prd(prd)
    assert "## 2. Architecture Summary" in render_trd(trd, prd)
    assert "## 3. Tasks by Agent" in render_tasks(plan, trd)
    assert "## 3. Criteria by Feature" in render_definition_of_done(dod, prd, trd)


def test_tasks_document_has_one_section_per_agent(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    tasks_md = render_tasks(plan, trd)
    for lane in plan.lanes():
        assert f"{plan.lane_agents[lane]} — `{lane}`" in tasks_md


def test_renderers_are_pure_so_reruns_are_identical():
    first = run_workflow(REQUIREMENT, write=False)
    second = run_workflow(REQUIREMENT, write=False)
    assert first.documents == second.documents


# -- output location --------------------------------------------------------

def test_a_lone_requirement_is_its_own_project():
    assert document_directory("refund-an-order") == "generated/refund-an-order/docs"


def test_a_named_project_nests_the_requirement_under_its_docs():
    assert document_directory("refund-an-order", project="Merchant Portal") == \
        "generated/merchant-portal/docs/refund-an-order"


def test_run_workflow_writes_all_four_documents(tmp_path):
    result = run_workflow(REQUIREMENT, output_root=str(tmp_path))
    directory = tmp_path / "merchant-self-serve-onboarding"
    for name in (PRD_FILENAME, TRD_FILENAME, DOD_FILENAME, TASKS_FILENAME):
        assert (directory / name).read_text(encoding="utf-8")
    assert set(result.written) == {PRD_FILENAME, TRD_FILENAME, DOD_FILENAME, TASKS_FILENAME}


def test_a_gate_failure_writes_nothing(tmp_path):
    with pytest.raises(IntakeError):
        run_workflow("", output_root=str(tmp_path))
    assert list(tmp_path.iterdir()) == []


# -- tool registry ----------------------------------------------------------

def test_workflow_tools_are_registered():
    registry = create_dsdm_tool_registry()
    assert registry.get("run_requirement_workflow")
    assert registry.get("generate_task_breakdown")


def test_task_breakdown_tool_reports_every_agents_work():
    registry = create_dsdm_tool_registry()
    payload = json.loads(
        registry.get("generate_task_breakdown").execute(requirement=REQUIREMENT)
    )
    assert payload["success"] is True
    assert payload["task_count"] == sum(a["task_count"] for a in payload["assignments"].values())
    assert payload["assignments"]["Automation Tester Agent"]["role_ids"] == ["automation-tester"]


def test_run_workflow_tool_writes_the_documents(tmp_path):
    registry = create_dsdm_tool_registry()
    payload = json.loads(
        registry.get("run_requirement_workflow").execute(
            requirement=REQUIREMENT, output_root=str(tmp_path)
        )
    )
    assert payload["success"] is True
    assert set(payload["documents"]) == {PRD_FILENAME, TRD_FILENAME, DOD_FILENAME, TASKS_FILENAME}


def test_workflow_tool_reports_a_gate_failure_rather_than_raising():
    registry = create_dsdm_tool_registry()
    payload = json.loads(registry.get("run_requirement_workflow").execute(requirement="   "))
    assert payload["success"] is False
    assert payload["documents_written"] == []


# -- Definition of Done -----------------------------------------------------

def test_every_feature_gets_all_three_perspectives(prd, dod):
    for fr in prd.functional:
        assert {c.perspective for c in dod.for_feature(fr.id)} == set(PERSPECTIVES)


def test_every_applicable_criterion_reaches_exactly_one_done_check(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    checked = [ref for task in plan.tasks for ref in task.traces_dod]
    assert sorted(checked) == sorted(c.id for c in dod.all_criteria() if c.applies)


def test_each_lane_closes_with_a_done_check(prd, trd, dod):
    plan = build_task_plan(prd, trd, dod)
    for lane in plan.lanes():
        assert plan.for_lane(lane)[-1].traces_dod


def test_the_mandatory_bars_are_always_present(dod):
    universal = " ".join(c.text for c in dod.universal)
    assert "WCAG 2.2 AAA" in universal
    assert "Business Ambassador" in universal
    assert "instrumented" in universal
    assert "at least 80%" in universal
    assert "rollback plan" in universal.lower()


def test_an_inapplicable_criterion_is_owned_by_nobody():
    backend_only = build_prd(normalise_requirement(
        "Nightly settlement export\n- Export settled orders to the finance system every night"
    ))
    trd = build_trd(backend_only)
    dod = build_definition_of_done(backend_only, trd)
    plan = build_task_plan(backend_only, trd, dod)

    accessibility = next(c for c in dod.universal if "WCAG" in c.text)
    assert accessibility.applies is False
    checked = {ref for task in plan.tasks for ref in task.traces_dod}
    assert accessibility.id not in checked


def test_done_stage_is_gated(prd):
    with pytest.raises(GateError):
        build_definition_of_done(
            PRD(requirement=prd.requirement, functional=[], non_functional=[]), build_trd(prd)
        )


def test_definition_of_done_tool_reports_owners_and_applicability():
    registry = create_dsdm_tool_registry()
    payload = json.loads(
        registry.get("define_what_done_means").execute(requirement=REQUIREMENT)
    )
    assert payload["success"] is True
    assert payload["by_owner"]
    assert all(entry["perspective"] for entry in payload["universal"])
    assert all(entry["evidence"] for entry in payload["universal"])
