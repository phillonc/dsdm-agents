"""Git Pin Throughput Optimizer - Pipeline parallelism and batch scheduling.

Provides higher-level throughput optimization strategies that sit above
the core agent loop:
- Pipeline parallelism: run multiple agents concurrently on different tasks
- Batch scheduling: group related tool calls for maximum parallelism
- Adaptive concurrency: tune parallel workers based on observed latency
- Throughput dashboard: aggregate metrics across agents
"""

import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_agent import AgentResult, BaseAgent, ProgressCallback, ProgressEvent
from .git_pin_agent_core import (
    GitPinBaseAgent,
    GitPinLoopConfig,
    ThroughputMetrics,
    ToolExecutionMode,
)


# ---------------------------------------------------------------------------
# Adaptive concurrency controller
# ---------------------------------------------------------------------------

@dataclass
class AdaptiveConcurrencyState:
    """Tracks latency to auto-tune concurrency levels."""
    current_workers: int = 4
    min_workers: int = 2
    max_workers: int = 16
    window_size: int = 10
    latencies_ms: List[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_latency(self, latency_ms: float) -> None:
        with self._lock:
            self.latencies_ms.append(latency_ms)
            if len(self.latencies_ms) > self.window_size:
                self.latencies_ms = self.latencies_ms[-self.window_size:]

    def maybe_adjust(self) -> int:
        """Adjust concurrency based on recent latency trends.

        If latencies are decreasing (system has headroom), increase workers.
        If latencies are increasing (system saturated), decrease workers.
        """
        with self._lock:
            if len(self.latencies_ms) < self.window_size:
                return self.current_workers

            mid = len(self.latencies_ms) // 2
            first_half_avg = sum(self.latencies_ms[:mid]) / mid
            second_half_avg = sum(self.latencies_ms[mid:]) / (len(self.latencies_ms) - mid)

            if second_half_avg < first_half_avg * 0.9:
                # Latency decreasing -> more headroom -> increase
                self.current_workers = min(self.current_workers + 1, self.max_workers)
            elif second_half_avg > first_half_avg * 1.2:
                # Latency increasing -> saturated -> decrease
                self.current_workers = max(self.current_workers - 1, self.min_workers)

            return self.current_workers


# ---------------------------------------------------------------------------
# Pipeline parallelism: run multiple agents concurrently
# ---------------------------------------------------------------------------

@dataclass
class PipelineTask:
    """A task in the agent pipeline."""
    agent: BaseAgent
    user_input: str
    context: Optional[Dict[str, Any]] = None
    depends_on: Optional[List[str]] = None
    task_id: str = ""


@dataclass
class PipelineResult:
    """Result from a pipeline execution."""
    task_id: str
    agent_name: str
    result: AgentResult
    elapsed_ms: float


class GitPinPipeline:
    """Execute multiple agents in parallel with dependency management.

    Agents with no dependencies run concurrently. Agents that depend
    on other tasks wait for their dependencies to complete.
    """

    def __init__(
        self,
        max_concurrent_agents: int = 4,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.max_concurrent = max_concurrent_agents
        self.progress_callback = progress_callback
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_agents)

    def _emit_progress(self, event, message, **kwargs):
        if self.progress_callback:
            from .base_agent import ProgressInfo
            self.progress_callback(ProgressInfo(
                event=event, message=message, **kwargs
            ))

    def execute(self, tasks: List[PipelineTask]) -> List[PipelineResult]:
        """Execute pipeline tasks respecting dependencies.

        Tasks without dependencies are submitted immediately.
        Tasks with dependencies wait for their predecessors.
        """
        results: Dict[str, PipelineResult] = {}
        futures: Dict[str, Future] = {}
        pending = list(tasks)

        self._emit_progress(
            ProgressEvent.STARTED,
            f"[GitPin Pipeline] Starting {len(tasks)} tasks",
        )

        while pending or futures:
            # Find tasks whose dependencies are satisfied
            ready = []
            still_pending = []

            for task in pending:
                if task.depends_on:
                    deps_met = all(dep in results for dep in task.depends_on)
                    if deps_met:
                        # Inject dependency results into context
                        dep_context = task.context or {}
                        for dep_id in task.depends_on:
                            dep_result = results[dep_id]
                            dep_context[f"{dep_id}_output"] = dep_result.result.output
                            dep_context[f"{dep_id}_artifacts"] = dep_result.result.artifacts
                        task.context = dep_context
                        ready.append(task)
                    else:
                        still_pending.append(task)
                else:
                    ready.append(task)

            pending = still_pending

            # Submit ready tasks
            for task in ready:
                if len(futures) >= self.max_concurrent:
                    break
                pending = [t for t in pending if t.task_id != task.task_id]

                self._emit_progress(
                    ProgressEvent.PROCESSING,
                    f"[GitPin Pipeline] Launching: {task.agent.name} ({task.task_id})",
                )

                future = self._executor.submit(
                    self._run_task, task
                )
                futures[task.task_id] = future

            # Wait for at least one future to complete
            if futures:
                completed_ids = []
                for task_id, future in futures.items():
                    if future.done():
                        try:
                            pipeline_result = future.result()
                            results[task_id] = pipeline_result
                            self._emit_progress(
                                ProgressEvent.TOOL_COMPLETED,
                                f"[GitPin Pipeline] Completed: {pipeline_result.agent_name} "
                                f"({pipeline_result.elapsed_ms:.0f}ms)",
                            )
                        except Exception as e:
                            results[task_id] = PipelineResult(
                                task_id=task_id,
                                agent_name="error",
                                result=AgentResult(success=False, output=str(e)),
                                elapsed_ms=0,
                            )
                        completed_ids.append(task_id)

                for cid in completed_ids:
                    del futures[cid]

                if not completed_ids and futures:
                    # No tasks completed yet, wait briefly
                    time.sleep(0.05)

            # Re-add tasks that were removed from pending for submission
            ready_not_submitted = [
                t for t in ready
                if t.task_id not in futures and t.task_id not in results
            ]
            pending.extend(ready_not_submitted)

        self._emit_progress(
            ProgressEvent.COMPLETED,
            f"[GitPin Pipeline] All {len(tasks)} tasks complete",
        )

        # Return in original task order
        return [results[t.task_id] for t in tasks if t.task_id in results]

    def _run_task(self, task: PipelineTask) -> PipelineResult:
        """Run a single pipeline task."""
        start = time.time()
        result = task.agent.run(task.user_input, task.context)
        elapsed = (time.time() - start) * 1000

        return PipelineResult(
            task_id=task.task_id,
            agent_name=task.agent.name,
            result=result,
            elapsed_ms=elapsed,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# Batch tool call scheduler
# ---------------------------------------------------------------------------

class BatchToolScheduler:
    """Groups related tool calls for optimal batch execution.

    Analyzes tool call patterns and reorders them to maximize
    parallelism while respecting data dependencies.
    """

    # Tools that can safely run in parallel (no shared state)
    PARALLELIZABLE_TOOLS = frozenset({
        "file_write", "file_read", "file_append", "file_copy",
        "directory_create", "directory_list",
        "generate_code", "write_file", "generate_code_scaffold",
        "run_linter", "check_code_quality", "review_code",
        "security_check", "analyze_dependencies",
        "create_documentation", "generate_docs",
    })

    # Tools that must run sequentially (modify shared state)
    SEQUENTIAL_TOOLS = frozenset({
        "project_init",  # Must complete before file writes
        "run_tests",     # Depends on written files
        "deploy_to_environment",
        "rollback_deployment",
    })

    @classmethod
    def schedule(
        cls, tool_calls: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Schedule tool calls into batches for optimal execution.

        Returns a list of batches. Each batch contains tool calls
        that can be executed in parallel. Batches are executed
        sequentially.
        """
        if not tool_calls:
            return []

        batches: List[List[Dict[str, Any]]] = []
        current_batch: List[Dict[str, Any]] = []

        for tc in tool_calls:
            tool_name = tc.get("name", "")

            if tool_name in cls.SEQUENTIAL_TOOLS:
                # Flush current parallel batch
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                # Sequential tool gets its own batch
                batches.append([tc])
            elif tool_name in cls.PARALLELIZABLE_TOOLS:
                current_batch.append(tc)
            else:
                # Unknown tool - add to current batch (parallel by default)
                current_batch.append(tc)

        # Flush remaining
        if current_batch:
            batches.append(current_batch)

        return batches


# ---------------------------------------------------------------------------
# Throughput Dashboard - aggregate metrics across agents
# ---------------------------------------------------------------------------

class ThroughputDashboard:
    """Aggregates throughput metrics from multiple Git pin agents."""

    def __init__(self):
        self._metrics: Dict[str, ThroughputMetrics] = {}
        self._pipeline_results: List[PipelineResult] = []
        self._lock = threading.Lock()

    def record_agent_metrics(self, agent_name: str, metrics: ThroughputMetrics) -> None:
        with self._lock:
            self._metrics[agent_name] = metrics

    def record_pipeline_results(self, results: List[PipelineResult]) -> None:
        with self._lock:
            self._pipeline_results.extend(results)

    def get_summary(self) -> Dict[str, Any]:
        """Generate aggregate throughput summary."""
        with self._lock:
            total_tools = sum(m.total_tool_calls for m in self._metrics.values())
            total_tool_time = sum(m.total_tool_execution_time_ms for m in self._metrics.values())
            total_llm_time = sum(m.total_llm_call_time_ms for m in self._metrics.values())
            total_turns = sum(m.total_turns for m in self._metrics.values())

            agent_summaries = {}
            for name, m in self._metrics.items():
                agent_summaries[name] = m.to_dict()

            pipeline_summary = []
            for pr in self._pipeline_results:
                pipeline_summary.append({
                    "task_id": pr.task_id,
                    "agent": pr.agent_name,
                    "success": pr.result.success,
                    "elapsed_ms": round(pr.elapsed_ms, 2),
                })

            return {
                "aggregate": {
                    "total_agents": len(self._metrics),
                    "total_tool_calls": total_tools,
                    "total_tool_time_ms": round(total_tool_time, 2),
                    "total_llm_time_ms": round(total_llm_time, 2),
                    "total_turns": total_turns,
                },
                "agents": agent_summaries,
                "pipeline": pipeline_summary,
            }

    def format_report(self) -> str:
        """Format a human-readable throughput report."""
        summary = self.get_summary()
        agg = summary["aggregate"]

        lines = [
            "## Git Pin Throughput Report",
            "",
            f"**Agents:** {agg['total_agents']}",
            f"**Total Tool Calls:** {agg['total_tool_calls']}",
            f"**Tool Execution Time:** {agg['total_tool_time_ms']:.0f}ms",
            f"**LLM Call Time:** {agg['total_llm_time_ms']:.0f}ms",
            f"**Total Turns:** {agg['total_turns']}",
            "",
        ]

        if summary["agents"]:
            lines.append("### Per-Agent Metrics")
            for name, metrics in summary["agents"].items():
                lines.append(f"\n**{name}:**")
                lines.append(f"  - Tool calls: {metrics['total_tool_calls']}")
                lines.append(f"  - Throughput: {metrics['throughput_tools_per_sec']:.1f} tools/sec")
                lines.append(f"  - Parallel batches: {metrics['parallel_batches']}")
                lines.append(f"  - Elapsed: {metrics['elapsed_ms']:.0f}ms")

        if summary["pipeline"]:
            lines.append("\n### Pipeline Tasks")
            for task in summary["pipeline"]:
                status = "OK" if task["success"] else "FAIL"
                lines.append(f"  - [{status}] {task['task_id']}: {task['agent']} ({task['elapsed_ms']:.0f}ms)")

        return "\n".join(lines)
