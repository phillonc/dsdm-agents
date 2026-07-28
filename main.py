#!/usr/bin/env python3
"""DSDM Agents - Main entry point."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import (
    DSDMOrchestrator,
    DSDMPhase,
    OrchestratorConfig,
    PhaseConfig,
)
from src.agents.base_agent import AgentMode
from src.agents import (
    FeasibilityAgent,
    ProductManagerAgent,
    BusinessStudyAgent,
    FunctionalModelAgent,
    DesignBuildAgent,
    ImplementationAgent,
)
from src.agents.devops_agent import DevOpsAgent
from src.rooms import (
    create_delivery_room,
    export_delivery_room,
    get_delivery_room_status,
    load_delivery_room,
)
from src.rooms.delivery_room import get_room_base_path
from src.rooms.room_dashboard import RoomDashboardFilters, build_room_dashboard_markdown
from src.orchestrator import pi_session_runner
from src.agents.role_definitions_check import check_role_definitions
from src.tools.dsdm_tools import create_dsdm_tool_registry


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="DSDM Agents - Dynamic Systems Development Method AI Agents"
    )
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument(
        "--phase",
        choices=["feasibility", "business_study", "functional_model", "design_build", "implementation", "devops"],
        help="Run a specific phase",
    )
    parser.add_argument("--mode", choices=["manual", "automated", "hybrid"], default="automated", help="Agent mode")
    parser.add_argument("--input", "-t", type=str, help="Task, project description, or delivery room mission")
    parser.add_argument("--workflow", action="store_true", help="Run the full DSDM workflow")
    parser.add_argument("--list-phases", action="store_true", help="List all phases and their status")
    parser.add_argument("--list-tools", action="store_true", help="List all available tools")
    parser.add_argument("--git-pin-pipeline", action="store_true", help="Run Git Pin high-throughput parallel pipeline")
    parser.add_argument("--max-concurrent", type=int, default=4, help="Max concurrent agents for Git Pin pipeline")

    parser.add_argument(
        "--agent-runtime",
        choices=["legacy", "pi"],
        default=None,
        help="Execution runtime for eligible phases (feasibility, business_study, functional_model, "
        "design_build, implementation, devops). Defaults to the AGENT_RUNTIME env var, or 'legacy'.",
    )
    parser.add_argument(
        "--llm-provider",
        choices=["anthropic", "openai", "gemini", "ollama", "vllm"],
        default=None,
        help="LLM provider to use. Defaults to the LLM_PROVIDER env var, or 'anthropic'. "
        "'vllm' targets a private/self-hosted vLLM endpoint and requires --agent-runtime pi.",
    )
    parser.add_argument(
        "--pi-doctor",
        action="store_true",
        help="Diagnose pi.dev agent runtime setup (pi CLI, extensions, vLLM config) and exit",
    )
    parser.add_argument(
        "--generate-agents",
        action="store_true",
        help="Check role_definitions.py for drift against ToolRegistry and .github/agents/*.agent.md, and exit",
    )

    parser.add_argument("--room-create", action="store_true", help="Create an Autonomous Delivery Room")
    parser.add_argument("--room-run", action="store_true", help="Create and run an Autonomous Delivery Room")
    parser.add_argument("--room-status", action="store_true", help="Show Autonomous Delivery Room status")
    parser.add_argument("--room-dashboard", action="store_true", help="Show a filtered Autonomous Delivery Room dashboard")
    parser.add_argument("--room-export", action="store_true", help="Export Autonomous Delivery Room dashboard to Markdown")
    parser.add_argument("--room-project", type=str, help="Project name for delivery room commands")
    parser.add_argument("--room-template", choices=["mvp", "platform", "migration", "enterprise", "compliance"], default="mvp")
    parser.add_argument("--room-overwrite", action="store_true", help="Overwrite an existing delivery room when creating")

    parser.add_argument("--dashboard-sections", type=str, help="Comma-separated sections: summary,health,agents,blockers,decisions,handoffs,artifacts,actions")
    parser.add_argument("--dashboard-agent", type=str, help="Filter dashboard by agent or role")
    parser.add_argument("--dashboard-phase", type=str, help="Filter dashboard by phase")
    parser.add_argument("--dashboard-status", type=str, help="Filter dashboard by status")
    parser.add_argument("--dashboard-severity", type=str, help="Filter blockers by severity")
    parser.add_argument("--dashboard-artifact-type", type=str, help="Filter artifacts by type")
    parser.add_argument("--dashboard-include-resolved", action="store_true", help="Include resolved blockers")
    parser.add_argument("--dashboard-output", type=str, help="Optional Markdown output path for filtered dashboard")
    return parser


def _requires_llm(args: argparse.Namespace) -> bool:
    """Return True when the selected command needs an LLM provider."""
    return not (
        args.pi_doctor
        or args.generate_agents
        or args.room_create
        or args.room_status
        or args.room_export
        or args.room_dashboard
    )


def _resolve_agent_runtime(args: argparse.Namespace) -> str:
    """Mirror DSDMOrchestrator's own --agent-runtime / AGENT_RUNTIME / default precedence."""
    resolved = (args.agent_runtime or os.environ.get("AGENT_RUNTIME") or "legacy").strip().lower()
    return resolved if resolved in ("legacy", "pi") else "legacy"


