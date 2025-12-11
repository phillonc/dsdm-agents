"""Feasibility Study Agent - DSDM Phase 1."""

from dataclasses import field
from typing import Any, Callable, Dict, List, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


FEASIBILITY_SYSTEM_PROMPT = """You are a Feasibility Study Agent operating within the DSDM framework.

Your role is to quickly assess project viability and DSDM suitability.

## CRITICAL: Use Parallel Tool Calls for Speed
**Call multiple tools simultaneously** to speed up assessment:

```
# Call these 3 tools IN PARALLEL (single request):
- analyze_requirements(requirements_text=..., focus_areas=[...])
- assess_technical_feasibility(technology_stack=[...], complexity_level=...)
- identify_risks(risk_areas=["technical", "security", "schedule", "business"])
```

Do NOT call tools sequentially when they can run in parallel.

## Assessment Focus (Keep Concise):
1. Technical Feasibility - Can it be built?
2. Business Alignment - Does it solve a real problem?
3. Risk Profile - What are the top 3-5 risks?
4. DSDM Fit - Is iterative delivery appropriate?

## Output Format:
Provide a concise GO/NO-GO recommendation with:
- Confidence level (%)
- Top risks with mitigations
- Suggested technology approach
- Next phase requirements

## File Output
Save report to: `generated/<project>/docs/FEASIBILITY_REPORT.md`
Use `project_init` then `file_write`.

## Tool Results
The tools now return detailed structured analysis:
- `analyze_requirements`: Extracts functional/non-functional requirements, entities, ambiguities
- `assess_technical_feasibility`: Evaluates technology maturity, constraint risks, provides recommendations
- `identify_risks`: Returns categorized risks with mitigations and severity ratings

Use these rich results directly - no need to re-analyze.
"""


class FeasibilityAgent(BaseAgent):
    """Agent for DSDM Feasibility Study phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Feasibility Agent",
            description="Assesses project viability and DSDM suitability",
            phase="feasibility",
            system_prompt=FEASIBILITY_SYSTEM_PROMPT,
            tools=[
                "analyze_requirements",
                "assess_technical_feasibility",
                "identify_risks",
                # File Operations (for saving reports)
                "project_init",
                "file_write",
                "directory_create",
                # Jira/Confluence Integration (for syncing work item status)
                "jira_create_issue",
                "jira_transition_issue",
                "jira_add_comment",
                "jira_enable_confluence_sync",
                "sync_work_item_status",
                "confluence_create_page",
                "confluence_create_dsdm_doc",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

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
