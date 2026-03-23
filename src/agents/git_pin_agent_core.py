"""Git Pin Agent Core - Event-driven agent loop with parallel tool execution.

Adapted from pi-mono's agent-core architecture to optimize throughput
within the DSDM framework. Provides:
- Event-driven agent loop with streaming support
- Parallel and sequential tool execution modes
- Steering messages (mid-run injection) and follow-up message queues
- Before/after tool call hooks for validation and transformation
- Context window management with message pruning
"""

import asyncio
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .base_agent import (
    AgentConfig,
    AgentMode,
    AgentResult,
    BaseAgent,
    ProgressCallback,
    ProgressEvent,
)
from ..tools.tool_registry import Tool, ToolRegistry


# ---------------------------------------------------------------------------
# Event types mirroring pi-mono's AgentEvent system
# ---------------------------------------------------------------------------

class GitPinEventType(Enum):
    """Event types emitted during a Git pin agent loop."""
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    MESSAGE_START = "message_start"
    MESSAGE_UPDATE = "message_update"
    MESSAGE_END = "message_end"
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_UPDATE = "tool_execution_update"
    TOOL_EXECUTION_END = "tool_execution_end"
    STEERING_INJECTED = "steering_injected"
    FOLLOW_UP_INJECTED = "follow_up_injected"
    CONTEXT_PRUNED = "context_pruned"
    THROUGHPUT_REPORT = "throughput_report"


@dataclass
class GitPinEvent:
    """An event emitted by the Git pin agent loop."""
    type: GitPinEventType
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)


# Type alias for event sink callback
EventSink = Callable[[GitPinEvent], None]


# ---------------------------------------------------------------------------
# Tool execution modes
# ---------------------------------------------------------------------------

