#!/usr/bin/env python3
"""DSDM Agents - Main entry point."""

import argparse
import os
import sys

from dotenv import load_dotenv
from rich.console import Console

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
    BusinessStudyAgent,
    FunctionalModelAgent,
    DesignBuildAgent,
    ImplementationAgent,
)


def main():
    """Main entry point."""
    load_dotenv()

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console = Console()
        console.print("[red]Error: ANTHROPIC_API_KEY not set[/red]")
        console.print("Please set your API key in .env file or environment variable")
        sys.exit(1)

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
        help="Task or project description",
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

    args = parser.parse_args()

    # Create orchestrator with default config
    config = OrchestratorConfig(
        phases=[
            PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, AgentMode.HYBRID if args.mode == "automated" else AgentMode(args.mode)),
            PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, AgentMode.MANUAL if args.mode == "automated" else AgentMode(args.mode)),
        ],
        interactive=args.interactive or not args.input,
        auto_advance=False,
    )

    orchestrator = DSDMOrchestrator(config)

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

    # Default to interactive mode if no specific action
    orchestrator.interactive_menu()


if __name__ == "__main__":
    main()
