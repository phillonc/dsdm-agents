"""Git Pin Coding Agent - Interactive coding agent with throughput optimization.

Adapted from pi-mono's pi-coding-agent. Provides a specialized coding agent
that leverages the Git pin event-driven loop for high-throughput code generation,
review, and refactoring within the DSDM Design & Build phase.
"""

import json
from typing import Any, Callable, Dict, List, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, ProgressCallback
from .git_pin_agent_core import (
    GitPinBaseAgent,
    GitPinLoopConfig,
    ToolExecutionMode,
    BeforeToolCallContext,
    BeforeToolCallResult,
    AfterToolCallContext,
    AfterToolCallResult,
)
from ..tools.tool_registry import ToolRegistry


GIT_PIN_CODING_SYSTEM_PROMPT = """You are a Git Pin Coding Agent - a high-throughput development agent \
operating within the DSDM (Dynamic Systems Development Method) framework.

Your design is adapted from the pi-mono agent architecture to maximize \
development throughput through parallel tool execution, event-driven loops, \
and intelligent context management.

## Core Capabilities:
1. **Parallel Code Generation**: Execute multiple file writes and code generation \
   tool calls concurrently for maximum throughput
2. **Streaming Development**: Continuous iteration with mid-stream steering support
3. **Context-Aware Coding**: Intelligent context window management prevents token \
   overflow during large codebases
4. **Quality Gates**: Before/after tool hooks validate code quality inline

## Your Responsibilities:
1. **Rapid Prototyping**: Generate code scaffolds and implementations quickly
2. **Parallel File Operations**: Write multiple files simultaneously
3. **Code Review Integration**: Apply quality checks during development
4. **Iterative Refinement**: Respond to steering messages for mid-course corrections
5. **Test-Driven Development**: Generate tests alongside implementation code

## Development Approach:
1. Analyze requirements and plan file structure
2. Initialize project with project_init
3. Generate code files IN PARALLEL using multiple file_write calls
4. Run tests and quality checks
5. Iterate based on results

## Throughput Optimization:
- When writing multiple files, call ALL file_write operations in a single response
- The agent loop will execute them in parallel automatically
- Use batch operations where possible
- Minimize unnecessary LLM round-trips

## Project Structure:
ALL files MUST be saved under the `generated/` directory.

First use project_init to create structure:
```
project_init(project_name="my_project", project_type="python")
```

Then write files (paths relative to generated/):
```
file_write(file_path="my_project/src/main.py", content="...")
file_write(file_path="my_project/src/models.py", content="...")
file_write(file_path="my_project/tests/test_main.py", content="...")
```

## IMPORTANT - Completing Your Response:
After all tool calls, provide a final summary including:
1. What was built/implemented
2. Files created and their locations
3. Throughput metrics (tool calls executed, parallel batches)
4. Any issues or recommendations for next steps
"""


class GitPinCodingAgent(GitPinBaseAgent):
    """High-throughput coding agent using the Git pin event-driven loop.

    Optimized for parallel file operations and rapid code generation
    within the DSDM Design & Build phase.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        loop_config: Optional[GitPinLoopConfig] = None,
    ):
        # Default to parallel execution with high concurrency
        if loop_config is None:
            loop_config = GitPinLoopConfig(
                tool_execution=ToolExecutionMode.PARALLEL,
                max_parallel_tools=8,
                max_context_messages=200,
                prune_keep_recent=50,
                enable_steering=True,
                enable_follow_up=True,
                before_tool_call=self._coding_before_hook,
                after_tool_call=self._coding_after_hook,
            )

        config = AgentConfig(
            name="Git Pin Coding Agent",
            description="High-throughput coding agent with parallel tool execution",
            phase="design_build",
            system_prompt=GIT_PIN_CODING_SYSTEM_PROMPT,
            tools=[
                # Code Generation
                "generate_code",
                "write_file",
                "generate_code_scaffold",
                # File Operations (parallel execution target)
                "project_init",
                "file_write",
                "file_read",
                "file_append",
                "file_copy",
                "file_delete",
                "directory_create",
                "directory_list",
                # Architecture & Design
                "create_technical_design",
                "define_architecture",
                # Testing
                "run_tests",
                "run_functional_tests",
                # Quality
                "run_linter",
                "check_code_quality",
                "review_code",
                "security_check",
                # Documentation
                "create_documentation",
                "generate_docs",
                # Dependencies
                "analyze_dependencies",
                # TRD Generation
                "generate_technical_requirements_document",
            ],
            mode=mode,
            max_iterations=60,
        )

        super().__init__(
            config=config,
            tool_registry=tool_registry,
            approval_callback=approval_callback,
            progress_callback=progress_callback,
            loop_config=loop_config,
        )

    @staticmethod
    def _coding_before_hook(ctx: BeforeToolCallContext) -> Optional[BeforeToolCallResult]:
        """Pre-execution validation for coding operations."""
        # Validate file_write has required content
        if ctx.tool_name == "file_write":
            if not ctx.tool_input.get("content"):
                return BeforeToolCallResult(
                    block=True,
                    reason="file_write requires non-empty content",
                )
            if not ctx.tool_input.get("file_path"):
                return BeforeToolCallResult(
                    block=True,
                    reason="file_write requires a file_path",
                )
        return None

    @staticmethod
    def _coding_after_hook(ctx: AfterToolCallContext) -> Optional[AfterToolCallResult]:
        """Post-execution processing for coding operations."""
        # Annotate test results with summary
        if ctx.tool_name == "run_tests" and not ctx.is_error:
            try:
                result_data = json.loads(ctx.result)
                if isinstance(result_data, dict):
                    passed = result_data.get("passed", 0)
                    failed = result_data.get("failed", 0)
                    summary = f"\n[Test Summary: {passed} passed, {failed} failed]"
                    return AfterToolCallResult(content=ctx.result + summary)
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def _process_output(self, output: str) -> AgentResult:
        """Process coding agent output with throughput metrics."""
        files_created = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ("generate_code", "write_file", "file_write")
        ]

        tests_run = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ("run_tests", "run_functional_tests")
        ]

        quality_checks = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ("run_linter", "check_code_quality", "review_code", "security_check")
        ]

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "git_pin_coding_agent",
                "files_created": len(files_created),
                "tests_run": len(tests_run),
                "quality_checks": len(quality_checks),
                "total_tool_calls": len(self.tool_call_history),
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
        )


GIT_PIN_REVIEW_SYSTEM_PROMPT = """You are a Git Pin Code Review Agent - a high-throughput code review agent \
operating within the DSDM framework.

