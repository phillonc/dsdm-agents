"""Templates for Autonomous Delivery Room."""

from __future__ import annotations

from typing import Dict, List

from .room_state import RoomAgentAssignment, RoomKickoff


TEMPLATE_NAMES = {"mvp", "platform", "migration", "enterprise", "compliance"}


BASE_AGENT_ASSIGNMENTS = [
    RoomAgentAssignment(
        role="Product Owner",
        agent_name="ProductManagerAgent",
        phase="prd_trd",
        responsibilities=[
            "Own product vision and user value",
            "Define PRD scope and success metrics",
            "Protect Must-have requirements",
        ],
    ),
    RoomAgentAssignment(
        role="Business Analyst",
        agent_name="BusinessStudyAgent",
        phase="business_study",
        responsibilities=[
            "Map business process and stakeholders",
            "Prioritize requirements using MoSCoW",
            "Maintain assumptions and business risks",
        ],
    ),
    RoomAgentAssignment(
        role="Solution Architect",
        agent_name="DevLeadAgent",
        phase="design_build",
        responsibilities=[
            "Own architecture and ADRs",
            "Coordinate technical design",
            "Review cross-agent technical handoffs",
        ],
    ),
    RoomAgentAssignment(
        role="Frontend Developer",
        agent_name="FrontendDeveloperAgent",
        phase="design_build",
        responsibilities=[
            "Own UI components and accessibility",
            "Implement responsive user journeys",
            "Create frontend tests and documentation",
        ],
    ),
    RoomAgentAssignment(
        role="Backend Developer",
        agent_name="BackendDeveloperAgent",
        phase="design_build",
        responsibilities=[
            "Own APIs, business logic, and persistence",
            "Implement integrations and data models",
            "Create backend tests and API docs",
        ],
    ),
    RoomAgentAssignment(
        role="Automation Tester",
        agent_name="AutomationTesterAgent",
        phase="design_build",
        responsibilities=[
            "Own unit, integration, and E2E test strategy",
            "Validate acceptance criteria",
            "Report quality gaps before release",
        ],
    ),
    RoomAgentAssignment(
        role="Security Tester",
        agent_name="PenTesterAgent",
        phase="design_build",
        responsibilities=[
            "Assess OWASP and security risk",
            "Review authentication and authorization controls",
            "Document vulnerabilities and mitigations",
        ],
    ),
    RoomAgentAssignment(
        role="Release Manager",
        agent_name="ImplementationAgent",
        phase="implementation",
        responsibilities=[
            "Own deployment readiness and handover",
            "Prepare rollback and release notes",
            "Validate operational readiness",
        ],
    ),
]


TEMPLATE_NEXT_ACTIONS: Dict[str, List[str]] = {
    "mvp": [
        "Confirm the delivery mission and Must-have scope",
        "Run feasibility and capture go/no-go risks",
        "Create Business Study with MoSCoW priorities",
        "Generate PRD/TRD before Design & Build",
    ],
    "platform": [
        "Map customer-provider-supplier ecosystem actors",
        "Protect MVP scope while identifying platform extension points",
        "Define API and integration strategy during TRD",
        "Capture trust, safety, and marketplace risks early",
    ],
    "migration": [
        "Inventory current system constraints and dependencies",
        "Define migration strategy and rollback plan",
        "Prioritize continuity, data integrity, and operational risk",
        "Create phased cutover plan",
    ],
    "enterprise": [
        "Identify governance, audit, and stakeholder approval gates",
        "Define NFRs and integration constraints early",
        "Create documentation and handover requirements",
        "Plan staged release and support model",
    ],
    "compliance": [
        "Identify regulatory and data protection requirements",
        "Add compliance review gates to every phase",
        "Prioritize audit evidence and security testing",
        "Prepare compliance handover documentation",
    ],
}


