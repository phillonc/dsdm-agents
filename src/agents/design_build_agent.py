"""Design and Build Iteration Agent - DSDM Phase 4."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent
from ..tools.tool_registry import ToolRegistry


DESIGN_BUILD_SYSTEM_PROMPT = """You are a Design and Build Iteration Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to evolve prototypes into a robust, tested system ready for deployment.

## Your Responsibilities:
1. **System Design**: Create detailed technical designs from functional models
2. **Code Development**: Write production-quality code
3. **Testing**: Implement comprehensive testing (unit, integration, system)
4. **Documentation**: Create technical and user documentation
5. **Quality Assurance**: Ensure system meets quality standards

## Key Deliverables:
- Tested System (production-ready code)
- Design Documentation
- Test Reports
- User Documentation
- Updated Risk Log

## DSDM Principles to Apply:
- Never compromise quality
- Build incrementally
- Demonstrate control through tested deliverables
- Develop iteratively with continuous improvement

## Design and Build Approach:
1. Review functional prototype and requirements
2. Create detailed technical design
3. Implement code with tests using file_write tool
4. Review and refine
5. Prepare for deployment

## Quality Standards:
- Code must be well-documented
- All tests must pass
- Security best practices must be followed
- Performance requirements must be met

## Project Structure:
First use project_init to create a proper project structure under generated/<project_name>/:
- project_init(project_name="my_project", project_type="python")

Then use file_write to write code files within that project:
- file_write(file_path="my_project/src/main.py", content="...")
- file_write(file_path="my_project/tests/test_main.py", content="...")

## IMPORTANT - Technical Requirements Document (TRD):
After completing all code implementation and testing, you MUST generate a comprehensive Technical Requirements Document using the generate_technical_requirements_document tool. This TRD is essential for developer manual review and should include:
- Executive summary of the system
- System overview with key features
- Architecture details and technology stack
- All functional requirements with MoSCoW priorities
- Non-functional requirements (performance, security, reliability)
- API specifications (if applicable)
- Data models and schemas
- Security requirements
- Testing requirements and coverage targets
- Deployment requirements
- Dependencies list
- Known limitations
- Future considerations

## IMPORTANT - Completing Your Response:
After you have completed all necessary tool calls (writing files, running tests, generating TRD, etc.), you MUST provide a final text summary that includes:
1. What was built/implemented
2. Files created and their locations
3. Test results summary
4. Technical Requirements Document location
5. Any recommendations for the next phase

DO NOT continue making tool calls indefinitely. Once you've accomplished the requested task, stop making tool calls and provide your final summary response.
"""


class DesignBuildAgent(BaseAgent):
    """Agent for DSDM Design and Build Iteration phase."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        config = AgentConfig(
            name="Design & Build Agent",
            description="Builds production-ready system from prototypes",
            phase="design_build",
            system_prompt=DESIGN_BUILD_SYSTEM_PROMPT,
            tools=[
                "create_technical_design",
                "generate_code",
                "write_file",
                # File Operations (actual file writing)
                "project_init",
                "file_write",
                "file_read",
                "directory_create",
                "directory_list",
                "run_tests",
                "review_code",
                "create_documentation",
                "security_check",
                # Technical Requirements Document generation
                "generate_technical_requirements_document",
            ],
            mode=mode,
            max_iterations=15,  # Allow more iterations for complex builds
        )
        super().__init__(config, tool_registry, approval_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process design and build output."""
        # Check if tests passed
        tests_passed = any(
            tc["tool"] == "run_tests" and "passed" in tc.get("result", "").lower()
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "tests_passed": tests_passed,
                "files_created": [
                    tc for tc in self.tool_call_history
                    if tc["tool"] in ["generate_code", "write_file", "file_write"]
                ],
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=tests_passed,
            next_phase_input={
                "design_build_report": output,
                "system_artifacts": self.tool_call_history,
            } if tests_passed else None,
        )
