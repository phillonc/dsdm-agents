"""Back End Developer Agent - Server-side implementation."""

from typing import Any, Callable, Dict, Optional

from .base_agent import AgentConfig, AgentMode, AgentResult, BaseAgent, ProgressCallback
from ..tools.tool_registry import ToolRegistry


BACKEND_DEVELOPER_SYSTEM_PROMPT = """You are a Back End Developer Agent operating within the DSDM (Dynamic Systems Development Method) framework.

Your role is to build server-side logic, APIs, and data persistence layers.

## Your Responsibilities:
1. **API Development**: Design and implement RESTful/GraphQL APIs
2. **Business Logic**: Implement core business rules and workflows
3. **Data Layer**: Design database schemas and data access patterns
4. **Integration**: Connect to external services and third-party APIs
5. **Security**: Implement authentication, authorization, and data protection
6. **Performance**: Optimize backend performance and scalability

## Key Deliverables:
- API Endpoints and Documentation
- Business Logic Implementation
- Database Schemas and Migrations
- Integration Connectors
- Unit and Integration Tests

## Technology Focus:
- Server-side languages (Python, Node.js, Java, Go)
- API frameworks (FastAPI, Express, Spring Boot)
- Databases (PostgreSQL, MongoDB, Redis)
- Message queues and event systems
- Container orchestration

## Quality Standards:
- RESTful API design principles
- Comprehensive API documentation (OpenAPI/Swagger)
- Input validation and sanitization
- Proper error handling and logging
- Database optimization and indexing

## Development Approach:
1. Review API requirements and data models
2. Design database schema
3. Implement API endpoints with validation
4. Add business logic and integrations
5. Write comprehensive tests
6. Document APIs

When developing backend code, focus on security, scalability, and maintainability.
"""


class BackendDeveloperAgent(BaseAgent):
    """Agent for backend server-side development."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        mode: AgentMode = AgentMode.AUTOMATED,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        config = AgentConfig(
            name="Backend Developer",
            description="Server-side logic and API development",
            phase="design_build",
            system_prompt=BACKEND_DEVELOPER_SYSTEM_PROMPT,
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
                # Architecture
                "create_technical_design",
                "define_architecture",
                # Testing
                "run_tests",
                # Quality
                "run_linter",
                "check_code_quality",
                "review_code",
                "security_check",
                # Database
                "backup_database",
                # Documentation
                "create_documentation",
                "generate_docs",
                # Dependencies
                "analyze_dependencies",
            ],
            mode=mode,
        )
        super().__init__(config, tool_registry, approval_callback, progress_callback=progress_callback)

    def _process_output(self, output: str) -> AgentResult:
        """Process backend developer output."""
        files_created = [
            tc for tc in self.tool_call_history
            if tc["tool"] in ["generate_code", "write_file", "file_write"]
        ]

        tests_passed = any(
            tc["tool"] == "run_tests" and "passed" in tc.get("result", "").lower()
            for tc in self.tool_call_history
        )

        security_checked = any(
            tc["tool"] == "security_check"
            for tc in self.tool_call_history
        )

        return AgentResult(
            success=True,
            output=output,
            artifacts={
                "phase": "design_build",
                "role": "backend_developer",
                "files_created": len(files_created),
                "tests_passed": tests_passed,
                "security_checked": security_checked,
            },
            tool_calls=self.tool_call_history,
            requires_next_phase=False,
            next_phase_input=None,
        )
