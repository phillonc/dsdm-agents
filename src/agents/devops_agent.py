"""DevOps Agent - Based on Development Principles.

Installed Tools and Package Versions:
=====================================
Testing & Quality (Principle 2, 3):
  - pytest 9.0.1
  - pytest-cov 4.1.0
  - pytest-asyncio 0.21.1

Linting & Static Analysis (Principle 3):
  - ruff 0.1.7
  - pylint 2.16.2
  - flake8 7.0.0

Security Scanning (Principle 7):
  - bandit 1.9.2
  - safety 3.7.0
  - pip-audit 2.10.0

Performance Testing (Principle 7):
  - locust 2.42.6

Infrastructure as Code (Principle 6, 8):
  - Terraform 1.5.7
  - Docker 28.5.1

Accessibility Testing (Principle 7):
  - pa11y 9.0.1

Cryptography (secure JWT with pyca/cryptography):
  - pyjwt[crypto] 2.10.1
  - cryptography 46.0.3
"""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


# Tool version constants for runtime validation
DEVOPS_TOOL_VERSIONS = {
    # Testing & Quality
    "pytest": "9.0.1",
    "pytest-cov": "4.1.0",
    "pytest-asyncio": "0.21.1",
    # Linting & Static Analysis
    "ruff": "0.1.7",
    "pylint": "2.16.2",
    "flake8": "7.0.0",
    # Security Scanning
    "bandit": "1.9.2",
    "safety": "3.7.0",
    "pip-audit": "2.10.0",
    # Performance Testing
    "locust": "2.42.6",
    # Infrastructure as Code
    "terraform": "1.5.7",
    "docker": "28.5.1",
    # Accessibility Testing
    "pa11y": "9.0.1",
    # Cryptography
    "pyjwt": "2.10.1",
    "cryptography": "46.0.3",
}


DEVOPS_SYSTEM_PROMPT = """You are a DevOps Agent operating based on the Development Principles.

Your role is to enable and enforce development best practices throughout the software development lifecycle.

## Core Development Principles You Enforce:

### 1. Decision Making should be distributed
- Document technical decisions with rationale
- Use Architecture Decision Records (ADRs)
- Enable collaborative decision making

### 2. If it's not tested, it's broken
- Enforce test-driven development
- Maintain high test coverage (minimum 80%)
- Run automated tests continuously

### 3. Transparency dispels myth
- Provide code metrics and quality data
- Track and report on progress
- Use data to validate hypotheses

### 4. Mean Time To Innocence (MTTI)
- Build health dashboards
- Enable quick service verification
- Monitor system health continuously

### 5. No Dead Cats over the fence
- You Build It, You Operate It
- Ensure CI/CD ownership
- Track code ownership

### 6. Friends would not let friends build data centres
- Cloud-first development
- Elastic, fault-tolerant systems
- Infrastructure as Code

### 7. Non Functional Requirements are first class citizens
- Performance testing
- Security scanning
- Accessibility validation

### 8. Cattle not Pets
- Infrastructure as Code for all environments
- Disposable, reproducible environments
- Container orchestration

### 9. Keep the Hostage
- Complete backup/restore automation
- Devalue production through automation
- Disaster recovery capabilities

### 10. Elimination of Toil, via automation
- Automate repetitive tasks
- Reduce manual intervention
- Continuous automation improvement

### 11. Failure is Normal, but customer disruption is not
- Design for failure
- Implement circuit breakers
- Multi-region deployment

### 12. Dependencies create "latency as a service"
- Minimize external dependencies
- Analyze and optimize dependencies
- Enable team autonomy

### 13. Focus our efforts on differentiating code and infrastructure
- Use managed services where cost-effective
- Focus engineering on business value
- Leverage AI-assisted development

### 14. Stop Starting and Start Stopping / Completing tasks
- Track incomplete work
- Focus on task completion
- Measure earned value

## Your Responsibilities:
1. **Quality Gates**: Enforce testing, coverage, and quality standards
2. **CI/CD**: Manage build, test, and deployment pipelines
3. **Infrastructure**: Manage cloud infrastructure as code
4. **Monitoring**: Set up health checks and dashboards
5. **Security**: Run security scans and enforce compliance
6. **Automation**: Identify and eliminate toil

## Available Tools and Versions:

### Testing & Quality (Principle 2, 3):
- pytest 9.0.1 - Test framework with coverage support
- pytest-cov 4.1.0 - Coverage plugin for pytest
- pytest-asyncio 0.21.1 - Async test support

### Linting & Static Analysis (Principle 3):
- ruff 0.1.7 - Fast Python linter
- pylint 2.16.2 - Python static code analyzer
- flake8 7.0.0 - Style guide enforcement

### Security Scanning (Principle 7):
- bandit 1.9.2 - Security issue finder
- safety 3.7.0 - Dependency vulnerability checker
- pip-audit 2.10.0 - Audit Python packages for vulnerabilities

### Performance Testing (Principle 7):
- locust 2.42.6 - Load testing framework

### Infrastructure as Code (Principle 6, 8):
- Terraform 1.5.7 - Infrastructure provisioning
- Docker 28.5.1 - Container management

### Accessibility Testing (Principle 7):
- pa11y 9.0.1 - Accessibility testing tool

### Cryptography:
- pyjwt[crypto] 2.10.1 - JWT implementation using pyca/cryptography
- cryptography 46.0.3 - Secure cryptographic operations

When helping with DevOps tasks, always reference the relevant principle and explain how the action aligns with it.
"""


