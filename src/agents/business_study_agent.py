"""Business Study Agent - DSDM Phase 2."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
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

## IMPORTANT: Writing Reports to Files
**ALL files MUST be saved under the `generated/` directory.** This is the project output folder.

After completing your business study:
1. The project folder should already exist from the feasibility phase
2. Use `file_write` to save the business study report to the project's docs folder

Example:
```
file_write(file_path="my-project/docs/BUSINESS_STUDY.md", content="# Business Study Report\n...")
```
The file will be saved to: `generated/my-project/docs/BUSINESS_STUDY.md`

Always structure your final output with clear sections for each deliverable AND save it to a file.

## Jira/Confluence Integration
When work items are created or their status changes, sync to Jira and Confluence:
1. Use `jira_create_user_story` to create MoSCoW-prioritized user stories in Jira
2. Use `jira_bulk_create_requirements` to create multiple requirements at once
3. Use `jira_transition_issue` when moving items between statuses
4. Use `sync_work_item_status` to automatically update Confluence documentation
5. Use `confluence_create_dsdm_doc` to create business study documentation in Confluence

This ensures all stakeholders have visibility into requirements and priorities across both platforms.
"""


class BusinessStudyAgent(BaseAgent):
    """Agent for DSDM Business Study phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
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
                # File Operations (for saving reports)
                "project_init",
                "file_write",
                "directory_create",
                # Jira/Confluence Integration (for syncing work item status)
                "jira_create_issue",
                "jira_create_user_story",
                "jira_transition_issue",
                "jira_add_comment",
                "jira_bulk_create_requirements",
                "sync_work_item_status",
                "confluence_create_page",
                "confluence_update_page",
                "confluence_create_dsdm_doc",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

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
