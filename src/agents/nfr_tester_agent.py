"""Non-Functional Requirements Tester Agent - Performance, reliability, and NFR testing."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


NFR_TESTER_SYSTEM_PROMPT = """You are a Non-Functional Requirements (NFR) Tester Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to test and validate non-functional requirements including performance, scalability, reliability, and accessibility.

## Your Responsibilities:
1. **Performance Testing**: Load, stress, and endurance testing
2. **Scalability Testing**: Verify system scales under load
3. **Reliability Testing**: Chaos engineering and resilience testing
4. **Accessibility Testing**: WCAG compliance validation
5. **Availability Testing**: Uptime and failover testing
6. **Capacity Planning**: Determine system limits and thresholds

## Key Deliverables:
- Performance Test Reports
- Scalability Analysis
- Reliability Metrics
- Accessibility Audit Reports
- NFR Compliance Matrix

## NFR Categories (Development Principle 7):
- **Performance**: Response time, throughput, latency
- **Scalability**: Horizontal/vertical scaling capabilities
- **Reliability**: MTBF, MTTR, fault tolerance
- **Accessibility**: WCAG 2.1 AA/AAA compliance
- **Availability**: Uptime SLAs (99.9%, 99.99%)
- **Maintainability**: Code quality, documentation

## Testing Types:
- Load Testing: Normal and peak load scenarios
- Stress Testing: Beyond normal capacity
- Spike Testing: Sudden load increases
- Soak Testing: Extended duration under load
- Chaos Testing: Failure injection and recovery

## Quality Standards:
- Response time < 200ms (p95)
- Error rate < 0.1%
- Availability > 99.9%
- WCAG 2.1 AA compliance
- Recovery time < 30 seconds

## Testing Approach:
1. Define NFR acceptance criteria
2. Design test scenarios
3. Execute performance/load tests
4. Run accessibility audits
5. Conduct chaos experiments
6. Analyze and report results

Remember: NFRs are first-class citizens. Fix NFR issues before adding new features.
"""


class NFRTesterAgent(BaseAgent):
    """Agent for non-functional requirements testing."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.HYBRID,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="NFR Tester",
            description="Performance, reliability, and non-functional testing",
            phase="design_build",
            system_prompt=NFR_TESTER_SYSTEM_PROMPT,
            tools=[
                # Performance Testing
                "run_performance_test",
                "validate_nfr",
                # Accessibility
                "check_accessibility",
                # Reliability & Chaos
                "run_chaos_test",
                "health_check",
                "check_service_status",
                # Monitoring
                "setup_monitoring",
                # Quality
                "check_code_quality",
                # Scaling
                "scale_service",
                # Documentation
                "create_documentation",
                "generate_docs",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process NFR tester output."""
        performance_tests = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "run_performance_test"
        ]

        accessibility_tests = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "check_accessibility"
        ]

        chaos_tests = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "run_chaos_test"
        ]

        nfr_validations = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "validate_nfr"
        ]

        all_passed = all(
            "passed" in tc.get("result", "").lower() or "success" in tc.get("result", "").lower()
            for tc in performance_tests + nfr_validations
        ) if (performance_tests or nfr_validations) else True

        return AgentResult(
            success=all_passed,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "nfr_tester",
                "performance_tests": len(performance_tests),
                "accessibility_tests": len(accessibility_tests),
                "chaos_tests": len(chaos_tests),
                "nfr_validations": len(nfr_validations),
                "all_nfrs_passed": all_passed,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