class ToolExecutionMode(Enum):
    """How tool calls from a single assistant message are executed."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


# ---------------------------------------------------------------------------
# Before / After tool call hooks
# ---------------------------------------------------------------------------

@dataclass
class BeforeToolCallContext:
    """Context passed to before_tool_call hook."""
    tool_name: str
    tool_input: Dict[str, Any]
    assistant_message: str
    agent_context: Dict[str, Any]


@dataclass
class BeforeToolCallResult:
    """Result from before_tool_call hook."""
    block: bool = False
    reason: Optional[str] = None


@dataclass
class AfterToolCallContext:
    """Context passed to after_tool_call hook."""
    tool_name: str
    tool_input: Dict[str, Any]
    result: str
    is_error: bool
    assistant_message: str
    agent_context: Dict[str, Any]


@dataclass
class AfterToolCallResult:
    """Result from after_tool_call hook - overrides parts of tool result."""
    content: Optional[str] = None
    is_error: Optional[bool] = None


# ---------------------------------------------------------------------------
# Throughput metrics
# ---------------------------------------------------------------------------

@dataclass
class ThroughputMetrics:
    """Tracks agent loop throughput statistics."""
    total_turns: int = 0
    total_tool_calls: int = 0
    parallel_tool_batches: int = 0
    sequential_tool_calls: int = 0
    total_tool_execution_time_ms: float = 0
    total_llm_call_time_ms: float = 0
    steering_messages_processed: int = 0
    follow_up_messages_processed: int = 0
    context_prunes: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def elapsed_ms(self) -> float:
        return (time.time() - self.start_time) * 1000

    @property
    def avg_tool_time_ms(self) -> float:
        if self.total_tool_calls == 0:
            return 0
        return self.total_tool_execution_time_ms / self.total_tool_calls

    @property
    def throughput_tools_per_sec(self) -> float:
        elapsed_s = self.elapsed_ms / 1000
        if elapsed_s == 0:
            return 0
        return self.total_tool_calls / elapsed_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_turns": self.total_turns,
            "total_tool_calls": self.total_tool_calls,
            "parallel_batches": self.parallel_tool_batches,
            "sequential_calls": self.sequential_tool_calls,
            "avg_tool_time_ms": round(self.avg_tool_time_ms, 2),
            "total_tool_time_ms": round(self.total_tool_execution_time_ms, 2),
            "total_llm_time_ms": round(self.total_llm_call_time_ms, 2),
            "elapsed_ms": round(self.elapsed_ms, 2),
            "throughput_tools_per_sec": round(self.throughput_tools_per_sec, 2),
            "steering_messages": self.steering_messages_processed,
            "follow_up_messages": self.follow_up_messages_processed,
            "context_prunes": self.context_prunes,
        }


# ---------------------------------------------------------------------------
# Git Pin Agent Loop Configuration
# ---------------------------------------------------------------------------

@dataclass
class GitPinLoopConfig:
    """Configuration for the Git pin agent loop."""
    tool_execution: ToolExecutionMode = ToolExecutionMode.PARALLEL
    max_parallel_tools: int = 8
    max_context_messages: int = 200
    prune_keep_recent: int = 40
    enable_steering: bool = True
    enable_follow_up: bool = True
    before_tool_call: Optional[Callable[[BeforeToolCallContext], Optional[BeforeToolCallResult]]] = None
    after_tool_call: Optional[Callable[[AfterToolCallContext], Optional[AfterToolCallResult]]] = None
    get_steering_messages: Optional[Callable[[], List[Dict[str, Any]]]] = None
    get_follow_up_messages: Optional[Callable[[], List[Dict[str, Any]]]] = None
    transform_context: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None


# ---------------------------------------------------------------------------
# Core Agent Loop
# ---------------------------------------------------------------------------

class GitPinAgentLoop:
    """Event-driven agent loop adapted from pi-mono's architecture.

    Provides high-throughput tool execution with parallel batching,
    mid-run steering, follow-up message processing, and context
    window management.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        loop_config: Optional[GitPinLoopConfig] = None,
        event_sink: Optional[EventSink] = None,
    ):
        self.tool_registry = tool_registry
        self.config = loop_config or GitPinLoopConfig()
        self.event_sink = event_sink
        self.metrics = ThroughputMetrics()
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_parallel_tools)

    def _emit(self, event_type: GitPinEventType, **data) -> None:
        """Emit an event to the event sink."""
        if self.event_sink:
            self.event_sink(GitPinEvent(type=event_type, data=data))

    # ------------------------------------------------------------------
    # Context window management
    # ------------------------------------------------------------------

    def _maybe_prune_context(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prune context window if it exceeds the max limit."""
        if len(messages) <= self.config.max_context_messages:
            return messages

        self.metrics.context_prunes += 1
        keep = self.config.prune_keep_recent

        # Always keep the first message (system/initial prompt) and recent messages
        pruned = [messages[0]] + messages[-keep:]
        self._emit(
            GitPinEventType.CONTEXT_PRUNED,
            original_count=len(messages),
            pruned_count=len(pruned),
        )
        return pruned

    def _apply_context_transform(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply optional context transformation."""
        if self.config.transform_context:
            return self.config.transform_context(messages)
        return messages

    # ------------------------------------------------------------------
    # Tool execution (parallel + sequential)
    # ------------------------------------------------------------------

    def _prepare_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        assistant_message: str,
        agent_context: Dict[str, Any],
    ) -> Tuple[Optional[Tool], Optional[Dict[str, Any]], Optional[str]]:
        """Prepare a tool call: validate and run before hook.

        Returns (tool, validated_input, error_message).
        """
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            # Try normalizing
            for prefix in ["files.", "tools.", "file.", "tool."]:
                if tool_name.lower().startswith(prefix):
                    tool = self.tool_registry.get(tool_name[len(prefix):])
                    if tool:
                        break
        if tool is None:
            return None, None, f"Tool '{tool_name}' not found"

        # Before hook
        if self.config.before_tool_call:
            ctx = BeforeToolCallContext(
                tool_name=tool.name,
                tool_input=tool_input,
                assistant_message=assistant_message,
                agent_context=agent_context,
            )
            result = self.config.before_tool_call(ctx)
            if result and result.block:
                return None, None, result.reason or "Tool execution was blocked"

        return tool, tool_input, None

    def _execute_single_tool(
        self,
        tool: Tool,
        tool_input: Dict[str, Any],
        tool_call_id: str,
        assistant_message: str,
        agent_context: Dict[str, Any],
    ) -> Tuple[str, bool]:
        """Execute a single tool and apply after hook.

        Returns (result_content, is_error).
        """
        self._emit(
            GitPinEventType.TOOL_EXECUTION_START,
            tool_call_id=tool_call_id,
            tool_name=tool.name,
            args=tool_input,
        )

        start = time.time()
        is_error = False
        try:
            result = tool.execute(**tool_input)
        except Exception as e:
            result = f"Error executing {tool.name}: {str(e)}"
            is_error = True

        elapsed_ms = (time.time() - start) * 1000
        self.metrics.total_tool_execution_time_ms += elapsed_ms
        self.metrics.total_tool_calls += 1

        # After hook
        if self.config.after_tool_call:
            ctx = AfterToolCallContext(
                tool_name=tool.name,
                tool_input=tool_input,
                result=result,
                is_error=is_error,
                assistant_message=assistant_message,
                agent_context=agent_context,
            )
            after = self.config.after_tool_call(ctx)
            if after:
                if after.content is not None:
                    result = after.content
                if after.is_error is not None:
                    is_error = after.is_error

        self._emit(
            GitPinEventType.TOOL_EXECUTION_END,
            tool_call_id=tool_call_id,
            tool_name=tool.name,
            is_error=is_error,
            elapsed_ms=elapsed_ms,
        )

        return result, is_error

    def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        assistant_message: str,
        agent_context: Dict[str, Any],
        approval_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Execute tool calls with configured execution mode.

        Returns list of tool result dicts for message history.
        """
        if self.config.tool_execution == ToolExecutionMode.SEQUENTIAL:
            return self._execute_sequential(
                tool_calls, assistant_message, agent_context, approval_callback
            )
        return self._execute_parallel(
            tool_calls, assistant_message, agent_context, approval_callback
        )

    def _execute_sequential(
        self,
        tool_calls: List[Dict[str, Any]],
        assistant_message: str,
        agent_context: Dict[str, Any],
        approval_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Execute tool calls one by one."""
        results = []
        for tc in tool_calls:
            self.metrics.sequential_tool_calls += 1
            result = self._process_one_tool_call(
                tc, assistant_message, agent_context, approval_callback
            )
            results.append(result)
        return results

    def _execute_parallel(
        self,
        tool_calls: List[Dict[str, Any]],
        assistant_message: str,
        agent_context: Dict[str, Any],
        approval_callback: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Execute tool calls in parallel where possible.

        Tools are prepared sequentially (for before-hook ordering),
        then executed concurrently.
        """
        self.metrics.parallel_tool_batches += 1

        # Phase 1: Prepare all tool calls sequentially
        prepared = []
        immediate_results = []

        for tc in tool_calls:
            tool_name = tc["name"]
            tool_input = tc.get("input", {})
            tool_call_id = tc.get("id", f"tc_{len(prepared)}")

            tool, validated_input, error = self._prepare_tool_call(
                tool_name, tool_input, assistant_message, agent_context
            )

            if error:
                immediate_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": error,
                    "is_error": True,
                    "index": tc.get("_index", len(prepared) + len(immediate_results)),
                })
            else:
                # Check approval
                if approval_callback and tool.requires_approval:
                    if not approval_callback(tool.name, tool_input):
                        immediate_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_call_id,
                            "content": f"Tool execution denied: {tool.name}",
                            "is_error": True,
                            "index": tc.get("_index", len(prepared) + len(immediate_results)),
                        })
                        continue

                prepared.append({
                    "tool": tool,
                    "input": validated_input,
                    "id": tool_call_id,
                    "index": tc.get("_index", len(prepared) + len(immediate_results)),
                })

        # Phase 2: Execute prepared tools in parallel
        parallel_results = []
        if prepared:
            futures = {}
            for p in prepared:
                future = self._executor.submit(
                    self._execute_single_tool,
                    p["tool"],
                    p["input"],
                    p["id"],
                    assistant_message,
                    agent_context,
                )
                futures[future] = p

            for future in as_completed(futures):
                p = futures[future]
                try:
                    content, is_error = future.result()
                except Exception as e:
                    content = f"Parallel execution error: {str(e)}"
                    is_error = True

                parallel_results.append({
                    "type": "tool_result",
                    "tool_use_id": p["id"],
                    "content": content,
                    "is_error": is_error,
                    "index": p["index"],
                })

        # Merge and sort by original order
        all_results = immediate_results + parallel_results
        all_results.sort(key=lambda r: r.get("index", 0))

        # Clean up index field
        for r in all_results:
            r.pop("index", None)
            r.pop("is_error", None)

        return all_results

    def _process_one_tool_call(
        self,
        tc: Dict[str, Any],
        assistant_message: str,
        agent_context: Dict[str, Any],
        approval_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Process a single tool call through the full lifecycle."""
        tool_name = tc["name"]
        tool_input = tc.get("input", {})
        tool_call_id = tc.get("id", "tc_0")

        tool, validated_input, error = self._prepare_tool_call(
            tool_name, tool_input, assistant_message, agent_context
        )

        if error:
            return {
                "type": "tool_result",
                "tool_use_id": tool_call_id,
                "content": error,
            }

        # Check approval
        if approval_callback and tool.requires_approval:
            if not approval_callback(tool.name, tool_input):
                return {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": f"Tool execution denied: {tool.name}",
                }

        content, _ = self._execute_single_tool(
            tool, validated_input, tool_call_id, assistant_message, agent_context
        )

        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": content,
        }

    # ------------------------------------------------------------------
    # Steering & follow-up message retrieval
    # ------------------------------------------------------------------

    def get_steering_messages(self) -> List[Dict[str, Any]]:
        """Retrieve pending steering messages."""
        if not self.config.enable_steering or not self.config.get_steering_messages:
            return []
        messages = self.config.get_steering_messages()
        if messages:
            self.metrics.steering_messages_processed += len(messages)
            self._emit(
                GitPinEventType.STEERING_INJECTED,
                count=len(messages),
            )
        return messages

    def get_follow_up_messages(self) -> List[Dict[str, Any]]:
        """Retrieve pending follow-up messages."""
        if not self.config.enable_follow_up or not self.config.get_follow_up_messages:
            return []
        messages = self.config.get_follow_up_messages()
        if messages:
            self.metrics.follow_up_messages_processed += len(messages)
            self._emit(
                GitPinEventType.FOLLOW_UP_INJECTED,
                count=len(messages),
            )
        return messages

    def report_throughput(self) -> Dict[str, Any]:
        """Generate a throughput report."""
        report = self.metrics.to_dict()
        self._emit(GitPinEventType.THROUGHPUT_REPORT, **report)
        return report

    def shutdown(self) -> None:
        """Clean up thread pool."""
        self._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Git Pin Base Agent - extends BaseAgent with the high-throughput loop
