"""Penetration Tester Agent - Security testing and vulnerability assessment."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


PEN_TESTER_SYSTEM_PROMPT = """You are a Penetration Tester Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to identify security vulnerabilities and ensure the application is protected against common attack vectors.

## Your Responsibilities:
1. **Vulnerability Assessment**: Identify security weaknesses
2. **Penetration Testing**: Simulate attacks to test defenses
3. **Security Code Review**: Review code for security issues
4. **Dependency Scanning**: Check for vulnerable dependencies
5. **Compliance Validation**: Ensure security compliance (OWASP, etc.)
6. **Security Reporting**: Document findings and remediation

## Key Deliverables:
- Vulnerability Assessment Report
- Penetration Test Results
- Security Code Review Findings
- Dependency Vulnerability Report
- Remediation Recommendations

## OWASP Top 10 Focus Areas:
1. Broken Access Control
2. Cryptographic Failures
3. Injection (SQL, XSS, Command)
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable Components
7. Authentication Failures
8. Data Integrity Failures
9. Logging & Monitoring Failures
10. Server-Side Request Forgery (SSRF)

## Testing Methodology:
- Static Application Security Testing (SAST)
- Dynamic Application Security Testing (DAST)
- Software Composition Analysis (SCA)
- Secret/Credential Scanning
- Infrastructure Security Assessment

## Security Standards:
- OWASP Testing Guide
- NIST Cybersecurity Framework
- CIS Benchmarks
- Industry-specific compliance (PCI-DSS, HIPAA, SOC2)

## Testing Approach:
1. Reconnaissance and information gathering
2. Vulnerability scanning and analysis
3. Manual penetration testing
4. Code security review
5. Document findings with severity
6. Provide remediation guidance

IMPORTANT: All testing must be authorized and conducted ethically within the defined scope.
Security findings should be classified by severity (Critical, High, Medium, Low, Informational).
"""


class PenTesterAgent(BaseAgent):
    """Agent for penetration testing and security assessment."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.MANUAL,  # Security testing requires approval
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Penetration Tester",
            description="Security testing and vulnerability assessment",
            phase="design_build",
            system_prompt=PEN_TESTER_SYSTEM_PROMPT,
            tools=[
                # Security Scanning
                "run_security_scan",
                "security_check",
                # Dependency Analysis
                "analyze_dependencies",
                # Code Review
                "review_code",
                "check_code_quality",
                # Testing
                "run_tests",
                # Documentation
                "create_documentation",
                "generate_docs",
                # Risk Management
                "identify_risks",
                "update_risk_log",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process pen tester output."""
        security_scans = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ["run_security_scan", "security_check"]
        ]

        dependency_scans = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "analyze_dependencies"
        ]

        code_reviews = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "review_code"
        ]

        # Check for critical/high vulnerabilities
        has_critical_vulns = any(
            "critical" in tc.get("result", "").lower() and
            any(c.isdigit() and int(c) > 0 for c in tc.get("result", "").split("critical")[1][:5] if c.isdigit())
            for tc in security_scans
        )

        risks_identified = [
            tc for tc in self.tool_call_history
            if tc["tool"] == "identify_risks"
        ]

        return AgentResult(
            success=not has_critical_vulns,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "pen_tester",
                "security_scans": len(security_scans),
                "dependency_scans": len(dependency_scans),
                "code_reviews": len(code_reviews),
                "risks_identified": len(risks_identified),
                "has_critical_vulnerabilities": has_critical_vulns,
                "scan_results": security_scans,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
