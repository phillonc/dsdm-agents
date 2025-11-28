#!/usr/bin/env python3
"""Simple usage example for DSDM Agents."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.orchestrator.dsdm_orchestrator import DSDMOrchestrator, DSDMPhase
from src.agents.base_agent import AgentMode


def main():
    """Demonstrate basic DSDM agent usage."""
    load_dotenv()

    # Create orchestrator with default settings
    orchestrator = DSDMOrchestrator()

    # Example 1: Run a single phase
    print("\n" + "=" * 60)
    print("Example 1: Running Feasibility Study Phase")
    print("=" * 60)

    project_description = """
    We want to build a customer feedback management system that:
    - Collects feedback from multiple channels (email, web, mobile)
    - Analyzes sentiment using AI
    - Generates reports for management
    - Integrates with existing CRM system
    """

    result = orchestrator.run_phase(
        DSDMPhase.FEASIBILITY,
        project_description
    )

    print(f"\nFeasibility Result: {'Success' if result.success else 'Failed'}")
    print(f"Recommendation: {result.artifacts.get('recommendation', 'N/A')}")

    # Example 2: Configure agent modes
    print("\n" + "=" * 60)
    print("Example 2: Configuring Agent Modes")
    print("=" * 60)

    # Set Feasibility to automated (runs without approval)
    orchestrator.set_agent_mode(DSDMPhase.FEASIBILITY, AgentMode.AUTOMATED)
    print("Feasibility: AUTOMATED")

    # Set Business Study to hybrid (some tools need approval)
    orchestrator.set_agent_mode(DSDMPhase.BUSINESS_STUDY, AgentMode.HYBRID)
    print("Business Study: HYBRID")

    # Set Implementation to manual (all tools need approval)
    orchestrator.set_agent_mode(DSDMPhase.IMPLEMENTATION, AgentMode.MANUAL)
    print("Implementation: MANUAL")

    # Example 3: List all phases and tools
    print("\n" + "=" * 60)
    print("Example 3: List Phases and Tools")
    print("=" * 60)

    orchestrator.list_phases()
    orchestrator.list_tools(DSDMPhase.FEASIBILITY)


def programmatic_workflow_example():
    """Example of running a complete workflow programmatically."""
    load_dotenv()

    # Custom approval callback for hybrid/manual modes
    def my_approval_callback(tool_name: str, tool_input: dict) -> bool:
        """Custom approval logic."""
        # Auto-approve certain tools
        auto_approve = ["analyze_requirements", "identify_risks"]
        if tool_name in auto_approve:
            print(f"Auto-approving: {tool_name}")
            return True

        # For other tools, you could implement custom logic
        print(f"Tool requires approval: {tool_name}")
        print(f"Input: {tool_input}")

        # For demo, approve all
        return True

    # Create orchestrator
    orchestrator = DSDMOrchestrator()

    # Run specific phases in sequence
    phases_to_run = [
        DSDMPhase.FEASIBILITY,
        DSDMPhase.BUSINESS_STUDY,
    ]

    project = "Build an inventory management system for small retail businesses"

    for phase in phases_to_run:
        print(f"\n--- Running {phase.value} ---")
        result = orchestrator.run_phase(phase, project)

        if not result.success:
            print(f"Phase {phase.value} failed!")
            break

        if result.requires_next_phase:
            print(f"Phase completed, ready for next phase")
        else:
            print(f"Phase completed, manual intervention may be needed")


if __name__ == "__main__":
    print("DSDM Agents - Simple Usage Examples")
    print("=" * 60)

    main()

    print("\n\nRunning programmatic workflow example...")
    programmatic_workflow_example()
