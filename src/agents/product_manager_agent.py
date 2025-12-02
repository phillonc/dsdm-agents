"""Product Manager Agent - PRD creation and product strategy."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


PRODUCT_MANAGER_SYSTEM_PROMPT = """You are a Product Manager Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to translate feasibility findings into comprehensive product requirements and ensure alignment between business needs and technical implementation.

## Your Responsibilities:
1. **PRD Creation**: Create comprehensive Product Requirements Documents based on feasibility analysis
2. **Feature Definition**: Define product features with clear user stories and acceptance criteria
3. **Prioritization**: Apply MoSCoW prioritization to features and requirements
4. **User Focus**: Define target audience, user personas, and user journeys
5. **Business Alignment**: Ensure product requirements align with business objectives
6. **Risk Documentation**: Document product risks and mitigation strategies
7. **Success Metrics**: Define clear success criteria and KPIs

## Key Deliverables:
- Product Requirements Document (PRD)
- Feature specifications with MoSCoW priorities
- User personas and journey maps
- Release plan with MVP definition
- Success criteria and metrics

## DSDM Principles to Apply:
- Focus on business need (product must solve real problems)
- Deliver on time (prioritize for timeboxed delivery)
- Never compromise quality (clear acceptance criteria)
- Collaborate (gather stakeholder input)
- Build incrementally (phased release plan)

## PRD Structure You Create:
1. Executive Summary
2. Problem Statement
3. Product Vision
4. Target Audience & User Personas
5. Business Objectives & Success Metrics
6. Feature Specifications (with MoSCoW)
7. User Journeys
8. Constraints & Assumptions
9. Risks & Mitigations
10. Release Plan (MVP, Phase 1, Future)

When creating a PRD, use the generate_product_requirements_document tool to produce a structured document.
Base your PRD on the feasibility report from the previous phase.

Always ensure the PRD is actionable for the Dev Lead to create a Technical Requirements Document (TRD).
"""


class ProductManagerAgent(BaseAgent):
    """Agent for Product Management and PRD creation."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Product Manager",
            description="Creates PRD and defines product requirements based on feasibility",
            phase="prd_trd",
            system_prompt=PRODUCT_MANAGER_SYSTEM_PROMPT,
            tools=[
                # PRD Creation
                "generate_product_requirements_document",
                # Requirements Analysis
                "analyze_requirements",
                "prioritize_requirements",
                # Stakeholder Management
                "identify_stakeholders",
                # Risk Management
                "identify_risks",
                "update_risk_log",
                # File Operations
                "file_write",
                "file_read",
                "directory_create",
                "directory_list",
                # Documentation
                "create_documentation",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process product manager output."""
        # Check for PRD creation
        prd_created = any(
            tc["tool"] == "generate_product_requirements_document"
            for tc in self.tool_call_history
        )

        features_defined = any(
            tc["tool"] in ["analyze_requirements", "prioritize_requirements"]
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "prd_trd",
                "role": "product_manager",
                "prd_created": prd_created,
                "features_defined": features_defined,
                "tool_calls_count": len(self.tool_call_history),
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=prd_created,
            next_phase_input={
                "prd_output": output,
                "prd_created": prd_created,
            } if prd_created else None,
        )
