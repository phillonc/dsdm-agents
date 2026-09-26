"""Single source of truth for every DSDM agent role.

Phase 2 of the Pi Agent Runtime migration
(docs/category-defining-features/11-pi-agent-runtime/TRD.md sections 15/18,
PAR-PRD-FR-002). Before this module existed, each role's system prompt,
tool list, and default execution mode lived only inside its `BaseAgent`
subclass's `__init__`, duplicated a second time (by hand, with different
prose) in the corresponding `.github/agents/*.agent.md` file for GitHub
Copilot CLI. Nothing detected drift between the two.

This module does not re-type any of that content a second time — every
`RoleDefinition` below is built from the same module-level constants each
agent class's own `AgentConfig(...)` call uses (e.g. `FEASIBILITY_TOOLS`,
`FEASIBILITY_SYSTEM_PROMPT` in `feasibility_agent.py`). It is an aggregation
point, not a duplicate, and it is what `pi_session_runner.py` (Phase 3)
queries to build a pi.dev session for a role, and what
`tests/test_role_definitions.py` checks for internal consistency.

`.github/agents/*.agent.md` is intentionally NOT auto-generated from this
registry. Its prose (Responsibilities, DSDM principles applied, working
style, MCP integration notes, ...) is hand-authored and valuable; the
`tools:` frontmatter it uses is GitHub Copilot CLI's own generic tool
taxonomy (`read`/`write`/`edit`/`search`/`execute`), not DSDM tool names, so
there is no meaningful byte-for-byte comparison to make there. What *is*
checked is structural: every role_id with a Copilot CLI counterpart names
the `.agent.md` file that exists for it, and every tool this registry lists
actually exists in `ToolRegistry` — see `tests/test_role_definitions.py`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .automation_tester_agent import AUTOMATION_TESTER_SYSTEM_PROMPT, AUTOMATION_TESTER_TOOLS
from .backend_developer_agent import BACKEND_DEVELOPER_SYSTEM_PROMPT, BACKEND_DEVELOPER_TOOLS
from .base_agent import AgentMode
from .business_study_agent import BUSINESS_STUDY_SYSTEM_PROMPT, BUSINESS_STUDY_TOOLS
from .change_control_agent import CHANGE_CONTROL_SYSTEM_PROMPT, CHANGE_CONTROL_TOOLS
from .design_build_agent import DESIGN_BUILD_SYSTEM_PROMPT, DESIGN_BUILD_TOOLS
from .dev_lead_agent import DEV_LEAD_SYSTEM_PROMPT, DEV_LEAD_TOOLS
from .devops_agent import DEVOPS_SYSTEM_PROMPT, DEVOPS_TOOLS
from .feasibility_agent import FEASIBILITY_SYSTEM_PROMPT, FEASIBILITY_TOOLS
from .frontend_developer_agent import FRONTEND_DEVELOPER_SYSTEM_PROMPT, FRONTEND_DEVELOPER_TOOLS
from .functional_model_agent import FUNCTIONAL_MODEL_SYSTEM_PROMPT, FUNCTIONAL_MODEL_TOOLS
from .git_pin_coding_agent import (
    GIT_PIN_CODING_SYSTEM_PROMPT,
    GIT_PIN_CODING_TOOLS,
    GIT_PIN_REVIEW_SYSTEM_PROMPT,
    GIT_PIN_REVIEW_TOOLS,
)
from .implementation_agent import IMPLEMENTATION_SYSTEM_PROMPT, IMPLEMENTATION_TOOLS
from .nfr_tester_agent import NFR_TESTER_SYSTEM_PROMPT, NFR_TESTER_TOOLS
from .pen_tester_agent import PEN_TESTER_SYSTEM_PROMPT, PEN_TESTER_TOOLS
from .product_manager_agent import PRODUCT_MANAGER_SYSTEM_PROMPT, PRODUCT_MANAGER_TOOLS
from .workflow_modes import WorkflowMode


@dataclass(frozen=True)
class RoleDefinition:
    """Everything needed to run one DSDM role, on either execution engine."""

    role_id: str  # kebab-case; matches the .agent.md filename stem where one exists
    display_name: str  # AgentConfig.name equivalent
    phase: str  # AgentConfig.phase equivalent (DSDMPhase value, or "design_build" for a sub-role)
    description: str  # AgentConfig.description equivalent — short, not the .agent.md prose
    system_prompt: str
    tools: List[str]  # DSDM tool names, as registered in ToolRegistry
    default_mode: AgentMode
    default_workflow_mode: WorkflowMode = WorkflowMode.AGENT_WRITES_CODE
    model: Optional[str] = None  # None = resolve via the phase-based default (see providers.py)
    handoffs: List[str] = field(default_factory=list)  # role_ids this role can hand off to
    agent_md_name: Optional[str] = None  # .github/agents/<agent_md_name>.agent.md; None if no Copilot CLI file exists


_DEV_LEAD_HANDOFFS = ["frontend-developer", "backend-developer", "automation-tester", "nfr-tester", "pen-tester"]
_DESIGN_BUILD_HANDOFFS = ["dev-lead", "frontend-developer", "backend-developer", "automation-tester"]


ROLE_DEFINITIONS: Dict[str, RoleDefinition] = {
    role.role_id: role
    for role in [
        RoleDefinition(
            role_id="feasibility",
            display_name="Feasibility Agent",
            phase="feasibility",
            description="Assesses project viability and DSDM suitability",
            system_prompt=FEASIBILITY_SYSTEM_PROMPT,
            tools=FEASIBILITY_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="feasibility",
        ),
        RoleDefinition(
            role_id="product-manager",
            display_name="Product Manager",
            phase="prd_trd",
            description="Creates PRD and defines product requirements based on feasibility",
            system_prompt=PRODUCT_MANAGER_SYSTEM_PROMPT,
            tools=PRODUCT_MANAGER_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="product-manager",
        ),
        RoleDefinition(
            role_id="business-study",
            display_name="Business Study Agent",
            phase="business_study",
            description="Defines business context and prioritizes requirements",
            system_prompt=BUSINESS_STUDY_SYSTEM_PROMPT,
            tools=BUSINESS_STUDY_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="business-study",
        ),
        RoleDefinition(
            role_id="functional-model",
            display_name="Functional Model Agent",
            phase="functional_model",
            description="Creates and refines functional prototypes iteratively",
            system_prompt=FUNCTIONAL_MODEL_SYSTEM_PROMPT,
            tools=FUNCTIONAL_MODEL_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="functional-model",
        ),
        RoleDefinition(
            role_id="design-build",
            display_name="Design & Build Agent",
            phase="design_build",
            description="Builds production-ready system from prototypes",
            system_prompt=DESIGN_BUILD_SYSTEM_PROMPT,
            tools=DESIGN_BUILD_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            handoffs=_DESIGN_BUILD_HANDOFFS,
            agent_md_name="design-build",
        ),
        RoleDefinition(
            role_id="dev-lead",
            display_name="Dev Lead",
            phase="design_build",
            description="Technical leadership and architecture coordination",
            system_prompt=DEV_LEAD_SYSTEM_PROMPT,
            tools=DEV_LEAD_TOOLS,
            default_mode=AgentMode.HYBRID,
            handoffs=_DEV_LEAD_HANDOFFS,
            agent_md_name="dev-lead",
        ),
        RoleDefinition(
            role_id="frontend-developer",
            display_name="Frontend Developer",
            phase="design_build",
            description="UI/UX implementation and frontend development",
            system_prompt=FRONTEND_DEVELOPER_SYSTEM_PROMPT,
            tools=FRONTEND_DEVELOPER_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="frontend-developer",
        ),
        RoleDefinition(
            role_id="backend-developer",
            display_name="Backend Developer",
            phase="design_build",
            description="Server-side logic and API development",
            system_prompt=BACKEND_DEVELOPER_SYSTEM_PROMPT,
            tools=BACKEND_DEVELOPER_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="backend-developer",
        ),
        RoleDefinition(
            role_id="automation-tester",
            display_name="Automation Tester",
            phase="design_build",
            description="Automated testing and quality assurance",
            system_prompt=AUTOMATION_TESTER_SYSTEM_PROMPT,
            tools=AUTOMATION_TESTER_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name="automation-tester",
        ),
        RoleDefinition(
            role_id="nfr-tester",
            display_name="NFR Tester",
            phase="design_build",
            description="Performance, reliability, and non-functional testing",
            system_prompt=NFR_TESTER_SYSTEM_PROMPT,
            tools=NFR_TESTER_TOOLS,
            default_mode=AgentMode.HYBRID,
            agent_md_name="nfr-tester",
        ),
        RoleDefinition(
            role_id="change-control",
            display_name="Change Control Agent",
            phase="design_build",
            description="Arbitrates mid-timebox scope-change requests via MoSCoW trade-offs",
            system_prompt=CHANGE_CONTROL_SYSTEM_PROMPT,
            tools=CHANGE_CONTROL_TOOLS,
            default_mode=AgentMode.HYBRID,
            handoffs=["business-study"],
            agent_md_name="change-control",
        ),
        RoleDefinition(
            role_id="pen-tester",
            display_name="Penetration Tester",
            phase="design_build",
            description="Security testing and vulnerability assessment",
            system_prompt=PEN_TESTER_SYSTEM_PROMPT,
            tools=PEN_TESTER_TOOLS,
            default_mode=AgentMode.MANUAL,
            agent_md_name="pen-tester",
        ),
        RoleDefinition(
            role_id="implementation",
            display_name="Implementation Agent",
            phase="implementation",
            description="Deploys system to production and ensures successful transition",
            system_prompt=IMPLEMENTATION_SYSTEM_PROMPT,
            tools=IMPLEMENTATION_TOOLS,
            # ImplementationAgent.__init__'s own default is HYBRID. main.py forces MANUAL for
            # this phase even under --mode automated, and README documents "Manual" as the
            # operational default — that's a deployment-policy override layered on top of the
            # role's intrinsic default, not a second definition of it. See dsdm_orchestrator.py.
            default_mode=AgentMode.HYBRID,
            agent_md_name="implementation",
        ),
        RoleDefinition(
            role_id="devops",
            display_name="DevOps Agent",
            phase="devops",
            description="Enables development principles through DevOps practices",
            system_prompt=DEVOPS_SYSTEM_PROMPT,
            tools=DEVOPS_TOOLS,
            default_mode=AgentMode.HYBRID,
            agent_md_name="devops",
        ),
        RoleDefinition(
            role_id="git-pin-coder",
            display_name="Git Pin Coding Agent",
            phase="design_build",
            description="High-throughput coding agent with parallel tool execution",
            system_prompt=GIT_PIN_CODING_SYSTEM_PROMPT,
            tools=GIT_PIN_CODING_TOOLS,
            default_mode=AgentMode.AUTOMATED,
            agent_md_name=None,  # no GitHub Copilot CLI counterpart — pi.dev/Git Pin specific
        ),
        RoleDefinition(
            role_id="git-pin-reviewer",
            display_name="Git Pin Review Agent",
            phase="design_build",
            description="High-throughput code review with parallel analysis",
            system_prompt=GIT_PIN_REVIEW_SYSTEM_PROMPT,
            tools=GIT_PIN_REVIEW_TOOLS,
            default_mode=AgentMode.HYBRID,
            agent_md_name=None,
        ),
    ]
}


def get_role(role_id: str) -> RoleDefinition:
    """Look up a role by id, raising a clear error if it doesn't exist."""
    try:
        return ROLE_DEFINITIONS[role_id]
    except KeyError:
        raise KeyError(f"Unknown role_id {role_id!r}. Known roles: {sorted(ROLE_DEFINITIONS)}") from None