def _check_llm_provider(console: Console, agent_runtime: str) -> None:
    """Validate LLM provider configuration for agent commands."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    api_key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "ollama": None,
        "vllm": None,
    }
    if provider not in api_key_map:
        console.print(f"[red]Error: unknown LLM_PROVIDER '{provider}'[/red]")
        console.print("\nAvailable providers: anthropic, openai, gemini, ollama, vllm")
        sys.exit(1)

    if provider == "vllm":
        if agent_runtime != "pi":
            console.print("[red]Error: LLM_PROVIDER=vllm requires --agent-runtime pi (or AGENT_RUNTIME=pi)[/red]")
            console.print("The private vLLM provider is only wired up through the pi.dev agent runtime.")
            sys.exit(1)
        missing = [
            var for var in ("DSDM_VLLM_BASE_URL", "DSDM_VLLM_MODEL_ID") if not os.environ.get(var)
        ]
        if missing:
            console.print(f"[red]Error: missing required env var(s) for vllm: {', '.join(missing)}[/red]")
            console.print("Set DSDM_VLLM_BASE_URL (the private/VPC vLLM endpoint) and DSDM_VLLM_MODEL_ID "
                           "(the model the vLLM server was launched with) in your .env file.")
            sys.exit(1)
        return

    required_key = api_key_map.get(provider)
    if required_key and not os.environ.get(required_key):
        console.print(f"[red]Error: {required_key} not set[/red]")
        console.print(f"Please set your API key in .env file for provider: {provider}")
        console.print("\nAvailable providers: anthropic, openai, gemini, ollama, vllm")
        sys.exit(1)


def _run_pi_doctor(console: Console, agent_runtime: str) -> None:
    """Diagnose pi.dev agent runtime setup without running any agent."""
    console.print("[bold cyan]Pi Agent Runtime Doctor[/bold cyan]\n")

    table = Table(show_header=False)
    table.add_column("Check", style="cyan")
    table.add_column("Result")

    ok = True

    table.add_row("AGENT_RUNTIME", agent_runtime)

    pi_bin_ok = pi_session_runner.PI_BIN.exists()
    ok = ok and pi_bin_ok
    table.add_row(
        "pi CLI binary",
        f"[green]found[/green] ({pi_session_runner.PI_BIN})" if pi_bin_ok else f"[red]missing[/red] ({pi_session_runner.PI_BIN})",
    )

    for label, path in (
        ("dsdm-tools-bridge extension", pi_session_runner.TOOLS_BRIDGE_EXTENSION),
        ("dsdm-approval-gate extension", pi_session_runner.APPROVAL_GATE_EXTENSION),
    ):
        exists = path.exists()
        ok = ok and exists
        table.add_row(label, f"[green]found[/green] ({path})" if exists else f"[red]missing[/red] ({path})")

    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    resolved_provider = pi_session_runner._resolve_provider(provider)
    table.add_row("LLM_PROVIDER", f"{provider} -> pi provider '{resolved_provider}'")

    if provider == "vllm":
        import tempfile

        tmp_dir = Path(tempfile.mkdtemp(prefix="dsdm-pi-doctor-"))
        try:
            pi_session_runner._write_vllm_models_config(tmp_dir)
            table.add_row("vLLM models.json", "[green]valid[/green] (DSDM_VLLM_BASE_URL / DSDM_VLLM_MODEL_ID set)")
        except pi_session_runner.VllmConfigurationError as exc:
            ok = False
            table.add_row("vLLM models.json", f"[red]invalid[/red]: {exc}")
        finally:
            import shutil

            shutil.rmtree(tmp_dir, ignore_errors=True)

    console.print(table)
    if not ok:
        console.print("\n[red]One or more checks failed.[/red]")
        sys.exit(1)
    console.print("\n[green]All checks passed.[/green]")


def _run_generate_agents(console: Console) -> None:
    """Check role_definitions.py (the single source of truth for every DSDM role)
    for drift against ToolRegistry and .github/agents/*.agent.md.

    Does not overwrite .agent.md content: that file's prose is intentionally
    hand-authored, not generated from RoleDefinition — see
    src/agents/role_definitions_check.py and role_definitions.py's module
    docstring for why. This is a structural consistency check, the same one
    tests/test_role_definitions.py runs in CI, exposed here so an operator can
    run it without pytest after editing a role's tools or handoffs.
    """
    console.print("[bold cyan]Role Definitions Consistency Check[/bold cyan]\n")
    registry = create_dsdm_tool_registry(include_jira=True, include_confluence=True, include_devops=True)
    issues = check_role_definitions(registry)

    if not issues:
        console.print("[green]No drift found: every role's tools resolve, and every "
                       ".agent.md file matches its RoleDefinition.[/green]")
        return

    table = Table(title="Consistency Issues")
    table.add_column("Role", style="cyan")
    table.add_column("Problem", style="red")
    for issue in issues:
        table.add_row(issue.role_id, issue.problem)
    console.print(table)
    console.print(f"\n[red]{len(issues)} issue(s) found.[/red]")
    sys.exit(1)


def _dashboard_filters_from_args(args: argparse.Namespace) -> RoomDashboardFilters:
    sections = None
    if args.dashboard_sections:
        sections = [item.strip() for item in args.dashboard_sections.split(",")]
    return RoomDashboardFilters.from_values(
        sections=sections,
        agent=args.dashboard_agent,
        phase=args.dashboard_phase,
        status=args.dashboard_status,
        severity=args.dashboard_severity,
        artifact_type=args.dashboard_artifact_type,
        include_resolved=args.dashboard_include_resolved,
    )


def _print_room_status(console: Console, project_name: str) -> None:
    """Print a delivery room status summary."""
    status = get_delivery_room_status(project_name)
    room = load_delivery_room(project_name)
    health = status.get("health", {})

    console.print(f"\n[bold cyan]Delivery Room: {status['project_name']}[/bold cyan]")
    console.print(f"Mission: {status['mission']}")
    console.print(f"Template: {status['template']}")
    console.print(f"Status: {status['status']}")
    console.print(f"Active phase: {status['active_phase']}")
    if health:
        console.print(f"Health: {health.get('overall')}/100 ({health.get('status')}, confidence {health.get('confidence')}/100)")
    console.print(f"Open blockers: {status['open_blocker_count']}")
    console.print(f"Decisions: {status['decision_count']}")
    console.print(f"Handoffs: {status['handoff_count']}")

    table = Table(title="Assigned Agents")
    table.add_column("Role", style="cyan")
    table.add_column("Agent", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("Status", style="magenta")
    for agent in room.agents:
        table.add_row(agent.role, agent.agent_name, agent.phase, agent.status)
    console.print(table)

    if health.get("weak_points"):
        console.print("\n[bold]Weak points[/bold]")
        for item in health["weak_points"]:
            console.print(f"  • {item}")

    recommended_actions = health.get("recommended_actions") or status["next_actions"]
    if recommended_actions:
        console.print("\n[bold]Recommended actions[/bold]")
        for action in recommended_actions:
            console.print(f"  • {action}")


def _handle_room_commands(args: argparse.Namespace, console: Console) -> bool:
    """Handle local delivery room commands. Returns True when command was handled."""
    if args.room_create:
        if not args.input:
            console.print("[red]Error: --room-create requires --input mission text[/red]")
            sys.exit(1)
        room = create_delivery_room(args.input, args.room_project, args.room_template, args.room_overwrite)
        export_path = export_delivery_room(room.project_name)
        console.print(f"[green]Created delivery room:[/green] {room.project_name}")
        console.print(f"State: generated/{room.project_name}/room_state.json")
        console.print(f"Dashboard: {export_path}")
        _print_room_status(console, room.project_name)
        return True

    if args.room_status:
        if not args.room_project:
            console.print("[red]Error: --room-status requires --room-project[/red]")
            sys.exit(1)
        _print_room_status(console, args.room_project)
        return True

    if args.room_dashboard:
        if not args.room_project:
            console.print("[red]Error: --room-dashboard requires --room-project[/red]")
            sys.exit(1)
        markdown = build_room_dashboard_markdown(args.room_project, _dashboard_filters_from_args(args))
        if args.dashboard_output:
            path = Path(args.dashboard_output)
        else:
            path = get_room_base_path(args.room_project) / "docs" / "ROOM_DASHBOARD_FILTERED.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        console.print(Markdown(markdown))
        console.print(f"\n[green]Filtered dashboard written:[/green] {path}")
        return True

    if args.room_export:
        if not args.room_project:
            console.print("[red]Error: --room-export requires --room-project[/red]")
            sys.exit(1)
        export_path = export_delivery_room(args.room_project)
        console.print(f"[green]Exported delivery room dashboard:[/green] {export_path}")
        return True

    return False


def _create_orchestrator(args: argparse.Namespace, agent_runtime: str) -> DSDMOrchestrator:
    """Create the DSDM orchestrator. Delivery-room tools are registered natively."""
    config = OrchestratorConfig(
        phases=[
            PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.PRD_TRD, ProductManagerAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, AgentMode.MANUAL if args.mode == "automated" else AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.DEVOPS, DevOpsAgent, AgentMode.HYBRID if args.mode == "automated" else AgentMode(args.mode)),
        ],
        interactive=args.interactive or not args.input,
        auto_advance=False,
    )
    return DSDMOrchestrator(
        config,
        include_devops=True,
        include_jira=False,
        include_confluence=False,
        agent_runtime=agent_runtime,
    )


def main():
    """Main entry point."""
    load_dotenv()
    console = Console()
    parser = _build_parser()
    args = parser.parse_args()

    if args.llm_provider:
        os.environ["LLM_PROVIDER"] = args.llm_provider

    agent_runtime = _resolve_agent_runtime(args)

    if args.pi_doctor:
        _run_pi_doctor(console, agent_runtime)
        return
    if args.generate_agents:
        _run_generate_agents(console)
        return

    if _handle_room_commands(args, console):
        return
    if _requires_llm(args):
        _check_llm_provider(console, agent_runtime)

    orchestrator = _create_orchestrator(args, agent_runtime)
    try:
        if args.list_phases:
            orchestrator.list_phases()
            return
        if args.list_tools:
            orchestrator.list_tools()
            return
        if args.room_run:
            if not args.input:
                console.print("[red]Error: --room-run requires --input mission text[/red]")
                sys.exit(1)
            room = orchestrator.run_delivery_room(args.input, args.room_project, args.room_template, overwrite=args.room_overwrite)
            export_path = export_delivery_room(room.project_name)
            console.print(f"[green]Delivery room workflow finished:[/green] {room.project_name}")
            console.print(f"Dashboard: {export_path}")
            _print_room_status(console, room.project_name)
            return
        if args.interactive:
            orchestrator.interactive_menu()
            return
        if args.phase and args.input:
            orchestrator.run_phase(DSDMPhase(args.phase), args.input)
            return
        if args.workflow and args.input:
            orchestrator.run_workflow(args.input)
            return
        if args.git_pin_pipeline and args.input:
            orchestrator.run_git_pin_pipeline(args.input, max_concurrent=args.max_concurrent)
            return

        orchestrator.interactive_menu()
    finally:
        orchestrator.shutdown_pi_bridge()


if __name__ == "__main__":
    main()
