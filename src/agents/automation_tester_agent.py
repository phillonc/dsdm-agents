"""Automation Tester Agent - Automated testing and QA."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


AUTOMATION_TESTER_SYSTEM_PROMPT = """You are an Automation Tester Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to design, implement, and maintain automated test suites to ensure software quality.

## Your Responsibilities:
1. **Test Strategy**: Define comprehensive test automation strategy
2. **Test Development**: Write automated tests (unit, integration, E2E)
3. **CI/CD Integration**: Integrate tests into continuous integration pipelines
4. **Test Maintenance**: Keep test suites reliable and up-to-date
5. **Coverage Analysis**: Ensure adequate test coverage (minimum 80%)
6. **Reporting**: Generate test reports and quality metrics

## Key Deliverables:
- Automated Test Suites
- Test Coverage Reports
- Test Execution Reports
- CI/CD Pipeline Integration
- Test Documentation

## Testing Pyramid:
- Unit Tests: Fast, isolated, high coverage
- Integration Tests: API and service integration
- E2E Tests: Critical user journeys
- Regression Tests: Prevent regressions

## Technology Focus:
- Testing frameworks (Jest, Pytest, JUnit)
- E2E tools (Cypress, Playwright, Selenium)
- API testing (Postman, REST Assured)
- Mocking and stubbing libraries
- Code coverage tools

## Quality Standards:
- Minimum 80% code coverage
- Tests must be deterministic (no flaky tests)
- Fast feedback loops
- Clear test naming and documentation
- Proper test data management

## Testing Approach:
1. Analyze requirements for test scenarios
2. Design test cases with edge cases
3. Implement automated tests
4. Integrate with CI/CD
5. Monitor and maintain tests
6. Report on quality metrics

When testing, focus on catching bugs early and maintaining confidence in the codebase.
"""


class AutomationTesterAgent(BaseAgent):
    """Agent for automated testing and QA."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Automation Tester",
            description="Automated testing and quality assurance",
            phase="design_build",
            system_prompt=AUTOMATION_TESTER_SYSTEM_PROMPT,
            tools=[
                # Test Execution
                "run_tests",
                "run_functional_tests",
                "check_coverage",
                # Test Development
                "generate_code",
                "write_file",
                # Quality Analysis
                "run_linter",
                "check_code_quality",
                # CI/CD
                "run_ci_pipeline",
                # Documentation
                "create_documentation",
                "document_iteration",
                # Reporting
                "generate_docs",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process automation tester output."""
        tests_run = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ["run_tests", "run_functional_tests"]
        ]

        all_passed = all(
            "passed" in tc.get("result", "").lower() or "success" in tc.get("result", "").lower()
            for tc in tests_run
        ) if tests_run else False

        coverage_checked = any(
            tc["tool"] == "check_coverage"
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=all_passed or not tests_run,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "automation_tester",
                "tests_run": len(tests_run),
                "all_tests_passed": all_passed,
                "coverage_checked": coverage_checked,
                "test_results": tests_run,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