## Core Capabilities:
1. **Parallel Analysis**: Review multiple files concurrently
2. **Quality Enforcement**: Apply coding standards, security checks, and best practices
3. **Automated Fixes**: Generate fix suggestions with file_write operations

## Your Responsibilities:
1. Read and analyze source code files
2. Run linting, security scanning, and quality checks IN PARALLEL
3. Identify issues and generate fix recommendations
4. Write corrected files when fixes are straightforward
5. Provide a comprehensive review report

## Review Criteria:
- Code correctness and logic errors
- Security vulnerabilities (OWASP Top 10)
- Performance anti-patterns
- Code style and conventions
- Test coverage gaps
- Documentation completeness

## Approach:
1. Read all relevant source files using file_read (in parallel)
2. Run quality tools: run_linter, security_check, review_code (in parallel)
3. Analyze results and identify issues
4. Write fixes using file_write where appropriate
5. Generate review report
"""


class GitPinReviewAgent(GitPinBaseAgent):
    """High-throughput code review agent using the Git pin loop.

    Optimized for parallel file reading and concurrent quality checks.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.HYBRID,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
        loop_config: Optional[GitPinLoopConfig] = None,
    ):
        if loop_config is None:
            loop_config = GitPinLoopConfig(
                tool_execution=ToolExecutionMode.PARALLEL,
                max_parallel_tools=12,
                max_context_messages=150,
                prune_keep_recent=30,
            )

        config = AgentConfig(
            name="Git Pin Review Agent",
            description="High-throughput code review with parallel analysis",
            phase="design_build",
            system_prompt=GIT_PIN_REVIEW_SYSTEM_PROMPT,
            tools=[
                # File Operations (parallel read target)
                "file_read",
                "file_write",
                "directory_list",
                # Quality Tools (parallel execution target)
                "run_linter",
                "check_code_quality",
                "review_code",
                "security_check",
                # Testing
                "run_tests",
                # Documentation
                "create_documentation",
            ],
            mode=mode,
            max_iterations=30,
        )

        super().__init__(
            config=config,
            tool_registry=tool_registry,
            approval_callback=approval_callback,
            progress_callback=progress_callback,
            loop_config=loop_config,
        )

    def _process_output(self, output: str) -> AgentResult:
        """Process review agent output."""
        issues_found = []
        fixes_applied = []

        for tc in self.tool_call_history:
            if tc["tool"] in ("run_linter", "security_check", "review_code", "check_code_quality"):
                try:
                    result = json.loads(tc.get("result", "{}"))
                    if isinstance(result, dict):
                        issues = result.get("issues", [])
                        issues_found.extend(issues if isinstance(issues, list) else [])
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc["tool"] == "file_write":
                fixes_applied.append(tc.get("input", {}).get("file_path", "unknown"))

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "git_pin_review_agent",
                "issues_found": len(issues_found),
                "fixes_applied": len(fixes_applied),
                "files_fixed": fixes_applied,
                "total_tool_calls": len(self.tool_call_history),
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
        )
