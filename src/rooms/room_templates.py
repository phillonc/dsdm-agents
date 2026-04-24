"""Templates for Autonomous Delivery Room."""

from __future__ import annotations

from typing import Dict, List

from .room_state import RoomAgentAssignment


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
