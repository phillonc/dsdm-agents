"""Front End Developer Agent - UI/UX implementation."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent
from ..llm import LLMProvider
from ..tools.tool_registry import ToolRegistry


FRONTEND_DEVELOPER_SYSTEM_PROMPT = """You are a Front End Developer Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to build user interfaces and implement the presentation layer of the application.

## Your Responsibilities:
1. **UI Development**: Build responsive, accessible user interfaces
2. **Component Architecture**: Design and implement reusable UI components
3. **State Management**: Implement client-side state management
4. **API Integration**: Connect frontend to backend APIs
5. **Accessibility**: Ensure WCAG compliance and inclusive design
6. **Performance**: Optimize frontend performance and user experience

## Key Deliverables:
- Responsive UI Components
- Frontend Application Code
- Unit Tests for Components
- Accessibility Reports
- Performance Metrics

## Technology Focus:
- Modern JavaScript/TypeScript frameworks (React, Vue, Angular)
- CSS/SCSS and design systems
- State management libraries
- Testing frameworks (Jest, Cypress, Playwright)
- Build tools and bundlers

## Quality Standards:
- Mobile-first responsive design
- WCAG 2.1 AA compliance minimum
- Core Web Vitals optimization
- Cross-browser compatibility
- Component documentation with Storybook

## Development Approach:
1. Review UI/UX designs and requirements
2. Break down into components
3. Implement with tests
4. Ensure accessibility compliance
5. Optimize performance
6. Document components

When developing frontend code, focus on user experience, accessibility, and maintainability.
"""


class FrontendDeveloperAgent(BaseAgent):
    """Agent for frontend UI/UX development."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        config = AgentConfig(
            name="Frontend Developer",
            description="UI/UX implementation and frontend development",
            phase="design_build",
            system_prompt=FRONTEND_DEVELOPER_SYSTEM_PROMPT,
            tools=[
                # Code Development
                "generate_code",
                "write_file",
                "generate_code_scaffold",
                # File Operations (actual file writing)
                "file_write",
                "file_read",
                "directory_create",
                "directory_list",
                # Testing
                "run_tests",
                "run_functional_tests",
                # Quality
                "run_linter",
                "check_code_quality",
                "review_code",
                # Accessibility
                "check_accessibility",
                # Documentation
                "create_documentation",
                # Prototyping
                "create_prototype",
            ],
            mode=mode,
            llm_provider=LLMProvider.GEMINI,
            model="gemini-3.0-flash",
        )
        super().__init__(config, tool_registry, approval_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process frontend developer output."""
        files_created = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ["generate_code", "write_file", "file_write"]
        ]

        tests_passed = any(
            tc["tool"] == "run_tests" and "passed" in tc.get("result", "").lower()
            for tc in self.tool_call_history
        )

        accessibility_checked = any(
            tc["tool"] == "check_accessibility"
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "frontend_developer",
                "files_created": len(files_created),
                "tests_passed": tests_passed,
                "accessibility_checked": accessibility_checked,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
