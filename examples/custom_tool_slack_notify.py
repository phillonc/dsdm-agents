#!/usr/bin/env python3
"""Custom tool example: notify a Slack channel when a DSDM phase completes.

Complements examples/custom_tools_example.py (which shows several small,
schema-only tools) by walking through ONE integration-shaped tool end to
end: registering it, wiring it into a phase's tool list, and calling it two
ways — directly via the registry (no LLM/API key required, good for CI or
a quick sanity check) and through an agent's normal tool-use loop (requires
ANTHROPIC_API_KEY or another configured provider).

Run directly, no API key needed:
    python examples/custom_tool_slack_notify.py

Run the agent-driven demo too (needs a configured LLM provider):
    python examples/custom_tool_slack_notify.py --with-agent
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib import error, request

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.tools.tool_registry import Tool, ToolRegistry
from src.tools.dsdm_tools import create_dsdm_tool_registry


def _post_to_slack(webhook_url: str, payload: dict) -> None:
    """POST a payload to a Slack incoming webhook. No third-party HTTP dependency."""
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Slack webhook returned HTTP {resp.status}")


def _notify_phase_complete_handler(project_slug: str, phase: str, summary: str, status: str = "success") -> str:
    """Handler for the notify_phase_complete tool.

    Reads SLACK_WEBHOOK_URL from the environment so credentials never pass
    through the LLM as a tool argument (same rule the MCP CLI tools follow —
    see .github/instructions/mcp.instructions.md).
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    emoji = {"success": ":white_check_mark:", "failed": ":x:", "blocked": ":warning:"}.get(status, ":information_source:")
    message = f"{emoji} *{project_slug}* — *{phase}* {status}\n{summary}"

    if not webhook_url:
        # Never block a phase on a missing integration — same convention
        # every DSDM tool follows for optional Jira/Confluence/MCP sync.
        return json.dumps({
            "success": True,
            "sent": False,
            "reason": "SLACK_WEBHOOK_URL not configured — skipped",
            "would_have_sent": message,
        })

    try:
        _post_to_slack(webhook_url, {"text": message})
    except (error.URLError, RuntimeError) as exc:
        return json.dumps({"success": False, "sent": False, "error": str(exc)})

    return json.dumps({
        "success": True,
        "sent": True,
        "project_slug": project_slug,
        "phase": phase,
        "status": status,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    })


NOTIFY_PHASE_COMPLETE_TOOL = Tool(
    name="notify_phase_complete",
    description=(
        "Post a message to the team's Slack channel announcing that a DSDM "
        "phase finished. Use this as the last step of any phase-completion "
        "hand-off, alongside (not instead of) the required file artefacts."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "project_slug": {"type": "string", "description": "The generated/<project-slug>/ this run belongs to"},
            "phase": {"type": "string", "description": "e.g. 'feasibility', 'design_build'"},
            "summary": {"type": "string", "description": "One or two sentence summary of the outcome"},
            "status": {
                "type": "string",
                "enum": ["success", "failed", "blocked"],
                "description": "Outcome of the phase",
            },
        },
        "required": ["project_slug", "phase", "summary"],
    },
    handler=_notify_phase_complete_handler,
    requires_approval=False,  # posting a status update is non-destructive; safe to automate
    category="devops",
)


def create_registry_with_slack_tool() -> ToolRegistry:
    """Default DSDM tool registry plus the Slack notification tool."""
    registry = create_dsdm_tool_registry()
    registry.register(NOTIFY_PHASE_COMPLETE_TOOL)
    return registry


def demo_direct_call(registry: ToolRegistry) -> None:
    """Call the tool directly through the registry — no LLM involved."""
    print("Calling notify_phase_complete via registry.execute() ...")
    result = registry.execute(
        "notify_phase_complete",
        project_slug="customer-feedback-portal",
        phase="feasibility",
        summary="GO at 87% confidence. 4 risks logged, all mitigated.",
        status="success",
    )
    print(json.dumps(json.loads(result), indent=2))


def demo_agent_driven(registry: ToolRegistry) -> None:
    """Let a real agent decide to call the tool as part of its normal run.

    Requires a configured LLM provider (ANTHROPIC_API_KEY by default).
    """
    from src.agents.feasibility_agent import FeasibilityAgent
    from src.agents.base_agent import AgentMode

    agent = FeasibilityAgent(tool_registry=registry, mode=AgentMode.AUTOMATED)
    agent.config.tools.append("notify_phase_complete")

    print(f"\nFeasibility Agent tools: {agent.config.tools}")
    print("\nRunning feasibility — the agent may call notify_phase_complete once it concludes...")

    result = agent.run(
        "Assess feasibility for 'customer-feedback-portal': a portal for "
        "collecting and triaging customer feedback with a weekly email "
        "digest. Project slug: customer-feedback-portal. After writing the "
        "report, post a Slack update via notify_phase_complete."
    )

    print(f"\nResult: {'Success' if result.success else 'Failed'}")
    slack_calls = [tc for tc in result.tool_calls if tc["tool"] == "notify_phase_complete"]
    print(f"notify_phase_complete calls made: {len(slack_calls)}")
    for tc in slack_calls:
        print(f"  -> {tc['result']}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-agent",
        action="store_true",
        help="Also run the agent-driven demo (requires a configured LLM provider)",
    )
    args = parser.parse_args()

    print("DSDM Agents - Custom Tool Example: Slack phase-complete notifications")
    print("=" * 72)

    registry = create_registry_with_slack_tool()
    print(f"\nRegistered tools: {len(registry.get_all())} (including notify_phase_complete)")

    demo_direct_call(registry)

    if args.with_agent:
        demo_agent_driven(registry)
    else:
        print("\n(Skipping agent-driven demo — pass --with-agent to run it against a real LLM)")


if __name__ == "__main__":
    main()
