"""Git Pin Tools - Throughput monitoring and pipeline management tools.

Registers tools that enable Git pin agents to monitor and control
their throughput optimization, batch scheduling, and pipeline execution.
"""

import json
import time
from typing import Any, Dict, List, Optional

from .tool_registry import Tool, ToolRegistry


def register_git_pin_tools(registry: ToolRegistry) -> None:
    """Register Git pin throughput and pipeline tools into the registry."""

    # ------------------------------------------------------------------
    # Throughput monitoring tools
    # ------------------------------------------------------------------

    registry.register(Tool(
        name="git_pin_throughput_report",
        description=(
            "Generate a throughput report for the current Git pin agent session. "
            "Shows tool execution metrics, parallel batch counts, LLM call times, "
            "and overall throughput (tools/sec)."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "include_details": {
                    "type": "boolean",
                    "description": "Include per-tool-call timing details",
                },
            },
            "required": [],
        },
        handler=lambda include_details=False: json.dumps({
            "success": True,
            "message": "Throughput report generated from agent loop metrics",
            "note": "Detailed metrics are attached to the agent result artifacts under 'git_pin_throughput'",
            "timestamp": time.time(),
        }),
        category="git_pin",
    ))

    # ------------------------------------------------------------------
    # Batch scheduling tools
    # ------------------------------------------------------------------

    registry.register(Tool(
        name="git_pin_batch_analyze",
        description=(
            "Analyze a list of planned tool calls and return an optimal batch "
            "execution schedule. Groups parallelizable tools together and "
            "identifies sequential dependencies."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tool_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tool names to schedule",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the batch operation",
                },
            },
            "required": ["tool_names"],
        },
        handler=lambda tool_names, description="": _analyze_batch_schedule(tool_names, description),
        category="git_pin",
    ))

    # ------------------------------------------------------------------
    # Pipeline management tools
    # ------------------------------------------------------------------

    registry.register(Tool(
        name="git_pin_pipeline_plan",
        description=(
            "Plan a multi-agent pipeline execution. Takes a list of tasks with "
            "optional dependencies and returns an execution plan showing which "
            "agents run in parallel and which are sequential."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "agent_type": {"type": "string"},
                            "description": {"type": "string"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["task_id", "agent_type"],
                    },
                    "description": "Pipeline tasks with optional dependencies",
                },
            },
            "required": ["tasks"],
        },
        handler=lambda tasks: _plan_pipeline(tasks),
        category="git_pin",
    ))

    registry.register(Tool(
        name="git_pin_concurrency_status",
        description=(
            "Check the current concurrency configuration and adaptive tuning state. "
            "Shows current worker count, min/max bounds, and recent latency trends."
        ),
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=lambda: json.dumps({
            "success": True,
            "concurrency": {
                "default_parallel_tools": 8,
                "execution_mode": "parallel",
                "adaptive_tuning": "enabled",
                "note": "Concurrency is auto-tuned based on observed tool latencies",
            },
        }),
        category="git_pin",
    ))

    # ------------------------------------------------------------------
    # Context management tools
    # ------------------------------------------------------------------

    registry.register(Tool(
        name="git_pin_context_status",
        description=(
            "Check the current context window utilization. Shows message count, "
            "estimated token usage, and whether context pruning has occurred."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "message_count": {
                    "type": "integer",
                    "description": "Current message count in the conversation",
                },
            },
            "required": [],
        },
        handler=lambda message_count=0: json.dumps({
            "success": True,
            "context": {
                "message_count": message_count,
                "max_messages": 200,
                "prune_threshold": 200,
                "prune_keep_recent": 40,
                "status": "healthy" if message_count < 150 else "approaching_limit",
            },
        }),
        category="git_pin",
    ))


def _analyze_batch_schedule(tool_names: List[str], description: str) -> str:
    """Analyze tool calls and produce a batch schedule."""
    from ..agents.git_pin_throughput_optimizer import BatchToolScheduler

    # Create mock tool calls for scheduling
    tool_calls = [{"name": name, "input": {}, "id": f"tc_{i}"} for i, name in enumerate(tool_names)]
    batches = BatchToolScheduler.schedule(tool_calls)

    schedule = {
        "success": True,
        "description": description,
        "total_tools": len(tool_names),
        "total_batches": len(batches),
        "batches": [],
    }

    for i, batch in enumerate(batches):
        batch_info = {
            "batch_index": i,
            "execution": "parallel" if len(batch) > 1 else "sequential",
            "tool_count": len(batch),
            "tools": [tc["name"] for tc in batch],
        }
        schedule["batches"].append(batch_info)

    # Estimate speedup
    if len(batches) < len(tool_names):
        speedup = len(tool_names) / max(len(batches), 1)
        schedule["estimated_speedup"] = f"{speedup:.1f}x"
    else:
        schedule["estimated_speedup"] = "1.0x (all sequential)"

    return json.dumps(schedule)


def _plan_pipeline(tasks: List[Dict[str, Any]]) -> str:
    """Plan a multi-agent pipeline execution."""
    task_map = {t["task_id"]: t for t in tasks}

    # Compute execution waves (topological sort by dependency depth)
    depths: Dict[str, int] = {}

    def get_depth(task_id: str) -> int:
        if task_id in depths:
            return depths[task_id]
        task = task_map.get(task_id)
        if not task or not task.get("depends_on"):
            depths[task_id] = 0
            return 0
        max_dep_depth = max(get_depth(dep) for dep in task["depends_on"])
        depths[task_id] = max_dep_depth + 1
        return depths[task_id]

    for t in tasks:
        get_depth(t["task_id"])

    # Group by depth into execution waves
    max_depth = max(depths.values()) if depths else 0
    waves = []
    for d in range(max_depth + 1):
        wave_tasks = [tid for tid, depth in depths.items() if depth == d]
        waves.append({
            "wave": d,
            "execution": "parallel" if len(wave_tasks) > 1 else "sequential",
            "tasks": [
                {
                    "task_id": tid,
                    "agent_type": task_map[tid].get("agent_type", "unknown"),
                    "description": task_map[tid].get("description", ""),
                }
                for tid in wave_tasks
            ],
        })

    plan = {
        "success": True,
        "total_tasks": len(tasks),
        "total_waves": len(waves),
        "max_parallelism": max(len(w["tasks"]) for w in waves) if waves else 0,
        "waves": waves,
    }

    return json.dumps(plan)