class DevOpsAgent(BaseAgent):
    """Agent for DevOps tasks based on development principles."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.HYBRID,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="DevOps Agent",
            description="Enables development principles through DevOps practices",
            phase="devops",
            system_prompt=DEVOPS_SYSTEM_PROMPT,
            tools=[
                # Testing & Quality (Principle 2, 3)
                "run_tests",
                "check_coverage",
                "run_linter",
                "run_security_scan",
                "check_code_quality",

                # CI/CD & Automation (Principle 5, 10)
                "run_ci_pipeline",
                "deploy_to_environment",
                "rollback_deployment",
                "automate_task",

                # Infrastructure (Principle 6, 8)
                "provision_infrastructure",
                "validate_terraform",
                "manage_containers",
                "scale_service",

                # Monitoring & Health (Principle 4, 11)
                "health_check",
                "setup_monitoring",
                "check_service_status",
                "run_chaos_test",

                # Dependencies & NFRs (Principle 7, 12)
                "analyze_dependencies",
                "run_performance_test",
                "check_accessibility",
                "validate_nfr",

                # Documentation & Decisions (Principle 1, 3)
                "create_adr",
                "generate_docs",
                "track_decision",

                # Task Management (Principle 14)
                "check_incomplete_tasks",
                "track_toil",

                # Backup & Recovery (Principle 9)
                "backup_database",
                "test_restore",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process DevOps agent output."""
        # Check for any failures in tool calls
        has_failures = any(
            "error" in tc.get("result", "").lower() or
            "failed" in tc.get("result", "").lower()
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=not has_failures,
            output=output,
            artifacts={
                "phase": "devops",
                "principles_applied": self._extract_principles(output),
                "tools_used": [tc["tool"] for tc in self.tool_call_history],
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )

    def _extract_principles(self, output: str) -> list:
        """Extract which principles were referenced in the output."""
        principles = []
        principle_keywords = {
            1: ["decision", "adr", "distributed"],
            2: ["test", "coverage", "tdd"],
            3: ["transparency", "metrics", "data"],
            4: ["mtti", "health", "monitoring"],
            5: ["ownership", "build it", "operate"],
            6: ["cloud", "elastic", "infrastructure"],
            7: ["nfr", "performance", "security", "accessibility"],
            8: ["cattle", "iac", "container"],
            9: ["backup", "restore", "recovery"],
            10: ["toil", "automation", "automate"],
            11: ["failure", "resilience", "circuit"],
            12: ["dependencies", "latency"],
            13: ["managed service", "differentiating"],
            14: ["complete", "wip", "earned value"],
        }

        output_lower = output.lower()
        for principle_num, keywords in principle_keywords.items():
            if any(kw in output_lower for kw in keywords):
                principles.append(principle_num)

        return principles
