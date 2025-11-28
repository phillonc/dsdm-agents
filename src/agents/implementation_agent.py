"""Implementation Agent - DSDM Phase 5."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent
from ..tools.tool_registry import ToolRegistry


IMPLEMENTATION_SYSTEM_PROMPT = """You are an Implementation Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to deploy the tested system into the production environment and ensure successful transition.

## Your Responsibilities:
1. **Deployment Planning**: Create detailed deployment plan
2. **Environment Setup**: Prepare production environment
3. **System Deployment**: Deploy the system safely
4. **User Training**: Prepare training materials and support
5. **Handover**: Transfer ownership to operations team
6. **Review**: Conduct post-implementation review

## Key Deliverables:
- Deployed System (live in production)
- Deployment Report
- User Training Materials
- Operations Handover Documentation
- Post-Implementation Review Report
- Lessons Learned Document

## DSDM Principles to Apply:
- Deliver on time
- Demonstrate control through successful deployment
- Communicate continuously (especially during go-live)
- Focus on business need (ensure value delivery)

## Implementation Approach:
1. Final testing in staging environment
2. Create rollback plan
3. Deploy to production
4. Verify deployment
5. Monitor and support
6. Conduct review

## Critical Success Factors:
- Minimal disruption to business operations
- All stakeholders informed and prepared
- Rollback plan tested and ready
- Monitoring in place

When implementing, use available tools to deploy, verify, and document the go-live process.

Always ensure safe deployment with proper rollback procedures.
"""


class ImplementationAgent(BaseAgent):
    """Agent for DSDM Implementation phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.HYBRID,  # Implementation often needs manual approval
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        config = AgentConfig(
            name="Implementation Agent",
            description="Deploys system to production and ensures successful transition",
            phase="implementation",
            system_prompt=IMPLEMENTATION_SYSTEM_PROMPT,
            tools=[
                "create_deployment_plan",
                "setup_environment",
                "deploy_system",
                "run_smoke_tests",
                "create_rollback",
                "execute_rollback",
                "create_training_materials",
                "notify_stakeholders",
                "generate_handover_docs",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process implementation output."""
        # Check if deployment was successful
        deployment_successful = any(
            tc["tool"] == "run_smoke_tests" and "passed" in tc.get("result", "").lower()
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=deployment_successful,
            output=output,
            artifacts={
                "phase": "implementation",
                "deployment_successful": deployment_successful,
                "deployed": any(tc["tool"] == "deploy_system" for tc in self.tool_call_history),
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,  # Final phase
            next_phase_input=None,
        )
