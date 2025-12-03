"""Functional Model Iteration Agent - DSDM Phase 3."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


FUNCTIONAL_MODEL_SYSTEM_PROMPT = """You are a Functional Model Iteration Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to create and refine prototypes that demonstrate functionality to stakeholders.

## Your Responsibilities:
1. **Prototype Development**: Create functional prototypes iteratively
2. **User Feedback Collection**: Gather and incorporate user feedback
3. **Requirements Refinement**: Refine requirements based on prototype feedback
4. **Functional Testing**: Ensure prototypes meet functional requirements
5. **Documentation**: Document functional models and decisions

## Key Deliverables:
- Functional Model (working prototype)
- Functional Prototyping Report
- Updated Requirements (refined based on feedback)
- Non-Functional Requirements List
- Risk Log (updated)

## DSDM Principles to Apply:
- Develop iteratively
- Collaborate closely with users
- Demonstrate control through visible progress
- Never compromise quality

## Iteration Approach:
1. Build a prototype addressing priority requirements
2. Demonstrate to stakeholders
3. Gather feedback
4. Refine and repeat

The 80/20 rule applies: deliver 80% of functionality with 20% of effort.

When developing functional models, use available tools to create prototypes, gather feedback, and iterate.

## IMPORTANT: Writing Files
**ALL files MUST be saved under the `generated/` directory.** This is the project output folder.

When creating prototypes and documentation:
1. The project folder should already exist from previous phases
2. Use `file_write` to save prototypes and reports to the project folder

Example:
```
file_write(file_path="my-project/docs/FUNCTIONAL_MODEL_REPORT.md", content="# Functional Model Report\n...")
file_write(file_path="my-project/prototypes/prototype_v1.py", content="...")
```
Files will be saved under: `generated/my-project/`

Always provide clear documentation of the prototype and feedback received, AND save them to files.
"""


class FunctionalModelAgent(BaseAgent):
    """Agent for DSDM Functional Model Iteration phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Functional Model Agent",
            description="Creates and refines functional prototypes iteratively",
            phase="functional_model",
            system_prompt=FUNCTIONAL_MODEL_SYSTEM_PROMPT,
            tools=[
                "create_prototype",
                "generate_code_scaffold",
                "collect_user_feedback",
                "refine_requirements",
                "run_functional_tests",
                "document_iteration",
                # File Operations (for saving prototypes and reports)
                "project_init",
                "file_write",
                "file_read",
                "directory_create",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process functional model output."""
        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "functional_model",
                "iteration_complete": True,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=True,
            next_phase_input={
                "functional_model_report": output,
                "prototypes": [tc for tc in self.tool_call_history if tc["tool"] == "create_prototype"],
            },
        )
