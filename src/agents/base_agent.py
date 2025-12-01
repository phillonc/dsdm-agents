"""Base Agent class for DSDM methodology agents."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from ..tools.tool_registry import Tool, ToolRegistry
from ..llm import LLMProvider, LLMConfig, BaseLLMClient, create_llm_client
from .workflow_modes import (
    WorkflowMode,
    TipsContext,
    get_tips_for_context,
    format_tips_as_markdown,
    get_workflow_mode_prompt,
)

load_dotenv()


class AgentMode(Enum):
    """Agent execution mode (tool approval)."""
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
    workflow_mode: WorkflowMode = WorkflowMode.AGENT_WRITES_CODE  # How agent interacts
    model: Optional[str] = None  # If None, uses provider default from env
    max_tokens: int = 4096
    max_iterations: int = 10
    llm_provider: Optional[LLMProvider] = None  # If None, uses LLM_PROVIDER from env


@dataclass
class AgentResult:
    """Result from an agent execution."""
    success: bool
    output: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    requires_next_phase: bool = False
    next_phase_input: Optional[Dict[str, Any]] = None
    tips: Optional[str] = None  # Formatted tips markdown (for TIPS and MANUAL modes)
    workflow_mode: Optional[WorkflowMode] = None  # Mode used for this execution


class BaseAgent(ABC):
    """Base class for all DSDM phase agents."""

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        self.config = config
        self.tool_registry = tool_registry
        self.approval_callback = approval_callback

        # Initialize LLM client - use provided client, or create from config/env
        if llm_client is not None:
            self.llm_client = llm_client
        else:
            llm_config = LLMConfig.from_env(config.llm_provider)
            # Override model if specified in agent config
            if config.model:
                llm_config.model = config.model
            self.llm_client = create_llm_client(config=llm_config)

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

    @property
    def workflow_mode(self) -> WorkflowMode:
        return self.config.workflow_mode

    @workflow_mode.setter
    def workflow_mode(self, value: WorkflowMode) -> None:
        self.config.workflow_mode = value

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

    def _get_effective_system_prompt(self) -> str:
        """Get system prompt with workflow mode adjustments."""
        base_prompt = self.config.system_prompt
        workflow_prompt = get_workflow_mode_prompt(self.config.workflow_mode)
        return f"{base_prompt}\n\n{workflow_prompt}"

    def _should_use_tools(self) -> bool:
        """Determine if tools should be enabled based on workflow mode."""
        # Only use tools in AGENT_WRITES_CODE mode
        return self.config.workflow_mode == WorkflowMode.AGENT_WRITES_CODE

    def _generate_tips(self, user_input: str, language: str = "python", framework: Optional[str] = None) -> str:
        """Generate contextual tips based on the task."""
        # Detect language and framework from input if not specified
        input_lower = user_input.lower()

        if "react" in input_lower or "jsx" in input_lower:
            language = "javascript"
            framework = "react"
        elif "node" in input_lower or "express" in input_lower:
            language = "javascript"
            framework = "node"
        elif "typescript" in input_lower:
            language = "javascript"
        elif "python" in input_lower or "django" in input_lower or "flask" in input_lower or "fastapi" in input_lower:
            language = "python"
            if "async" in input_lower:
                framework = "async"
            if "api" in input_lower or "fastapi" in input_lower:
                framework = "api"

        # Detect specific concerns
        concerns = []
        if any(word in input_lower for word in ["test", "testing", "pytest", "jest"]):
            concerns.append("testing")
        if any(word in input_lower for word in ["security", "auth", "login", "password"]):
            concerns.append("security")
        if any(word in input_lower for word in ["api", "endpoint", "rest", "graphql"]):
            concerns.append("api")
        if any(word in input_lower for word in ["async", "await", "concurrent"]):
            concerns.append("async")

        context = TipsContext(
            task_description=user_input,
            language=language,
            framework=framework,
            specific_concerns=concerns,
        )

        tips = get_tips_for_context(context)
        return format_tips_as_markdown(tips)

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

        # Generate tips for non-code-writing modes
        tips = None
        if self.config.workflow_mode in (WorkflowMode.AGENT_PROVIDES_TIPS, WorkflowMode.MANUAL_WITH_TIPS):
            tips = self._generate_tips(user_input)
            # Add tips to context for the LLM to reference
            message_content = f"{message_content}\n\n## Relevant Best Practices:\n{tips}"

        self.messages = [{"role": "user", "content": message_content}]
        self.tool_call_history = []

        # Only provide tools in AGENT_WRITES_CODE mode
        tools = self.get_tools_anthropic_format() if self._should_use_tools() else []
        effective_prompt = self._get_effective_system_prompt()
        iterations = 0

        while iterations < self.config.max_iterations:
            iterations += 1

            # Call LLM using provider-agnostic client
            response = self.llm_client.chat(
                messages=self.messages,
                system_prompt=effective_prompt,
                tools=tools if tools else None,
                max_tokens=self.config.max_tokens,
            )

            stop_reason = response.get("stop_reason", "")
            tool_calls = response.get("tool_calls", [])

            # Check for tool use (only in AGENT_WRITES_CODE mode)
            if (stop_reason == "tool_use" or tool_calls) and self._should_use_tools():
                # Add assistant response to messages
                # For Anthropic, use raw_content; for others, construct message
                if "raw_content" in response:
                    self.messages.append({"role": "assistant", "content": response["raw_content"]})
                else:
                    # Construct assistant message with tool calls for non-Anthropic providers
                    assistant_content = response.get("content", "")
                    self.messages.append({"role": "assistant", "content": assistant_content})

                # Process tool calls
                tool_results = []
                for tc in tool_calls:
                    result = self._execute_tool(tc["name"], tc["input"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": result,
                    })

                # Add tool results to messages
                self.messages.append({"role": "user", "content": tool_results})

            elif stop_reason in ("end_turn", "stop"):
                # Extract final response
                output = response.get("content", "")
                result = self._process_output(output)
                # Add tips and workflow mode to result
                result.tips = tips
                result.workflow_mode = self.config.workflow_mode
                return result

            else:
                return AgentResult(
                    success=False,
                    output=f"Unexpected stop reason: {stop_reason}",
                    workflow_mode=self.config.workflow_mode,
                )

        return AgentResult(
            success=False,
            output="Max iterations reached",
            workflow_mode=self.config.workflow_mode,
        )

    @abstractmethod
    def _process_output(self, output: str) -> AgentResult:
        """Process the agent's output. Override in subclasses."""
        pass

    def reset(self) -> None:
        """Reset the agent state."""
        self.messages = []
        self.tool_call_history = []
