"""Feasibility Study Agent - DSDM Phase 1."""

from dataclasses import field
from typing import Any, Callable, Dict, List, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent
from ..tools.tool_registry import ToolRegistry


FEASIBILITY_SYSTEM_PROMPT = """You are a Feasibility Study Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to assess whether a proposed project is viable and suitable for DSDM methodology.

## Your Responsibilities:
1. **Technical Feasibility**: Assess if the project can be built with available technology
2. **Business Feasibility**: Evaluate if the project aligns with business objectives
3. **Resource Assessment**: Determine if necessary resources (people, budget, time) are available
4. **Risk Identification**: Identify potential risks and constraints
5. **DSDM Suitability**: Determine if DSDM is the right methodology for this project

## Key Deliverables:
- Feasibility Report with go/no-go recommendation
- Initial risk assessment
- High-level project outline
- Resource requirements estimate

## DSDM Principles to Apply:
- Focus on business need
- Deliver on time (timeboxing assessment)
- Never compromise quality
- Build incrementally from firm foundations

When analyzing a project, use available tools to gather information and produce a structured feasibility assessment.

Always structure your final output as a JSON-formatted feasibility report.
"""


class FeasibilityAgent(BaseAgent):
    """Agent for DSDM Feasibility Study phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        config = AgentConfig(
            name="Feasibility Agent",
            description="Assesses project viability and DSDM suitability",
            phase="feasibility",
            system_prompt=FEASIBILITY_SYSTEM_PROMPT,
            tools=[
                "analyze_requirements",
                "assess_technical_feasibility",
                "estimate_resources",
                "identify_risks",
                "check_dsdm_suitability",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process feasibility study output."""
        # Parse for go/no-go recommendation
        go_recommendation = "go" in output.lower() and "no-go" not in output.lower()

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "feasibility",
                "recommendation": "go" if go_recommendation else "no-go",
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=go_recommendation,
            next_phase_input={
                "feasibility_report": output,
                "recommendation": "go" if go_recommendation else "no-go",
            } if go_recommendation else None,
        )
