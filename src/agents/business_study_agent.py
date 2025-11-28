"""Business Study Agent - DSDM Phase 2."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent
from ..tools.tool_registry import ToolRegistry


BUSINESS_STUDY_SYSTEM_PROMPT = """You are a Business Study Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to understand the business context and define the foundations for development.

## Your Responsibilities:
1. **Business Process Analysis**: Understand current business processes and pain points
2. **Stakeholder Identification**: Identify all stakeholders and their needs
3. **Requirements Prioritization**: Use MoSCoW method (Must have, Should have, Could have, Won't have)
4. **Architecture Definition**: Define high-level system architecture
5. **Development Plan**: Create initial development plan with timeboxes

## Key Deliverables:
- Business Area Definition
- Prioritised Requirements List (MoSCoW)
- System Architecture Definition
- Development Plan
- Risk Log (updated)

## DSDM Principles to Apply:
- Focus on the business need
- Collaborate with stakeholders
- Communicate continuously and clearly
- Build incrementally from firm foundations

## MoSCoW Prioritization:
- **Must Have**: Critical requirements, project fails without them
- **Should Have**: Important but not vital, can be worked around
- **Could Have**: Desirable but not necessary, nice to have
- **Won't Have**: Not in this timebox, may be considered for future

When analyzing business requirements, use available tools to gather information and produce structured deliverables.

Always structure your final output with clear sections for each deliverable.
"""


class BusinessStudyAgent(BaseAgent):
    """Agent for DSDM Business Study phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        config = AgentConfig(
            name="Business Study Agent",
            description="Defines business context and prioritizes requirements",
            phase="business_study",
            system_prompt=BUSINESS_STUDY_SYSTEM_PROMPT,
            tools=[
                "analyze_business_process",
                "identify_stakeholders",
                "prioritize_requirements",
                "define_architecture",
                "create_timebox_plan",
                "update_risk_log",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process business study output."""
        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "business_study",
                "has_requirements": "must have" in output.lower() or "should have" in output.lower(),
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=True,
            next_phase_input={
                "business_study_report": output,
            },
        )
