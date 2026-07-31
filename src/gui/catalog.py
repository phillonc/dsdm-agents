"""Business-facing metadata for the console.

The CLI speaks in phase ids (`business_study`), agent modes (`hybrid`) and
runtimes (`pi`). Business users should not have to. This module is the single
place where those internal identifiers are given plain-English names,
descriptions and expected deliverables, so the UI never has to invent its own
labels and the mapping back to CLI arguments stays honest.

Every `id` here is the exact value the CLI/orchestrator expects.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# --- Delivery stages (DSDMPhase values) ------------------------------------

STAGES: List[Dict[str, Any]] = [
    {
        "id": "feasibility",
        "name": "Feasibility",
        "question": "Is this worth doing?",
        "summary": (
            "Assesses viability, surfaces the biggest risks up front and gives a "
            "Go / No-Go recommendation before any money is committed."
        ),
        "deliverables": ["Go / No-Go recommendation", "Top risks", "DSDM fit assessment"],
        "in_full_delivery": True,
    },
    {
        "id": "business_study",
        "name": "Business Study",
        "question": "What does the business actually need?",
        "summary": (
            "Maps stakeholders and business processes, then prioritises every "
            "requirement as Must / Should / Could / Won't have."
        ),
        "deliverables": ["Stakeholder map", "Prioritised requirements", "Outline architecture"],
        "in_full_delivery": True,
    },
    {
        "id": "prd_trd",
        "name": "Requirements",
        "question": "What are we building, precisely?",
        "summary": (
            "The Product Manager writes the product requirements and the Dev Lead "
            "writes the matching technical requirements, so business and "
            "engineering sign off on the same scope."
        ),
        "deliverables": ["Product Requirements Document", "Technical Requirements Document"],
        "in_full_delivery": True,
    },
    {
        "id": "functional_model",
        "name": "Functional Model",
        "question": "Does the proposed solution work for users?",
        "summary": (
            "Builds working prototypes in short iterations and folds user feedback "
            "back in before the build phase begins."
        ),
        "deliverables": ["Iterative prototypes", "Captured feedback", "Refined requirements"],
        "in_full_delivery": True,
    },
    {
        "id": "design_build",
        "name": "Design & Build",
        "question": "Can we build it to a quality standard?",
        "summary": (
            "A full delivery team - lead, frontend, backend, test and security - "
            "produces production code, automated tests and technical documentation."
        ),
        "deliverables": ["Production code", "Automated tests", "Technical documentation"],
        "in_full_delivery": True,
    },
    {
        "id": "implementation",
        "name": "Implementation",
        "question": "How do we get it live and handed over?",
        "summary": (
            "Prepares the deployment plan, smoke tests and handover pack so the "
            "solution can go live safely and be supported afterwards."
        ),
        "deliverables": ["Deployment plan", "Smoke tests", "Handover pack"],
        "in_full_delivery": True,
    },
    {
        "id": "devops",
        "name": "DevOps & Quality",
        "question": "Is it safe, tested and repeatable?",
        "summary": (
            "A cross-cutting review of quality gates, CI/CD, infrastructure and "
            "security scanning. Run it at any point, not only at the end."
        ),
        "deliverables": ["Quality gate report", "Pipeline definition", "Security scan results"],
        "in_full_delivery": False,
    },
]

STAGE_IDS = [stage["id"] for stage in STAGES]
FULL_DELIVERY_STAGE_IDS = [stage["id"] for stage in STAGES if stage["in_full_delivery"]]


# --- Oversight levels (AgentMode values) -----------------------------------

OVERSIGHT_LEVELS: List[Dict[str, Any]] = [
    {
        "id": "automated",
        "name": "Hands-off",
        "summary": "Agents work autonomously and only report back when a stage is finished.",
        "detail": "Fastest option. Best for exploratory work, early stages and low-risk projects.",
        "recommended": True,
    },
    {
        "id": "hybrid",
        "name": "Guided",
        "summary": "Agents work on their own but ask you to approve the decisions that matter.",
        "detail": "Balanced option. You are asked to approve sensitive actions before they happen.",
        "recommended": False,
    },
    {
        "id": "manual",
        "name": "Full control",
        "summary": "Every action waits for your approval before it runs.",
        "detail": "Slowest option, and the right one for regulated or production-facing work.",
        "recommended": False,
    },
]


# --- Delivery room templates -----------------------------------------------

ROOM_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "mvp",
        "name": "MVP",
        "summary": "Prove the idea quickly with a tightly protected Must-have scope.",
    },
    {
        "id": "platform",
        "name": "Platform",
        "summary": "Multi-sided products where APIs, partners and extension points matter.",
    },
    {
        "id": "migration",
        "name": "Migration",
        "summary": "Moving off a legacy system with parallel running and cutover planning.",
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "summary": "Larger programmes with formal governance and multiple stakeholder groups.",
    },
    {
        "id": "compliance",
        "name": "Compliance",
        "summary": "Regulated delivery where audit trail and evidence are first-class outputs.",
    },
]


# --- Execution runtimes ----------------------------------------------------

RUNTIMES: List[Dict[str, Any]] = [
    {
        "id": "legacy",
        "name": "Built-in",
        "summary": "The standard agent engine. No extra setup required.",
    },
    {
        "id": "pi",
        "name": "pi.dev",
        "summary": "Runs eligible stages on the pi.dev engine. Required for private/self-hosted models.",
    },
]


PROVIDERS: List[Dict[str, Any]] = [
    {"id": "anthropic", "name": "Anthropic", "key_env": "ANTHROPIC_API_KEY"},
    {"id": "openai", "name": "OpenAI", "key_env": "OPENAI_API_KEY"},
    {"id": "gemini", "name": "Google Gemini", "key_env": "GEMINI_API_KEY"},
    {"id": "ollama", "name": "Ollama (local)", "key_env": None},
    {"id": "vllm", "name": "Private vLLM", "key_env": None},
]


# --- Progress events -------------------------------------------------------

# ProgressEvent values rendered as something a non-engineer can read.
EVENT_LABELS: Dict[str, str] = {
    "started": "Started",
    "thinking": "Thinking",
    "tool_calling": "Working",
    "tool_completed": "Step complete",
    "iteration": "Progress",
    "processing": "Processing",
    "completed": "Complete",
    "error": "Problem",
}


def stage_by_id(stage_id: str) -> Optional[Dict[str, Any]]:
    """Return the stage descriptor for `stage_id`, or None when unknown."""
    for stage in STAGES:
        if stage["id"] == stage_id:
            return stage
    return None


def stage_name(stage_id: Optional[str]) -> str:
    """Return a human-readable stage name, falling back to a tidied id."""
    if not stage_id:
        return "-"
    stage = stage_by_id(stage_id)
    if stage:
        return str(stage["name"])
    return stage_id.replace("_", " ").title()


def catalog() -> Dict[str, Any]:
    """Return everything the UI needs to render its choices."""
    return {
        "stages": STAGES,
        "oversightLevels": OVERSIGHT_LEVELS,
        "roomTemplates": ROOM_TEMPLATES,
        "runtimes": RUNTIMES,
        "providers": [
            {"id": item["id"], "name": item["name"]} for item in PROVIDERS
        ],
        "fullDeliveryStageIds": FULL_DELIVERY_STAGE_IDS,
    }
