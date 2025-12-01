"""Workflow modes for DSDM agents.

Defines the different ways agents can interact with developers:
- AGENT_WRITES_CODE: Agent autonomously writes code using tools
- AGENT_PROVIDES_TIPS: Agent provides guidance/tips without writing code
- MANUAL_WITH_TIPS: Developer writes code manually, agent provides contextual tips
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowMode(Enum):
    """How the agent interacts with the developer."""
    AGENT_WRITES_CODE = "agent_writes_code"      # Agent writes code autonomously
    AGENT_PROVIDES_TIPS = "agent_provides_tips"  # Agent provides tips/guidance only
    MANUAL_WITH_TIPS = "manual_with_tips"        # Developer writes, agent advises


@dataclass
class CodingTip:
    """A coding tip or best practice recommendation."""
    category: str           # e.g., "security", "performance", "testing", "architecture"
    title: str              # Brief title
    description: str        # Full description
    code_example: Optional[str] = None    # Optional code example
    documentation_url: Optional[str] = None  # Link to official docs
    priority: str = "medium"  # "high", "medium", "low"
    provider: Optional[str] = None  # Which LLM provider's docs this comes from
    framework: Optional[str] = None  # Which framework this applies to (e.g., "react", "node")


@dataclass
class TipsContext:
    """Context for generating tips based on the current task."""
    task_description: str
    language: str = "python"
    framework: Optional[str] = None
    existing_code: Optional[str] = None
    file_path: Optional[str] = None
    specific_concerns: List[str] = field(default_factory=list)


# Best practices organized by category and language/framework
BEST_PRACTICES_LIBRARY = {
    "python": {
        "general": [
            CodingTip(
                category="code_quality",
                title="Use Type Hints",
                description="Add type hints to function signatures for better code clarity and IDE support.",
                code_example='def calculate_total(items: List[Item], discount: float = 0.0) -> float:',
                documentation_url="https://docs.python.org/3/library/typing.html",
                priority="high",
            ),
            CodingTip(
                category="code_quality",
                title="Follow PEP 8 Style Guide",
                description="Adhere to PEP 8 for consistent, readable Python code. Use tools like black, flake8, or ruff.",
                documentation_url="https://pep8.org/",
                priority="high",
            ),
            CodingTip(
                category="error_handling",
                title="Use Specific Exception Types",
                description="Catch specific exceptions rather than bare except clauses. This makes debugging easier.",
                code_example='try:\n    result = api_call()\nexcept HTTPError as e:\n    logger.error(f"API failed: {e}")\nexcept Timeout:\n    retry_with_backoff()',
                priority="high",
            ),
            CodingTip(
                category="testing",
                title="Write Tests First (TDD)",
                description="Consider writing tests before implementation to clarify requirements and ensure testability.",
                code_example='def test_user_registration_validates_email():\n    with pytest.raises(ValidationError):\n        User.register(email="invalid")',
                priority="medium",
            ),
            CodingTip(
                category="security",
                title="Never Hardcode Secrets",
                description="Use environment variables or secret managers for API keys, passwords, and tokens.",
                code_example='import os\napi_key = os.environ.get("API_KEY")\n# or use python-dotenv',
                documentation_url="https://12factor.net/config",
                priority="high",
            ),
            CodingTip(
                category="performance",
                title="Use Generators for Large Data",
                description="Use generators instead of lists when processing large datasets to save memory.",
                code_example='def process_large_file(path):\n    with open(path) as f:\n        for line in f:\n            yield transform(line)',
                priority="medium",
            ),
            CodingTip(
                category="architecture",
                title="Single Responsibility Principle",
                description="Each function/class should do one thing well. If a function is hard to name, it might be doing too much.",
                priority="high",
            ),
            CodingTip(
                category="documentation",
                title="Write Meaningful Docstrings",
                description="Document the 'why' not just the 'what'. Include examples for complex functions.",
                code_example='def retry_with_backoff(func, max_retries=3):\n    """Retry a function with exponential backoff.\n    \n    Args:\n        func: The function to retry\n        max_retries: Maximum retry attempts (default: 3)\n    \n    Returns:\n        The function result on success\n    \n    Raises:\n        MaxRetriesExceeded: If all retries fail\n    \n    Example:\n        >>> result = retry_with_backoff(api_call)\n    """',
                priority="medium",
            ),
        ],
        "async": [
            CodingTip(
                category="async",
                title="Use asyncio.gather for Concurrent Tasks",
                description="Run multiple async operations concurrently with asyncio.gather.",
                code_example='results = await asyncio.gather(\n    fetch_users(),\n    fetch_orders(),\n    fetch_products(),\n)',
                documentation_url="https://docs.python.org/3/library/asyncio-task.html",
                priority="high",
            ),
            CodingTip(
                category="async",
                title="Avoid Blocking Calls in Async Code",
                description="Use run_in_executor for CPU-bound or blocking I/O operations.",
                code_example='loop = asyncio.get_event_loop()\nresult = await loop.run_in_executor(None, blocking_function)',
                priority="high",
            ),
        ],
        "testing": [
            CodingTip(
                category="testing",
                title="Use pytest Fixtures",
                description="Create reusable test fixtures for common setup/teardown.",
                code_example='@pytest.fixture\ndef db_session():\n    session = create_session()\n    yield session\n    session.rollback()',
                documentation_url="https://docs.pytest.org/en/stable/fixture.html",
                priority="high",
            ),
            CodingTip(
                category="testing",
                title="Mock External Dependencies",
                description="Use unittest.mock or pytest-mock to isolate tests from external services.",
                code_example='@patch("module.external_api")\ndef test_process(mock_api):\n    mock_api.return_value = {"status": "ok"}\n    result = process_data()\n    assert result.success',
                priority="high",
            ),
            CodingTip(
                category="testing",
                title="Test Edge Cases",
                description="Include tests for empty inputs, None values, boundary conditions, and error scenarios.",
                priority="medium",
            ),
        ],
        "api": [
            CodingTip(
                category="api",
                title="Use Pydantic for Validation",
                description="Use Pydantic models for request/response validation and serialization.",
                code_example='class UserCreate(BaseModel):\n    email: EmailStr\n    password: str = Field(min_length=8)\n    \n    @validator("password")\n    def validate_password(cls, v):\n        # Add complexity requirements\n        return v',
                documentation_url="https://docs.pydantic.dev/",
                priority="high",
            ),
            CodingTip(
                category="api",
                title="Implement Proper Error Responses",
                description="Return consistent error responses with appropriate HTTP status codes.",
                code_example='@app.exception_handler(ValidationError)\nasync def validation_error_handler(request, exc):\n    return JSONResponse(\n        status_code=422,\n        content={"detail": exc.errors()}\n    )',
                priority="high",
            ),
        ],
    },
    "javascript": {
        "general": [
            CodingTip(
                category="code_quality",
                title="Use TypeScript",
                description="Consider using TypeScript for type safety and better developer experience.",
                documentation_url="https://www.typescriptlang.org/docs/",
                priority="high",
            ),
            CodingTip(
                category="code_quality",
                title="Use const and let, Avoid var",
                description="Use const by default, let when reassignment is needed. Never use var.",
                priority="high",
            ),
            CodingTip(
                category="async",
                title="Use async/await Over Callbacks",
                description="Prefer async/await syntax over callbacks or raw promises for cleaner code.",
                code_example='async function fetchData() {\n  try {\n    const response = await fetch(url);\n    const data = await response.json();\n    return data;\n  } catch (error) {\n    console.error("Fetch failed:", error);\n  }\n}',
                priority="high",
            ),
            CodingTip(
                category="security",
                title="Sanitize User Input",
                description="Always sanitize and validate user input to prevent XSS and injection attacks.",
                priority="high",
            ),
            CodingTip(
                category="error_handling",
                title="Use Error Boundaries in React",
                description="Wrap components with Error Boundaries to gracefully handle rendering errors.",
                code_example='class ErrorBoundary extends React.Component {\n  componentDidCatch(error, info) {\n    logError(error, info);\n  }\n  render() {\n    if (this.state.hasError) {\n      return <FallbackUI />;\n    }\n    return this.props.children;\n  }\n}',
                priority="high",
                framework="react",
            ),
        ],
        "react": [
            CodingTip(
                category="performance",
                title="Use useMemo and useCallback",
                description="Memoize expensive computations and callbacks to prevent unnecessary re-renders.",
                code_example='const memoizedValue = useMemo(() => computeExpensive(a, b), [a, b]);\nconst memoizedCallback = useCallback(() => doSomething(id), [id]);',
                documentation_url="https://react.dev/reference/react/useMemo",
                priority="medium",
            ),
            CodingTip(
                category="architecture",
                title="Keep Components Small and Focused",
                description="Components should do one thing well. Extract logic into custom hooks.",
                priority="high",
            ),
            CodingTip(
                category="testing",
                title="Use React Testing Library",
                description="Test components by how users interact with them, not implementation details.",
                code_example='test("shows error on invalid email", async () => {\n  render(<LoginForm />);\n  await userEvent.type(screen.getByRole("textbox"), "invalid");\n  expect(screen.getByRole("alert")).toHaveTextContent(/email/i);\n});',
                documentation_url="https://testing-library.com/docs/react-testing-library/intro/",
                priority="high",
            ),
        ],
        "node": [
            CodingTip(
                category="security",
                title="Use Helmet for Express Security",
                description="Add helmet middleware to set security-related HTTP headers.",
                code_example='const helmet = require("helmet");\napp.use(helmet());',
                documentation_url="https://helmetjs.github.io/",
                priority="high",
            ),
            CodingTip(
                category="performance",
                title="Use Streaming for Large Data",
                description="Use streams instead of loading entire files into memory.",
                code_example='const readStream = fs.createReadStream("large-file.txt");\nreadStream.pipe(res);',
                priority="medium",
            ),
        ],
    },
}


def get_tips_for_context(context: TipsContext) -> List[CodingTip]:
    """Get relevant coding tips based on the context."""
    tips = []

    # Get language-specific tips
    language_tips = BEST_PRACTICES_LIBRARY.get(context.language, {})

    # Add general tips for the language
    tips.extend(language_tips.get("general", []))

    # Add framework-specific tips if applicable
    if context.framework:
        framework_tips = language_tips.get(context.framework.lower(), [])
        tips.extend(framework_tips)

    # Add category-specific tips based on concerns
    for concern in context.specific_concerns:
        category_tips = language_tips.get(concern.lower(), [])
        tips.extend(category_tips)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tips.sort(key=lambda t: priority_order.get(t.priority, 2))

    return tips


def format_tips_as_markdown(tips: List[CodingTip], max_tips: int = 10) -> str:
    """Format tips as markdown for display."""
    if not tips:
        return "No specific tips for this context."

    lines = ["## Coding Tips & Best Practices\n"]

    for i, tip in enumerate(tips[:max_tips], 1):
        priority_label = {"high": "[HIGH]", "medium": "[MEDIUM]", "low": "[LOW]"}.get(tip.priority, "")
        lines.append(f"### {i}. {priority_label} {tip.title}")
        lines.append(f"**Category:** {tip.category.replace('_', ' ').title()}")
        lines.append(f"\n{tip.description}\n")

        if tip.code_example:
            lines.append("**Example:**")
            lines.append(f"```\n{tip.code_example}\n```\n")

        if tip.documentation_url:
            lines.append(f"[Documentation]({tip.documentation_url})\n")

        lines.append("---\n")

    return "\n".join(lines)


# System prompt additions for each workflow mode
WORKFLOW_MODE_PROMPTS = {
    WorkflowMode.AGENT_WRITES_CODE: """
