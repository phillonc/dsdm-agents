"""Dev Lead Agent - Technical leadership and architecture."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


DEV_LEAD_SYSTEM_PROMPT = """You are a Dev Lead Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to provide technical leadership, architectural guidance, and coordinate the development team.

## Your Responsibilities:
1. **Architecture Design**: Define system architecture and technical standards
2. **Technical Decision Making**: Make and document architectural decisions (ADRs)
3. **Code Review**: Review code for quality, standards, and best practices
4. **Team Coordination**: Coordinate between frontend, backend, and testing teams
5. **Risk Management**: Identify and mitigate technical risks
6. **Quality Oversight**: Ensure overall code quality and technical debt management

## Key Deliverables:
- Architecture Decision Records (ADRs)
- Technical Design Documents
- Code Review Reports
- Technical Risk Assessments
- Development Standards and Guidelines

## Leadership Principles:
- Lead by example with high-quality code
- Foster collaborative decision making
- Balance technical debt with delivery
- Ensure knowledge sharing across the team
- Maintain focus on business value

## Technical Standards You Enforce:
- Clean code principles
- SOLID design patterns
- Security best practices
- Performance optimization
- Comprehensive documentation

When leading development, coordinate with specialized developers and testers to deliver quality systems.
"""


class DevLeadAgent(BaseAgent):
    """Agent for technical leadership and architecture."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.HYBRID,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Dev Lead",
            description="Technical leadership and architecture coordination",
            phase="design_build",
            system_prompt=DEV_LEAD_SYSTEM_PROMPT,
            tools=[
                # Architecture & Design
                "create_technical_design",
                "define_architecture",
                "create_adr",
                "track_decision",
                # File Operations
                "file_write",
                "file_read",
                "directory_create",
                "directory_list",
                # Code Review & Quality
                "review_code",
                "check_code_quality",
                "run_linter",
                # Documentation
                "create_documentation",
                "generate_docs",
                # Risk & Planning
                "identify_risks",
                "update_risk_log",
                "analyze_dependencies",
                # Testing oversight
                "run_tests",
                "check_coverage",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process dev lead output."""
        # Check for architectural decisions made
        adrs_created = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ["create_adr", "track_decision"]
        ]

        reviews_completed = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "review_code"
        ]

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "dev_lead",
                "adrs_created": len(adrs_created),
                "reviews_completed": len(reviews_completed),
                "decisions": adrs_created,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
