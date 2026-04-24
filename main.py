#!/usr/bin/env python3
"""DSDM Agents - Main entry point."""

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator.dsdm_orchestrator import (
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
from src.rooms import (
    create_delivery_room,
    export_delivery_room,
    get_delivery_room_status,
    load_delivery_room,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="DSDM Agents - Dynamic Systems Development Method AI Agents"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--phase",
        choices=["feasibility", "business_study", "functional_model", "design_build", "implementation"],
        help="Run a specific phase",
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "automated", "hybrid"],
        default="automated",
        help="Agent mode (default: automated)",
    )
    parser.add_argument(
        "--input", "-t",
        type=str,
        help="Task, project description, or delivery room mission",
    )
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run the full DSDM workflow",
    )
    parser.add_argument(
        "--list-phases",
        action="store_true",
        help="List all phases and their status",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List all available tools",
    )
    parser.add_argument(
        "--git-pin-pipeline",
        action="store_true",
        help="Run Git Pin high-throughput parallel pipeline",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=4,
        help="Max concurrent agents for Git Pin pipeline (default: 4)",
    )

    # Autonomous Delivery Room commands.
    parser.add_argument(
        "--room-create",
        action="store_true",
        help="Create an Autonomous Delivery Room. Use --input for mission.",
    )
    parser.add_argument(
        "--room-status",
        action="store_true",
        help="Show Autonomous Delivery Room status.",
    )
    parser.add_argument(
        "--room-export",
        action="store_true",
        help="Export Autonomous Delivery Room dashboard to Markdown.",
    )
    parser.add_argument(
        "--room-project",
        type=str,
        help="Project name for delivery room commands.",
    )
    parser.add_argument(
        "--room-template",
        choices=["mvp", "platform", "migration", "enterprise", "compliance"],
        default="mvp",
        help="Delivery room template (default: mvp).",
    )
    parser.add_argument(
        "--room-overwrite",
        action="store_true",
        help="Overwrite an existing delivery room when creating.",
    )
    return parser


def _requires_llm(args: argparse.Namespace) -> bool:
    """Return True when the selected command needs an LLM provider."""
    return not (args.room_create or args.room_status or args.room_export)


def _check_llm_provider(console: Console) -> None:
    """Validate LLM provider configuration for agent commands."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    api_key_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "ollama": None,  # Ollama doesn't require API key
    }

    required_key = api_key_map.get(provider)
    if required_key and not os.environ.get(required_key):
        console.print(f"[red]Error: {required_key} not set[/red]")
        console.print(f"Please set your API key in .env file for provider: {provider}")
        console.print("\nAvailable providers: anthropic, openai, gemini, ollama")
        sys.exit(1)


def _print_room_status(console: Console, project_name: str) -> None:
    """Print a delivery room status summary."""
    status = get_delivery_room_status(project_name)
    room = load_delivery_room(project_name)

    console.print(f"\n[bold cyan]Delivery Room: {status['project_name']}[/bold cyan]")
    console.print(f"Mission: {status['mission']}")
    console.print(f"Template: {status['template']}")
    console.print(f"Status: {status['status']}")
    console.print(f"Active phase: {status['active_phase']}")
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

    if status["next_actions"]:
        console.print("\n[bold]Next actions[/bold]")
        for action in status["next_actions"]:
            console.print(f"  • {action}")


def _handle_room_commands(args: argparse.Namespace, console: Console) -> bool:
    """Handle delivery room commands. Returns True when command was handled."""
    if args.room_create:
        if not args.input:
            console.print("[red]Error: --room-create requires --input mission text[/red]")
            sys.exit(1)
        room = create_delivery_room(
            mission=args.input,
            project_name=args.room_project,
            template=args.room_template,
            overwrite=args.room_overwrite,
        )
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

    if args.room_export:
        if not args.room_project:
            console.print("[red]Error: --room-export requires --room-project[/red]")
            sys.exit(1)
        export_path = export_delivery_room(args.room_project)
        console.print(f"[green]Exported delivery room dashboard:[/green] {export_path}")
        return True

    return False


def main():
    """Main entry point."""
    load_dotenv()
    console = Console()
    parser = _build_parser()
    args = parser.parse_args()

    if _handle_room_commands(args, console):
        return

    if _requires_llm(args):
        _check_llm_provider(console)

    # Create orchestrator with default config
    config = OrchestratorConfig(
        phases=[
            PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.PRD_TRD, ProductManagerAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, AgentMode.MANUAL if args.mode == "automated" else AgentMode(args.mode)),
        ],
        interactive=args.interactive or not args.input,
        auto_advance=False,
    )

    orchestrator = DSDMOrchestrator(
        config,
        include_devops=False,  # Disable to reduce prompt size
        include_jira=False,    # Disable to reduce prompt size
        include_confluence=False,  # Disable to reduce prompt size
    )

    # Handle commands
    if args.list_phases:
        orchestrator.list_phases()
        return

    if args.list_tools:
        orchestrator.list_tools()
        return

    if args.interactive:
        orchestrator.interactive_menu()
        return

    if args.phase and args.input:
        phase = DSDMPhase(args.phase)
        orchestrator.run_phase(phase, args.input)
        return

    if args.workflow and args.input:
        orchestrator.run_workflow(args.input)
        return

    if args.git_pin_pipeline and args.input:
        orchestrator.run_git_pin_pipeline(
            args.input,
            max_concurrent=args.max_concurrent,
        )
        return

    # Default to interactive mode if no specific action
    orchestrator.interactive_menu()


if __name__ == "__main__":
    main()