## Workflow Mode: AGENT WRITES CODE
You are operating in autonomous code-writing mode. You will:
1. Analyze the requirements thoroughly
2. Design the solution architecture
3. Write production-quality code using file_write and other tools
4. Create comprehensive tests
5. Document your implementation

Write actual, working code that follows best practices.
""",

    WorkflowMode.AGENT_PROVIDES_TIPS: """
## Workflow Mode: AGENT PROVIDES TIPS
You are operating in advisory mode. You will:
1. Analyze the requirements and provide architectural guidance
2. Suggest best practices and patterns to follow
3. Provide code examples and templates for reference
4. Highlight potential pitfalls and how to avoid them
5. Reference official documentation where helpful

DO NOT write actual project files. Instead, provide guidance, examples, and recommendations
that the developer can use to implement the solution themselves.

Format your response with:
- **Architecture Overview**: High-level design recommendations
- **Implementation Tips**: Specific coding advice
- **Code Examples**: Reference implementations (not project files)
- **Testing Strategy**: How to approach testing
- **Common Pitfalls**: What to avoid
- **Resources**: Links to relevant documentation
""",

    WorkflowMode.MANUAL_WITH_TIPS: """
## Workflow Mode: MANUAL CODING WITH TIPS
You are operating as a coding assistant. The developer will write the code manually,
and you will provide contextual tips and feedback.

When the developer shares code or asks questions:
1. Review the code/approach critically
2. Suggest improvements based on best practices
3. Point out potential issues (security, performance, maintainability)
4. Provide specific, actionable recommendations
5. Answer questions with detailed explanations

Be constructive and specific. Reference official documentation when relevant.
Focus on helping the developer learn and improve their skills.
""",
}


def get_workflow_mode_prompt(mode: WorkflowMode) -> str:
    """Get the system prompt addition for a workflow mode."""
    return WORKFLOW_MODE_PROMPTS.get(mode, "")
