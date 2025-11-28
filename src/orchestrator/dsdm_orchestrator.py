"""DSDM Orchestrator - Manages agent selection and workflow."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..agents.base_agent import AgentMode, AgentResult, BaseAgent
from ..agents.feasibility_agent import FeasibilityAgent
from ..agents.business_study_agent import BusinessStudyAgent
from ..agents.functional_model_agent import FunctionalModelAgent
from ..agents.design_build_agent import DesignBuildAgent
from ..agents.implementation_agent import ImplementationAgent
from ..tools.tool_registry import ToolRegistry
from ..tools.dsdm_tools import create_dsdm_tool_registry


class DSDMPhase(Enum):
    """DSDM project phases."""
    FEASIBILITY = "feasibility"
    BUSINESS_STUDY = "business_study"
    FUNCTIONAL_MODEL = "functional_model"
    DESIGN_BUILD = "design_build"
    IMPLEMENTATION = "implementation"


@dataclass
class PhaseConfig:
    """Configuration for a DSDM phase."""
    phase: DSDMPhase
    agent_class: Type[BaseAgent]
    mode: AgentMode = AgentMode.AUTOMATED
    enabled: bool = True


@dataclass
class OrchestratorConfig:
    """Configuration for the DSDM orchestrator."""
    phases: List[PhaseConfig] = field(default_factory=list)
    interactive: bool = True
    auto_advance: bool = False  # Automatically advance to next phase if conditions met


class DSDMOrchestrator:
    """Orchestrates DSDM methodology agents."""

    PHASE_ORDER = [
        DSDMPhase.FEASIBILITY,
        DSDMPhase.BUSINESS_STUDY,
        DSDMPhase.FUNCTIONAL_MODEL,
        DSDMPhase.DESIGN_BUILD,
        DSDMPhase.IMPLEMENTATION,
    ]

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or self._default_config()
        self.tool_registry = create_dsdm_tool_registry()
        self.console = Console()
        self.agents: Dict[DSDMPhase, BaseAgent] = {}
        self.results: Dict[DSDMPhase, AgentResult] = {}
        self.current_phase: Optional[DSDMPhase] = None

        # Initialize agents
        self._initialize_agents()

    def _default_config(self) -> OrchestratorConfig:
        """Create default configuration."""
        return OrchestratorConfig(
            phases=[
                PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, AgentMode.HYBRID),
                PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, AgentMode.MANUAL),
            ],
            interactive=True,
            auto_advance=False,
        )

    def _initialize_agents(self) -> None:
        """Initialize all phase agents."""
        for phase_config in self.config.phases:
            if phase_config.enabled:
                agent = phase_config.agent_class(
                    tool_registry=self.tool_registry,
                    mode=phase_config.mode,
                    approval_callback=self._approval_callback if self.config.interactive else None,
                )
                self.agents[phase_config.phase] = agent

    def _approval_callback(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """Callback for tool approval in manual/hybrid modes."""
        self.console.print(f"\n[yellow]Tool approval required:[/yellow] {tool_name}")
        self.console.print(f"[dim]Input: {tool_input}[/dim]")
        return Confirm.ask("Approve this tool execution?")

    def get_agent(self, phase: DSDMPhase) -> Optional[BaseAgent]:
        """Get agent for a specific phase."""
        return self.agents.get(phase)

    def set_agent_mode(self, phase: DSDMPhase, mode: AgentMode) -> None:
        """Set the mode for a specific phase agent."""
        agent = self.agents.get(phase)
        if agent:
            agent.mode = mode

    def list_phases(self) -> None:
        """Display all phases and their configurations."""
        table = Table(title="DSDM Phases")
        table.add_column("Phase", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Mode", style="yellow")
        table.add_column("Status", style="magenta")

        for phase in self.PHASE_ORDER:
            agent = self.agents.get(phase)
            if agent:
                status = "✓ Enabled"
                if phase in self.results:
                    status = "✓ Completed" if self.results[phase].success else "✗ Failed"
                elif phase == self.current_phase:
                    status = "► Running"

                table.add_row(
                    phase.value.replace("_", " ").title(),
                    agent.name,
                    agent.mode.value,
                    status,
                )
            else:
                table.add_row(
                    phase.value.replace("_", " ").title(),
                    "-",
                    "-",
                    "✗ Disabled",
                )

        self.console.print(table)

    def list_tools(self, phase: Optional[DSDMPhase] = None) -> None:
        """Display tools available for a phase or all phases."""
        if phase:
            agent = self.agents.get(phase)
            if not agent:
                self.console.print(f"[red]Phase {phase.value} not found[/red]")
                return
            phases_to_show = [(phase, agent)]
        else:
            phases_to_show = [(p, a) for p, a in self.agents.items()]

        for phase, agent in phases_to_show:
            table = Table(title=f"Tools for {phase.value.replace('_', ' ').title()}")
            table.add_column("Tool", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Requires Approval", style="yellow")

            for tool in agent.get_tools():
                table.add_row(
                    tool.name,
                    tool.description[:50] + "..." if len(tool.description) > 50 else tool.description,
                    "Yes" if tool.requires_approval else "No",
                )

            self.console.print(table)
            self.console.print()

    def run_phase(
        self,
        phase: DSDMPhase,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Run a specific phase."""
        agent = self.agents.get(phase)
        if not agent:
            return AgentResult(
                success=False,
                output=f"Phase {phase.value} is not enabled",
            )

        self.current_phase = phase
        self.console.print(Panel(
            f"[bold cyan]Starting {phase.value.replace('_', ' ').title()} Phase[/bold cyan]\n"
            f"Agent: {agent.name}\n"
            f"Mode: {agent.mode.value}",
            title="DSDM Phase",
        ))

        # Combine previous phase output with context if available
        full_context = context or {}
        prev_phase_idx = self.PHASE_ORDER.index(phase) - 1
        if prev_phase_idx >= 0:
            prev_phase = self.PHASE_ORDER[prev_phase_idx]
            if prev_phase in self.results and self.results[prev_phase].next_phase_input:
                full_context.update(self.results[prev_phase].next_phase_input)

        result = agent.run(user_input, full_context if full_context else None)
        self.results[phase] = result
        self.current_phase = None

        # Display result
        status = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
        self.console.print(Panel(
            f"{status}\n\n{result.output[:500]}{'...' if len(result.output) > 500 else ''}",
            title=f"{phase.value.replace('_', ' ').title()} Result",
        ))

        return result

    def run_workflow(
        self,
        user_input: str,
        start_phase: Optional[DSDMPhase] = None,
        end_phase: Optional[DSDMPhase] = None,
    ) -> Dict[DSDMPhase, AgentResult]:
        """Run the complete DSDM workflow or a subset of phases."""
        start_idx = 0 if start_phase is None else self.PHASE_ORDER.index(start_phase)
        end_idx = len(self.PHASE_ORDER) if end_phase is None else self.PHASE_ORDER.index(end_phase) + 1

        phases_to_run = self.PHASE_ORDER[start_idx:end_idx]

        self.console.print(Panel(
            f"[bold]Starting DSDM Workflow[/bold]\n"
            f"Phases: {' → '.join(p.value.replace('_', ' ').title() for p in phases_to_run)}",
            title="DSDM Orchestrator",
        ))

        current_input = user_input

        for phase in phases_to_run:
            if phase not in self.agents:
                self.console.print(f"[yellow]Skipping disabled phase: {phase.value}[/yellow]")
                continue

            result = self.run_phase(phase, current_input)

            if not result.success:
                self.console.print(f"[red]Phase {phase.value} failed. Stopping workflow.[/red]")
                break

            if not result.requires_next_phase and not self.config.auto_advance:
                if self.config.interactive:
                    if not Confirm.ask(f"Continue to next phase?"):
                        break
                else:
                    break

        return self.results

    def interactive_menu(self) -> None:
        """Run an interactive menu for phase selection."""
        while True:
            self.console.print("\n[bold cyan]DSDM Agent Orchestrator[/bold cyan]\n")
            self.list_phases()

            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("1. Run specific phase")
            self.console.print("2. Run full workflow")
            self.console.print("3. Configure phase modes")
            self.console.print("4. View tools")
            self.console.print("5. Exit")

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                self._run_specific_phase_menu()
            elif choice == "2":
                self._run_workflow_menu()
            elif choice == "3":
                self._configure_modes_menu()
            elif choice == "4":
                self._view_tools_menu()
            elif choice == "5":
                break

    def _run_specific_phase_menu(self) -> None:
        """Menu for running a specific phase."""
        phase_names = [p.value for p in self.PHASE_ORDER if p in self.agents]
        self.console.print("\nAvailable phases:")
        for i, name in enumerate(phase_names, 1):
            self.console.print(f"  {i}. {name.replace('_', ' ').title()}")

        choice = Prompt.ask("Select phase", choices=[str(i) for i in range(1, len(phase_names) + 1)])
        phase = DSDMPhase(phase_names[int(choice) - 1])

        user_input = Prompt.ask("Enter your task/requirement")
        self.run_phase(phase, user_input)

    def _run_workflow_menu(self) -> None:
        """Menu for running the workflow."""
        user_input = Prompt.ask("Enter your project description/requirements")
        self.run_workflow(user_input)

    def _configure_modes_menu(self) -> None:
        """Menu for configuring agent modes."""
        for phase in self.PHASE_ORDER:
            if phase in self.agents:
                agent = self.agents[phase]
                self.console.print(f"\n{phase.value.replace('_', ' ').title()}: {agent.mode.value}")
                new_mode = Prompt.ask(
                    "Select mode",
                    choices=["manual", "automated", "hybrid", "skip"],
                    default=agent.mode.value,
                )
                if new_mode != "skip":
                    agent.mode = AgentMode(new_mode)

    def _view_tools_menu(self) -> None:
        """Menu for viewing tools."""
        phase_names = ["all"] + [p.value for p in self.PHASE_ORDER if p in self.agents]
        choice = Prompt.ask("Select phase (or 'all')", choices=phase_names, default="all")

        if choice == "all":
            self.list_tools()
        else:
            self.list_tools(DSDMPhase(choice))
