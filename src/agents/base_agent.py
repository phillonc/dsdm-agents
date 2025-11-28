"""Base Agent class for DSDM methodology agents."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import anthropic
from dotenv import load_dotenv

from ..tools.tool_registry import Tool, ToolRegistry

load_dotenv()


class AgentMode(Enum):
    """Agent execution mode."""
    MANUAL = "manual"      # Requires user approval for each action
    AUTOMATED = "automated"  # Runs autonomously with tools
    HYBRID = "hybrid"       # Some tools require approval, others don't


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    description: str
    phase: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    mode: AgentMode = AgentMode.AUTOMATED
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_iterations: int = 10


@dataclass
class AgentResult:
    """Result from an agent execution."""
    success: bool
    output: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    requires_next_phase: bool = False
    next_phase_input: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """Base class for all DSDM phase agents."""

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
    ):
        self.config = config
        self.tool_registry = tool_registry
        self.approval_callback = approval_callback
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.messages: List[Dict[str, Any]] = []
        self.tool_call_history: List[Dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def phase(self) -> str:
        return self.config.phase

    @property
    def mode(self) -> AgentMode:
        return self.config.mode

    @mode.setter
    def mode(self, value: AgentMode) -> None:
        self.config.mode = value

    def get_tools(self) -> List[Tool]:
        """Get tools available to this agent."""
        return [
            self.tool_registry.get(name)
            for name in self.config.tools
            if self.tool_registry.get(name) is not None
        ]

    def get_tools_anthropic_format(self) -> List[Dict[str, Any]]:
        """Get tools in Anthropic API format."""
        return self.tool_registry.to_anthropic_format(self.config.tools)

    def _should_approve_tool(self, tool: Tool, tool_input: Dict[str, Any]) -> bool:
        """Check if tool execution should proceed."""
        if self.config.mode == AgentMode.AUTOMATED:
            return True
        if self.config.mode == AgentMode.MANUAL:
            if self.approval_callback:
                return self.approval_callback(tool.name, tool_input)
            return False
        # Hybrid mode - check tool's requires_approval flag
        if tool.requires_approval:
            if self.approval_callback:
                return self.approval_callback(tool.name, tool_input)
            return False
        return True

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool with approval check."""
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return f"Unknown tool: {tool_name}"

        if not self._should_approve_tool(tool, tool_input):
            return f"Tool execution denied: {tool_name} (requires approval)"

        result = tool.execute(**tool_input)
        self.tool_call_history.append({
            "tool": tool_name,
            "input": tool_input,
            "result": result,
        })
        return result

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Run the agent with user input."""
        # Build initial message with context
        message_content = user_input
        if context:
            message_content = f"Context: {context}\n\nTask: {user_input}"

        self.messages = [{"role": "user", "content": message_content}]
        self.tool_call_history = []

        tools = self.get_tools_anthropic_format()
        iterations = 0

        while iterations < self.config.max_iterations:
            iterations += 1

            # Call Claude
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                system=self.config.system_prompt,
                tools=tools if tools else None,
                messages=self.messages,
            )

            # Check for tool use
            if response.stop_reason == "tool_use":
                # Add assistant response to messages
                self.messages.append({"role": "assistant", "content": response.content})

                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Add tool results to messages
                self.messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Extract final response
                output = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        output = block.text
                        break

                return self._process_output(output)

            else:
                return AgentResult(
                    success=False,
                    output=f"Unexpected stop reason: {response.stop_reason}",
                )

        return AgentResult(
            success=False,
            output="Max iterations reached",
        )

    @abstractmethod
    def _process_output(self, output: str) -> AgentResult:
        """Process the agent's output. Override in subclasses."""
        pass

    def reset(self) -> None:
        """Reset the agent state."""
        self.messages = []
        self.tool_call_history = []