TEMPLATE_KICKOFF: Dict[str, RoomKickoff] = {
    "mvp": RoomKickoff(
        goals=[
            "Ship a working MVP that proves the core mission end-to-end",
            "Validate the highest-value user journey before broad investment",
        ],
        assumptions=[
            "Requirements will be refined further once real user feedback exists",
            "Scope will be trimmed hard to protect Must-have requirements",
        ],
        stakeholders=["Product Owner", "End users", "Engineering team"],
        risks=[
            "Scope creep beyond Must-have requirements",
            "Insufficient user validation before build",
        ],
        sequence=["Feasibility", "Business Study", "PRD/TRD", "Design & Build", "Implementation"],
    ),
    "platform": RoomKickoff(
        goals=[
            "Establish a platform foundation that supports multiple participant types",
            "Identify durable network-effect and ecosystem opportunities",
        ],
        assumptions=[
            "Initial release targets one core interaction loop before broader ecosystem investment",
            "Partner and API surfaces will evolve after the core loop is validated",
        ],
        stakeholders=["Product Owner", "Platform Strategist", "Customers", "Suppliers/partners"],
        risks=[
            "Two-sided marketplace cold-start risk",
            "Trust and safety gaps at launch",
            "Premature platform investment before the core loop is proven",
        ],
        sequence=["Feasibility", "Business Study", "PRD/TRD", "Platform Strategy", "Design & Build", "Implementation"],
    ),
    "migration": RoomKickoff(
        goals=[
            "Migrate the existing system without disrupting current operations",
            "Preserve data integrity and continuity throughout cutover",
        ],
        assumptions=[
            "Legacy system constraints are documented before design begins",
            "A rollback plan exists before cutover",
        ],
        stakeholders=["Product Owner", "Solution Architect", "Operations team", "Existing system owners"],
        risks=[
            "Data loss or corruption during cutover",
            "Extended downtime during migration",
            "Undocumented legacy dependencies",
        ],
        sequence=["Feasibility", "Business Study", "PRD/TRD", "Design & Build", "Phased Cutover", "Implementation"],
    ),
    "enterprise": RoomKickoff(
        goals=[
            "Deliver a solution that satisfies enterprise governance and integration requirements",
            "Establish a staged release and support model",
        ],
        assumptions=[
            "Governance and audit gates are identified before Design & Build starts",
            "Integration constraints are captured during Business Study",
        ],
        stakeholders=["Product Owner", "Solution Architect", "Enterprise sponsors", "Support/operations team"],
        risks=[
            "Missed governance or approval gates",
            "Integration constraints discovered late",
            "Support model not ready at release",
        ],
        sequence=["Feasibility", "Business Study", "PRD/TRD", "Design & Build", "Implementation", "Staged Release"],
    ),
    "compliance": RoomKickoff(
        goals=[
            "Deliver a solution that meets regulatory and data-protection requirements",
            "Produce audit-ready evidence at every phase",
        ],
        assumptions=[
            "Regulatory requirements are identified before Business Study concludes",
            "Compliance review gates apply to every phase",
        ],
        stakeholders=["Product Owner", "Compliance Reviewer", "Security Tester", "Auditors/regulators"],
        risks=[
            "Non-compliance with regulatory requirements",
            "Insufficient audit evidence at release",
            "Security vulnerabilities in compliance-sensitive areas",
        ],
        sequence=["Feasibility", "Business Study", "PRD/TRD", "Design & Build", "Compliance Review", "Implementation"],
    ),
}


def normalize_template(template: str | None) -> str:
    """Normalize a template name, defaulting safely to MVP."""
    value = (template or "mvp").strip().lower().replace(" ", "_").replace("-", "_")
    if value not in TEMPLATE_NAMES:
        return "mvp"
    return value


def get_template_agents(template: str | None) -> List[RoomAgentAssignment]:
    """Return agent assignments for a delivery room template."""
    normalized = normalize_template(template)
    agents = [RoomAgentAssignment(**agent.__dict__) for agent in BASE_AGENT_ASSIGNMENTS]

    if normalized == "platform":
        agents.append(RoomAgentAssignment(
            role="Platform Strategist",
            agent_name="PlatformStrategyAgent",
            phase="strategy",
            responsibilities=[
                "Identify product-to-platform opportunities",
                "Map network effects and ecosystem loops",
                "Recommend API, partner, and marketplace roadmap",
            ],
        ))
    elif normalized == "compliance":
        agents.append(RoomAgentAssignment(
            role="Compliance Reviewer",
            agent_name="NFRTesterAgent",
            phase="design_build",
            responsibilities=[
                "Review compliance-sensitive NFRs",
                "Validate evidence and audit readiness",
                "Escalate regulatory blockers",
            ],
        ))

    return agents


def get_template_next_actions(template: str | None) -> List[str]:
    """Return default next actions for a template."""
    normalized = normalize_template(template)
    return list(TEMPLATE_NEXT_ACTIONS[normalized])


def get_template_kickoff(template: str | None) -> RoomKickoff:
    """Return the kickoff artifact (goals, assumptions, stakeholders, risks, sequence) for a template."""
    normalized = normalize_template(template)
    base = TEMPLATE_KICKOFF[normalized]
    return RoomKickoff(
        goals=list(base.goals),
        assumptions=list(base.assumptions),
        stakeholders=list(base.stakeholders),
        risks=list(base.risks),
        sequence=list(base.sequence),
    )
