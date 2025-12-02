"""DSDM Orchestrator - Manages agent selection and workflow."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.markdown import Markdown

from ..agents.base_agent import AgentMode, AgentResult, BaseAgent
from ..agents.workflow_modes import WorkflowMode
from ..utils.output_formatter import OutputFormatter, get_formatter
from ..agents.feasibility_agent import FeasibilityAgent
from ..agents.business_study_agent import BusinessStudyAgent
from ..agents.functional_model_agent import FunctionalModelAgent
from ..agents.design_build_agent import DesignBuildAgent
from ..agents.implementation_agent import ImplementationAgent
from ..agents.devops_agent import DevOpsAgent

# Design & Build specialized agents
from ..agents.dev_lead_agent import DevLeadAgent
from ..agents.frontend_developer_agent import FrontendDeveloperAgent
from ..agents.backend_developer_agent import BackendDeveloperAgent
from ..agents.automation_tester_agent import AutomationTesterAgent
from ..agents.nfr_tester_agent import NFRTesterAgent
from ..agents.pen_tester_agent import PenTesterAgent

from ..tools.tool_registry import ToolRegistry
from ..tools.dsdm_tools import create_dsdm_tool_registry


class DSDMPhase(Enum):
    """DSDM project phases."""
    FEASIBILITY = "feasibility"
    BUSINESS_STUDY = "business_study"
    FUNCTIONAL_MODEL = "functional_model"
    DESIGN_BUILD = "design_build"
    IMPLEMENTATION = "implementation"
    DEVOPS = "devops"  # Cross-cutting DevOps support based on development principles


class DesignBuildRole(Enum):
    """Specialized roles within Design & Build phase."""
    DEV_LEAD = "dev_lead"
    FRONTEND_DEV = "frontend_developer"
    BACKEND_DEV = "backend_developer"
    AUTOMATION_TESTER = "automation_tester"
    NFR_TESTER = "nfr_tester"
    PEN_TESTER = "pen_tester"


@dataclass
class PhaseConfig:
    """Configuration for a DSDM phase."""
    phase: DSDMPhase
    agent_class: Type[BaseAgent]
    mode: AgentMode = AgentMode.AUTOMATED
    workflow_mode: WorkflowMode = WorkflowMode.AGENT_WRITES_CODE
    enabled: bool = True


@dataclass
class RoleConfig:
    """Configuration for a specialized role within Design & Build."""
    role: DesignBuildRole
    agent_class: Type[BaseAgent]
    mode: AgentMode = AgentMode.AUTOMATED
    workflow_mode: WorkflowMode = WorkflowMode.AGENT_WRITES_CODE
    enabled: bool = True


@dataclass
class OrchestratorConfig:
    """Configuration for the DSDM orchestrator."""
    phases: List[PhaseConfig] = field(default_factory=list)
    design_build_roles: List[RoleConfig] = field(default_factory=list)
    interactive: bool = True
    auto_advance: bool = False  # Automatically advance to next phase if conditions met
    default_workflow_mode: WorkflowMode = WorkflowMode.AGENT_WRITES_CODE


class DSDMOrchestrator:
    """Orchestrates DSDM methodology agents."""

    PHASE_ORDER = [
        DSDMPhase.FEASIBILITY,
        DSDMPhase.BUSINESS_STUDY,
        DSDMPhase.FUNCTIONAL_MODEL,
        DSDMPhase.DESIGN_BUILD,
        DSDMPhase.IMPLEMENTATION,
    ]

    DESIGN_BUILD_ROLE_ORDER = [
        DesignBuildRole.DEV_LEAD,
        DesignBuildRole.FRONTEND_DEV,
        DesignBuildRole.BACKEND_DEV,
        DesignBuildRole.AUTOMATION_TESTER,
        DesignBuildRole.NFR_TESTER,
        DesignBuildRole.PEN_TESTER,
    ]

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        include_devops: bool = True,
        include_confluence: bool = False,
        include_jira: bool = False,
        show_progress: bool = True,
    ):
        self.config = config or self._default_config()
        self.show_progress = show_progress
        self.tool_registry = create_dsdm_tool_registry(
            include_confluence=include_confluence,
            include_jira=include_jira,
            include_devops=include_devops,
        )
        self.console = Console()
        self.formatter = get_formatter(self.console)
        self.agents: Dict[DSDMPhase, BaseAgent] = {}
        self.design_build_agents: Dict[DesignBuildRole, BaseAgent] = {}
        self.results: Dict[DSDMPhase, AgentResult] = {}
        self.role_results: Dict[DesignBuildRole, AgentResult] = {}
        self.current_phase: Optional[DSDMPhase] = None
        self.current_role: Optional[DesignBuildRole] = None

        # Create progress callback if enabled
        self._progress_callback = self.formatter.create_progress_callback() if show_progress else None

        # Initialize agents
        self._initialize_agents()
        self._initialize_design_build_agents()

    def _default_config(self) -> OrchestratorConfig:
        """Create default configuration."""
        return OrchestratorConfig(
            phases=[
                PhaseConfig(DSDMPhase.FEASIBILITY, FeasibilityAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.BUSINESS_STUDY, BusinessStudyAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.FUNCTIONAL_MODEL, FunctionalModelAgent, AgentMode.AUTOMATED),
                PhaseConfig(DSDMPhase.DESIGN_BUILD, DesignBuildAgent, AgentMode.HYBRID),
                PhaseConfig(DSDMPhase.IMPLEMENTATION, ImplementationAgent, AgentMode.MANUAL),
                PhaseConfig(DSDMPhase.DEVOPS, DevOpsAgent, AgentMode.HYBRID),
            ],
            design_build_roles=[
                RoleConfig(DesignBuildRole.DEV_LEAD, DevLeadAgent, AgentMode.HYBRID),
                RoleConfig(DesignBuildRole.FRONTEND_DEV, FrontendDeveloperAgent, AgentMode.AUTOMATED),
                RoleConfig(DesignBuildRole.BACKEND_DEV, BackendDeveloperAgent, AgentMode.AUTOMATED),
                RoleConfig(DesignBuildRole.AUTOMATION_TESTER, AutomationTesterAgent, AgentMode.AUTOMATED),
                RoleConfig(DesignBuildRole.NFR_TESTER, NFRTesterAgent, AgentMode.HYBRID),
                RoleConfig(DesignBuildRole.PEN_TESTER, PenTesterAgent, AgentMode.MANUAL),
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
                    progress_callback=self._progress_callback,
                )
                self.agents[phase_config.phase] = agent

    def _initialize_design_build_agents(self) -> None:
        """Initialize specialized Design & Build agents."""
        for role_config in self.config.design_build_roles:
            if role_config.enabled:
                agent = role_config.agent_class(
                    tool_registry=self.tool_registry,
                    mode=role_config.mode,
                    approval_callback=self._approval_callback if self.config.interactive else None,
                    progress_callback=self._progress_callback,
                )
                self.design_build_agents[role_config.role] = agent

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

    def get_design_build_agent(self, role: DesignBuildRole) -> Optional[BaseAgent]:
        """Get a specialized Design & Build agent by role."""
        return self.design_build_agents.get(role)

    def set_role_mode(self, role: DesignBuildRole, mode: AgentMode) -> None:
        """Set the mode for a specialized Design & Build agent."""
        agent = self.design_build_agents.get(role)
        if agent:
            agent.mode = mode

    def set_workflow_mode(self, phase: DSDMPhase, workflow_mode: WorkflowMode) -> None:
        """Set the workflow mode for a specific phase agent."""
        agent = self.agents.get(phase)
        if agent:
            agent.workflow_mode = workflow_mode

    def set_role_workflow_mode(self, role: DesignBuildRole, workflow_mode: WorkflowMode) -> None:
        """Set the workflow mode for a specialized Design & Build agent."""
        agent = self.design_build_agents.get(role)
        if agent:
            agent.workflow_mode = workflow_mode

    def set_all_workflow_modes(self, workflow_mode: WorkflowMode) -> None:
        """Set the workflow mode for all agents."""
        for agent in self.agents.values():
            agent.workflow_mode = workflow_mode

    def set_progress_enabled(self, enabled: bool) -> None:
        """Enable or disable progress reporting for all agents."""
        self.show_progress = enabled
        if enabled:
            self._progress_callback = self.formatter.create_progress_callback()
        else:
            self._progress_callback = None

        # Update all agents
        for agent in self.agents.values():
            agent.set_progress_callback(self._progress_callback)
        for agent in self.design_build_agents.values():
            agent.set_progress_callback(self._progress_callback)

    def list_phases(self) -> None:
        """Display all phases and their configurations."""
        table = Table(title="DSDM Phases")
        table.add_column("Phase", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Mode", style="yellow")
        table.add_column("Workflow", style="blue")
        table.add_column("Status", style="magenta")

        workflow_labels = {
            WorkflowMode.AGENT_WRITES_CODE: "Write",
            WorkflowMode.AGENT_PROVIDES_TIPS: "Tips",
            WorkflowMode.MANUAL_WITH_TIPS: "Manual",
        }

        for phase in self.PHASE_ORDER:
            agent = self.agents.get(phase)
            if agent:
                status = "[+] Enabled"
                if phase in self.results:
                    status = "[+] Completed" if self.results[phase].success else "[x] Failed"
                elif phase == self.current_phase:
                    status = "[>] Running"

                workflow_display = workflow_labels.get(agent.workflow_mode, agent.workflow_mode.value)

                table.add_row(
                    phase.value.replace("_", " ").title(),
                    agent.name,
                    agent.mode.value,
                    workflow_display,
                    status,
                )
            else:
                table.add_row(
                    phase.value.replace("_", " ").title(),
                    "-",
                    "-",
                    "-",
                    "[x] Disabled",
                )

        self.console.print(table)

    def list_design_build_roles(self) -> None:
        """Display all Design & Build specialized roles."""
        table = Table(title="Design & Build Specialized Roles")
        table.add_column("Role", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Mode", style="yellow")
        table.add_column("Workflow", style="blue")
        table.add_column("Status", style="magenta")

        workflow_labels = {
            WorkflowMode.AGENT_WRITES_CODE: "Write",
            WorkflowMode.AGENT_PROVIDES_TIPS: "Tips",
            WorkflowMode.MANUAL_WITH_TIPS: "Manual",
        }

        for role in self.DESIGN_BUILD_ROLE_ORDER:
            agent = self.design_build_agents.get(role)
            if agent:
                status = "[+] Enabled"
                if role in self.role_results:
                    status = "[+] Completed" if self.role_results[role].success else "[x] Failed"
                elif role == self.current_role:
                    status = "[>] Running"

                workflow_display = workflow_labels.get(agent.workflow_mode, agent.workflow_mode.value)

                table.add_row(
                    role.value.replace("_", " ").title(),
                    agent.name,
                    agent.mode.value,
                    workflow_display,
                    status,
                )
            else:
                table.add_row(
                    role.value.replace("_", " ").title(),
                    "-",
                    "-",
                    "-",
                    "[x] Disabled",
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
            self.formatter.format_error(
                f"Phase {phase.value} is not enabled",
                "Enable this phase in the orchestrator configuration."
            )
            return AgentResult(
                success=False,
                output=f"Phase {phase.value} is not enabled",
            )

        self.current_phase = phase
        phase_title = phase.value.replace('_', ' ').title()

        # Display start banner
        self.formatter.format_agent_start(
            agent_name=agent.name,
            phase_or_role=f"{phase_title} Phase",
            mode=agent.mode.value,
            description=agent.config.description if hasattr(agent, 'config') else None,
        )

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

        # Display formatted result
        self.formatter.format_agent_result(
            phase_or_role=phase_title,
            success=result.success,
            output=result.output,
            artifacts=result.artifacts if result.artifacts else None,
            tool_calls=agent.tool_call_history if hasattr(agent, 'tool_call_history') else None,
        )

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
        phase_names = [p.value.replace('_', ' ').title() for p in phases_to_run]

        # Display workflow start banner
        self.formatter.format_workflow_start(
            phases=phase_names,
            description=f"Processing: {user_input[:100]}..." if len(user_input) > 100 else f"Processing: {user_input}",
        )

        current_input = user_input

        for i, phase in enumerate(phases_to_run):
            if phase not in self.agents:
                self.formatter.format_warning(f"Skipping disabled phase: {phase.value}")
                continue

            self.formatter.format_progress(i + 1, len(phases_to_run), f"Running {phase.value.replace('_', ' ').title()}")
            result = self.run_phase(phase, current_input)

            if not result.success:
                self.formatter.format_error(
                    f"Phase {phase.value} failed",
                    "Workflow stopped due to phase failure."
                )
                break

            if not result.requires_next_phase and not self.config.auto_advance:
                if self.config.interactive:
                    if not Confirm.ask(f"Continue to next phase?"):
                        break
                else:
                    break

        # Display workflow summary
        self.formatter.format_workflow_summary(
            {phase.value: result for phase, result in self.results.items()}
        )

        return self.results

    def run_design_build_role(
        self,
        role: DesignBuildRole,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Run a specialized Design & Build role."""
        agent = self.design_build_agents.get(role)
        if not agent:
            self.formatter.format_error(
                f"Role {role.value} is not enabled",
                "Enable this role in the orchestrator configuration."
            )
            return AgentResult(
                success=False,
                output=f"Role {role.value} is not enabled",
            )

        self.current_role = role
        role_title = role.value.replace('_', ' ').title()

        # Display start banner
        self.formatter.format_agent_start(
            agent_name=agent.name,
            phase_or_role=role_title,
            mode=agent.mode.value,
            description=agent.config.description if hasattr(agent, 'config') else None,
        )

        result = agent.run(user_input, context)
        self.role_results[role] = result
        self.current_role = None

        # Display formatted result
        self.formatter.format_agent_result(
            phase_or_role=role_title,
            success=result.success,
            output=result.output,
            artifacts=result.artifacts if result.artifacts else None,
            tool_calls=agent.tool_call_history if hasattr(agent, 'tool_call_history') else None,
        )

        return result

    def run_design_build_team(
        self,
        user_input: str,
        roles: Optional[List[DesignBuildRole]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[DesignBuildRole, AgentResult]:
        """Run multiple Design & Build roles in sequence."""
        roles_to_run = roles or self.DESIGN_BUILD_ROLE_ORDER
        role_names = [r.value.replace('_', ' ').title() for r in roles_to_run if r in self.design_build_agents]

        # Display team start banner
        self.formatter.format_team_start(
            team_name="Design & Build Team",
            roles=role_names,
        )

        accumulated_context = context or {}

        for i, role in enumerate(roles_to_run):
            if role not in self.design_build_agents:
                self.formatter.format_warning(f"Skipping disabled role: {role.value}")
                continue

            self.formatter.format_progress(i + 1, len(roles_to_run), f"Running {role.value.replace('_', ' ').title()}")
            result = self.run_design_build_role(role, user_input, accumulated_context)

            # Accumulate results for next role
            if result.artifacts:
                accumulated_context[f"{role.value}_artifacts"] = result.artifacts

            if not result.success:
                self.formatter.format_error(f"Role {role.value} failed")
                if self.config.interactive:
                    if not Confirm.ask("Continue with remaining roles?"):
                        break

        # Display team summary
        self.formatter.format_workflow_summary(
            {role.value: result for role, result in self.role_results.items()}
        )

        return self.role_results

    def interactive_menu(self) -> None:
        """Run an interactive menu for phase selection."""
        while True:
            self.console.print("\n[bold cyan]DSDM Agent Orchestrator[/bold cyan]\n")
            self.list_phases()

            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("1. Run specific phase")
            self.console.print("2. Run full workflow")
            self.console.print("3. Design & Build team")
            self.console.print("4. Configure modes")
            self.console.print("5. Configure workflow modes")
            self.console.print("6. View tools")
            self.console.print("7. Exit")

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6", "7"])

            if choice == "1":
                self._run_specific_phase_menu()
            elif choice == "2":
                self._run_workflow_menu()
            elif choice == "3":
                self._design_build_menu()
            elif choice == "4":
                self._configure_modes_menu()
            elif choice == "5":
                self._configure_workflow_modes_menu()
            elif choice == "6":
                self._view_tools_menu()
            elif choice == "7":
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

    def _design_build_menu(self) -> None:
        """Menu for Design & Build specialized roles."""
        while True:
            self.console.print("\n[bold cyan]Design & Build Team[/bold cyan]\n")
            self.list_design_build_roles()

            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("1. Run specific role")
            self.console.print("2. Run full team")
            self.console.print("3. Configure role modes")
            self.console.print("4. View role tools")
            self.console.print("5. Back to main menu")

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"])

            if choice == "1":
                self._run_specific_role_menu()
            elif choice == "2":
                self._run_full_team_menu()
            elif choice == "3":
                self._configure_role_modes_menu()
            elif choice == "4":
                self._view_role_tools_menu()
            elif choice == "5":
                break

    def _run_specific_role_menu(self) -> None:
        """Menu for running a specific Design & Build role."""
        role_names = [r.value for r in self.DESIGN_BUILD_ROLE_ORDER if r in self.design_build_agents]
        self.console.print("\nAvailable roles:")
        for i, name in enumerate(role_names, 1):
            self.console.print(f"  {i}. {name.replace('_', ' ').title()}")

        choice = Prompt.ask("Select role", choices=[str(i) for i in range(1, len(role_names) + 1)])
        role = DesignBuildRole(role_names[int(choice) - 1])

        user_input = Prompt.ask("Enter your task/requirement")
        self.run_design_build_role(role, user_input)

    def _run_full_team_menu(self) -> None:
        """Menu for running the full Design & Build team."""
        user_input = Prompt.ask("Enter your development task/requirement")
        self.run_design_build_team(user_input)

    def _configure_role_modes_menu(self) -> None:
        """Menu for configuring Design & Build role modes."""
        for role in self.DESIGN_BUILD_ROLE_ORDER:
            if role in self.design_build_agents:
                agent = self.design_build_agents[role]
                self.console.print(f"\n{role.value.replace('_', ' ').title()}: {agent.mode.value}")
                new_mode = Prompt.ask(
                    "Select mode",
                    choices=["manual", "automated", "hybrid", "skip"],
                    default=agent.mode.value,
                )
                if new_mode != "skip":
                    agent.mode = AgentMode(new_mode)

    def _view_role_tools_menu(self) -> None:
        """Menu for viewing Design & Build role tools."""
        role_names = ["all"] + [r.value for r in self.DESIGN_BUILD_ROLE_ORDER if r in self.design_build_agents]
        choice = Prompt.ask("Select role (or 'all')", choices=role_names, default="all")

        if choice == "all":
            for role, agent in self.design_build_agents.items():
                table = Table(title=f"Tools for {role.value.replace('_', ' ').title()}")
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
        else:
            role = DesignBuildRole(choice)
            agent = self.design_build_agents.get(role)
            if agent:
                table = Table(title=f"Tools for {role.value.replace('_', ' ').title()}")
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

    def _configure_modes_menu(self) -> None:
        """Menu for configuring agent modes."""
        self.console.print("\n[bold]Configure Phase Modes:[/bold]")
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

        if Confirm.ask("\nConfigure Design & Build role modes?"):
            self._configure_role_modes_menu()

    def _view_tools_menu(self) -> None:
        """Menu for viewing tools."""
        phase_names = ["all"] + [p.value for p in self.PHASE_ORDER if p in self.agents]
        choice = Prompt.ask("Select phase (or 'all')", choices=phase_names, default="all")

        if choice == "all":
            self.list_tools()
        else:
            self.list_tools(DSDMPhase(choice))

    def _configure_workflow_modes_menu(self) -> None:
        """Menu for configuring workflow modes."""
        self.console.print("\n[bold cyan]Configure Workflow Modes[/bold cyan]")
        self.console.print("\n[bold]Workflow Mode Options:[/bold]")
        self.console.print("  [green]agent_writes_code[/green] - Agent autonomously writes code using tools")
        self.console.print("  [yellow]agent_provides_tips[/yellow] - Agent provides guidance/tips without writing code")
        self.console.print("  [blue]manual_with_tips[/blue] - Developer writes code manually, agent advises")

        # Ask for scope
        self.console.print("\n[bold]Configure for:[/bold]")
        self.console.print("1. All agents")
        self.console.print("2. Specific phase")
        self.console.print("3. Design & Build roles")
        self.console.print("4. Back")

        choice = Prompt.ask("Select option", choices=["1", "2", "3", "4"])

        if choice == "1":
            # Set for all agents
            new_mode = Prompt.ask(
                "Select workflow mode for all agents",
                choices=["agent_writes_code", "agent_provides_tips", "manual_with_tips"],
                default="agent_writes_code",
            )
            self.set_all_workflow_modes(WorkflowMode(new_mode))
            self.console.print(f"\n[green][+] All agents set to: {new_mode}[/green]")

        elif choice == "2":
            # Set for specific phase
            phase_names = [p.value for p in self.PHASE_ORDER if p in self.agents]
            self.console.print("\nAvailable phases:")
            for i, name in enumerate(phase_names, 1):
                agent = self.agents[DSDMPhase(name)]
                self.console.print(f"  {i}. {name.replace('_', ' ').title()} (current: {agent.workflow_mode.value})")

            phase_choice = Prompt.ask("Select phase", choices=[str(i) for i in range(1, len(phase_names) + 1)])
            phase = DSDMPhase(phase_names[int(phase_choice) - 1])

            new_mode = Prompt.ask(
                "Select workflow mode",
                choices=["agent_writes_code", "agent_provides_tips", "manual_with_tips"],
                default=self.agents[phase].workflow_mode.value,
            )
            self.set_workflow_mode(phase, WorkflowMode(new_mode))
            self.console.print(f"\n[green][+] {phase.value} set to: {new_mode}[/green]")

        elif choice == "3":
            # Set for Design & Build roles
            self._configure_role_workflow_modes_menu()

    def _configure_role_workflow_modes_menu(self) -> None:
        """Menu for configuring Design & Build role workflow modes."""
        self.console.print("\n[bold cyan]Configure Design & Build Workflow Modes[/bold cyan]")

        # Ask if setting all or individual
        set_all = Confirm.ask("Set workflow mode for all roles at once?")

        if set_all:
            new_mode = Prompt.ask(
                "Select workflow mode for all Design & Build roles",
                choices=["agent_writes_code", "agent_provides_tips", "manual_with_tips"],
                default="agent_writes_code",
            )
            for role in self.DESIGN_BUILD_ROLE_ORDER:
                if role in self.design_build_agents:
                    self.set_role_workflow_mode(role, WorkflowMode(new_mode))
            self.console.print(f"\n[green][+] All Design & Build roles set to: {new_mode}[/green]")
        else:
            for role in self.DESIGN_BUILD_ROLE_ORDER:
                if role in self.design_build_agents:
                    agent = self.design_build_agents[role]
                    self.console.print(f"\n{role.value.replace('_', ' ').title()}: {agent.workflow_mode.value}")
                    new_mode = Prompt.ask(
                        "Select workflow mode",
                        choices=["agent_writes_code", "agent_provides_tips", "manual_with_tips", "skip"],
                        default=agent.workflow_mode.value,
                    )
                    if new_mode != "skip":
                        self.set_role_workflow_mode(role, WorkflowMode(new_mode))

    def _display_tips(self, result: AgentResult) -> None:
        """Display tips from an agent result if available."""
        if result.tips:
            self.console.print("\n")
            self.console.print(Panel(
                Markdown(result.tips),
                title="Coding Tips & Best Practices",
                border_style="yellow",
            ))
