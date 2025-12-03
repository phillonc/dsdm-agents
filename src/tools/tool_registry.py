"""Tool Registry for DSDM Agents."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import json


@dataclass
class Tool:
    """Represents a tool that can be used by an agent."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., str]
    requires_approval: bool = False  # If True, requires manual approval before execution
    category: str = "general"

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic API tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    # Common parameter aliases to handle LLM variations
    PARAMETER_ALIASES = {
        "path": "file_path",
        "filepath": "file_path",
        "filename": "file_path",
        "file": "file_path",
        "dir": "dir_path",
        "directory": "dir_path",
        "dirpath": "dir_path",
        "text": "content",
        "body": "content",
        "data": "content",
        "source": "source_path",
        "dest": "dest_path",
        "destination": "dest_path",
        "name": "project_name",
        "project": "project_name",
    }

    def execute(self, **kwargs) -> str:
        """Execute the tool with given arguments.

        Filters kwargs to only include parameters defined in the tool's input schema.
        This protects against LLM providers (like Gemini) returning extra fields
        in function call arguments that aren't part of the expected schema.
        Also applies parameter aliasing to handle common LLM variations.
        """
        try:
            # Apply parameter aliases to normalize LLM variations
            expected_params = set(self.input_schema.get("properties", {}).keys())
            normalized_kwargs = {}
            for k, v in kwargs.items():
                # Check if this is an alias for an expected parameter
                if k not in expected_params and k in self.PARAMETER_ALIASES:
                    canonical = self.PARAMETER_ALIASES[k]
                    if canonical in expected_params and canonical not in kwargs:
                        normalized_kwargs[canonical] = v
                        continue
                normalized_kwargs[k] = v

            # Filter kwargs to only include parameters defined in schema
            filtered_kwargs = {k: v for k, v in normalized_kwargs.items() if k in expected_params}

            # Validate required parameters are present
            required_params = set(self.input_schema.get("required", []))
            missing_params = required_params - set(filtered_kwargs.keys())
            if missing_params:
                return json.dumps({
                    "success": False,
                    "error": f"Missing required parameters: {missing_params}",
                    "received_params": list(kwargs.keys()),
                    "expected_params": list(expected_params),
                    "raw_input": {k: str(v)[:100] for k, v in kwargs.items()},  # Truncate for readability
                })

            result = self.handler(**filtered_kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing {self.name}: {str(e)}"


class ToolRegistry:
    """Registry for managing tools across agents."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a category."""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_all(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def to_anthropic_format(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic API format."""
        if tool_names is None:
            tools = self.get_all()
        else:
            tools = [self._tools[name] for name in tool_names if name in self._tools]
        return [tool.to_anthropic_format() for tool in tools]

    def execute(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if tool is None:
            return f"Unknown tool: {tool_name}"
        return tool.execute(**kwargs)


# Global registry instance
global_registry = ToolRegistry()


def register_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    requires_approval: bool = False,
    category: str = "general",
) -> Callable:
    """Decorator to register a function as a tool."""
    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        tool = Tool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=func,
            requires_approval=requires_approval,
            category=category,
        )
        global_registry.register(tool)
        return func
    return decorator