# ---------------------------------------------------------------------------

class GitPinBaseAgent(BaseAgent):
    """Base agent class that uses the Git pin event-driven loop for
    higher throughput tool execution and advanced loop control.
    """

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        approval_callback: Optional[Callable] = None,
        llm_client=None,
        progress_callback: Optional[ProgressCallback] = None,
        loop_config: Optional[GitPinLoopConfig] = None,
    ):
        super().__init__(
            config=config,
            tool_registry=tool_registry,
            approval_callback=approval_callback,
            llm_client=llm_client,
            progress_callback=progress_callback,
        )
        self._loop = GitPinAgentLoop(
            tool_registry=tool_registry,
            loop_config=loop_config or GitPinLoopConfig(),
            event_sink=self._handle_loop_event,
        )

    def _handle_loop_event(self, event: GitPinEvent) -> None:
        """Bridge loop events to progress callbacks."""
        event_map = {
            GitPinEventType.AGENT_START: ProgressEvent.STARTED,
            GitPinEventType.TOOL_EXECUTION_START: ProgressEvent.TOOL_CALLING,
            GitPinEventType.TOOL_EXECUTION_END: ProgressEvent.TOOL_COMPLETED,
            GitPinEventType.AGENT_END: ProgressEvent.COMPLETED,
        }
        mapped = event_map.get(event.type)
        if mapped:
            self._emit_progress(
                mapped,
                f"[GitPin] {event.type.value}",
                details=event.data,
            )

    def run(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Run the agent using the Git pin event-driven loop.

        Uses the high-throughput parallel tool execution engine while
        maintaining compatibility with the DSDM BaseAgent interface.
        """
        self._emit_progress(
            ProgressEvent.STARTED,
            f"[GitPin] Starting: {user_input[:80]}...",
            details={"context": context} if context else None,
        )
        self._loop.metrics = ThroughputMetrics()
        self._loop._emit(GitPinEventType.AGENT_START)

        # Build initial message
        message_content = user_input
        if context:
            message_content = f"Context: {json.dumps(context, default=str)}\n\nTask: {user_input}"

        # Generate tips for non-code modes
        tips = None
        if self.config.workflow_mode.value in ("agent_provides_tips", "manual_with_tips"):
            tips = self._generate_tips(user_input)
            message_content = f"{message_content}\n\n## Relevant Best Practices:\n{tips}"

        self.messages = [{"role": "user", "content": message_content}]
        self.tool_call_history = []

        tools = self.get_tools_anthropic_format() if self._should_use_tools() else []
        effective_prompt = self._get_effective_system_prompt()
        iterations = 0

        # Outer loop: continues when follow-up messages arrive
        while True:
            has_more_tool_calls = True
            pending_steering = self._loop.get_steering_messages()

            # Inner loop: process tool calls and steering messages
            while has_more_tool_calls or pending_steering:
                self._loop._emit(GitPinEventType.TURN_START)
                self._loop.metrics.total_turns += 1
                iterations += 1

                if iterations > self.config.max_iterations:
                    break

                # Inject steering messages
                if pending_steering:
                    for msg in pending_steering:
                        self.messages.append(msg)
                    pending_steering = []

                # Context management
                self.messages = self._loop._maybe_prune_context(self.messages)
                effective_messages = self._loop._apply_context_transform(self.messages)

                self._emit_progress(
                    ProgressEvent.THINKING,
                    f"[GitPin] Turn {iterations}/{self.config.max_iterations}",
                    iteration=iterations,
                )

                # LLM call with timing
                llm_start = time.time()
                response = self.llm_client.chat(
                    messages=effective_messages,
                    system_prompt=effective_prompt,
                    tools=tools if tools else None,
                    max_tokens=self.config.max_tokens,
                )
                self._loop.metrics.total_llm_call_time_ms += (time.time() - llm_start) * 1000

                stop_reason = response.get("stop_reason", "")
                tool_calls = response.get("tool_calls", [])

                if tool_calls and self._should_use_tools():
                    # Add assistant message
                    if "raw_content" in response:
                        self.messages.append({"role": "assistant", "content": response["raw_content"]})
                    else:
                        self.messages.append({"role": "assistant", "content": response.get("content", "")})

                    assistant_text = response.get("content", "")

                    # Annotate tool calls with index for ordering
                    for i, tc in enumerate(tool_calls):
                        tc["_index"] = i

                    # Execute via Git pin loop (parallel or sequential)
                    tool_results = self._loop.execute_tool_calls(
                        tool_calls=tool_calls,
                        assistant_message=assistant_text,
                        agent_context={"phase": self.config.phase, "iteration": iterations},
                        approval_callback=self.approval_callback,
                    )

                    # Record in history
                    for tc, tr in zip(tool_calls, tool_results):
                        self.tool_call_history.append({
                            "tool": tc["name"],
                            "input": tc.get("input", {}),
                            "result": tr["content"],
                        })

                    self.messages.append({"role": "user", "content": tool_results})
                    has_more_tool_calls = True

                elif stop_reason in ("end_turn", "stop", "end", ""):
                    has_more_tool_calls = False
                else:
                    has_more_tool_calls = False

                # Check for new steering messages
                pending_steering = self._loop.get_steering_messages()

                # Emit turn end
                self._loop._emit(
                    GitPinEventType.TURN_END,
                    iteration=iterations,
                    tool_calls_count=len(tool_calls),
                )

            # Check iteration limit
            if iterations >= self.config.max_iterations:
                break

            # Check for follow-up messages
            follow_ups = self._loop.get_follow_up_messages()
            if follow_ups:
                for msg in follow_ups:
                    self.messages.append(msg)
                continue
            break

        # Extract final output
        output = response.get("content", "")
        if not output and "raw_content" in response:
            raw_content = response["raw_content"]
            if isinstance(raw_content, list):
                for block in raw_content:
                    if hasattr(block, "text"):
                        output = block.text
                        break
            elif isinstance(raw_content, str):
                output = raw_content

        # Build result with throughput metrics
        throughput_report = self._loop.report_throughput()
        result = self._process_output(output)
        result.tips = tips
        result.workflow_mode = self.config.workflow_mode
        result.artifacts["git_pin_throughput"] = throughput_report

        self._loop._emit(GitPinEventType.AGENT_END, metrics=throughput_report)
        self._emit_progress(
            ProgressEvent.COMPLETED,
            f"[GitPin] Completed - {throughput_report['total_tool_calls']} tool calls, "
            f"{throughput_report['throughput_tools_per_sec']:.1f} tools/sec",
            details=throughput_report,
        )

        return result
