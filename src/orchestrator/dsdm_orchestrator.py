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
from ..agents.product_manager_agent import ProductManagerAgent
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
from ..tools.feasibility_optimizer import (
    quick_feasibility_check,
    generate_quick_feasibility_report,
    get_feasibility_cache,
)


def _moscow_to_jira_priority(moscow: str) -> str:
    """Convert MoSCoW priority to Jira priority."""
    mapping = {
        "must_have": "Highest",
        "should_have": "High",
        "could_have": "Medium",
        "wont_have": "Low",
    }
    return mapping.get(moscow.lower().replace(" ", "_"), "Medium")


class DSDMPhase(Enum):
    """DSDM project phases."""
    FEASIBILITY = "feasibility"
    PRD_TRD = "prd_trd"  # PRD (Product Manager) and TRD (Dev Lead) creation after feasibility
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
        DSDMPhase.PRD_TRD,
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
        include_confluence: bool = True,
        include_jira: bool = True,
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
                PhaseConfig(DSDMPhase.PRD_TRD, ProductManagerAgent, AgentMode.AUTOMATED),
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
        skip_fast_path: bool = False,
    ) -> AgentResult:
        """Run a specific phase."""
        # Special handling for PRD_TRD phase - runs both Product Manager and Dev Lead
        if phase == DSDMPhase.PRD_TRD:
            return self._run_prd_trd_phase(user_input, context)

        # Quick feasibility fast-path for FEASIBILITY phase
        if phase == DSDMPhase.FEASIBILITY and not skip_fast_path:
            quick_result = self._try_quick_feasibility(user_input)
            if quick_result is not None:
                return quick_result

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

        # Cache the result for future quick lookups
        if phase == DSDMPhase.FEASIBILITY and result.success:
            cache = get_feasibility_cache()
            cache.set(user_input, result.artifacts or {})

        return result

    def _try_quick_feasibility(self, user_input: str) -> Optional[AgentResult]:
        """
        Attempt quick feasibility assessment without running full agent.

        Returns AgentResult if quick assessment is confident enough,
        None if full analysis is needed.
        """
        quick_check = quick_feasibility_check(user_input)

        # Only use fast-path if confidence is high enough
        if not quick_check.is_quick_path or quick_check.confidence < 0.8:
            return None

        # For "needs_analysis" recommendation, always do full analysis
        if quick_check.recommendation == "needs_analysis":
            return None

        self.current_phase = DSDMPhase.FEASIBILITY

        # Display fast-path notification
        self.console.print("\n[bold cyan]═══ Quick Feasibility Assessment ═══[/bold cyan]")
        self.console.print(f"[dim]Fast-path activated (confidence: {quick_check.confidence * 100:.0f}%)[/dim]")

        if quick_check.project_type:
            self.console.print(f"[dim]Detected project type: {quick_check.project_type.replace('_', ' ').title()}[/dim]")

        # Generate the report
        report = generate_quick_feasibility_report(quick_check, user_input)

        # Build artifacts
        artifacts = {
            "phase": "feasibility",
            "recommendation": quick_check.recommendation,
            "fast_path": True,
            "confidence": quick_check.confidence,
            "project_type": quick_check.project_type,
        }

        if quick_check.cached_assessment:
            artifacts.update(quick_check.cached_assessment)

        # Determine if we should proceed to next phase
        go_recommendation = quick_check.recommendation == "go"

        result = AgentResult(
            success=True,
            output=report,
            artifacts=artifacts,
            requires_next_phase=go_recommendation,
            next_phase_input={
                "feasibility_report": report,
                "recommendation": quick_check.recommendation,
                "project_type": quick_check.project_type,
                "fast_path": True,
            } if go_recommendation else None,
        )

        self.results[DSDMPhase.FEASIBILITY] = result
        self.current_phase = None

        # Display result
        self.formatter.format_agent_result(
            phase_or_role="Feasibility (Quick)",
            success=True,
            output=report,
            artifacts=artifacts,
        )

        # Ask user if they want full analysis in interactive mode
        if self.config.interactive and quick_check.confidence < 0.95:
            self.console.print("\n[yellow]Quick assessment complete. Full analysis available if needed.[/yellow]")
            if Confirm.ask("Run full feasibility analysis instead?"):
                return None  # Fall through to full analysis

        return result

    def _run_prd_trd_phase(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Run the PRD/TRD phase - Product Manager creates PRD, Dev Lead creates TRD."""
        self.current_phase = DSDMPhase.PRD_TRD

        # Get context from previous phases (feasibility and business study)
        full_context = context or {}
        if DSDMPhase.FEASIBILITY in self.results and self.results[DSDMPhase.FEASIBILITY].next_phase_input:
            full_context.update(self.results[DSDMPhase.FEASIBILITY].next_phase_input)
        if DSDMPhase.BUSINESS_STUDY in self.results and self.results[DSDMPhase.BUSINESS_STUDY].next_phase_input:
            full_context.update(self.results[DSDMPhase.BUSINESS_STUDY].next_phase_input)

        combined_output = []
        combined_artifacts = {}
        all_tool_calls = []

        # Step 1: Product Manager creates PRD
        pm_agent = self.agents.get(DSDMPhase.PRD_TRD)
        if pm_agent:
            self.formatter.format_agent_start(
                agent_name="Product Manager",
                phase_or_role="PRD Creation",
                mode=pm_agent.mode.value,
                description="Creating Product Requirements Document based on feasibility analysis",
            )

            prd_input = f"""Based on the feasibility analysis and business study, create a comprehensive Product Requirements Document (PRD).

Feasibility Context:
{full_context.get('feasibility_report', user_input)}

Business Study Context:
{full_context.get('business_study_report', '')}

Create the PRD with:
1. Executive Summary
2. Problem Statement
3. Product Vision
4. Target Audience & User Personas
5. Business Objectives with Success Metrics
6. Feature Specifications (using MoSCoW prioritization)
7. User Journeys
8. Constraints & Assumptions
9. Risks & Mitigations
10. Release Plan (MVP, Phase 1, Future)

Use the generate_product_requirements_document tool to create the formal PRD."""

            prd_result = pm_agent.run(prd_input, full_context)
            combined_output.append(f"## PRD Creation\n{prd_result.output}")
            combined_artifacts["prd"] = prd_result.artifacts
            all_tool_calls.extend(prd_result.tool_calls or [])

            self.formatter.format_agent_result(
                phase_or_role="PRD Creation",
                success=prd_result.success,
                output=prd_result.output,
                artifacts=prd_result.artifacts,
                tool_calls=pm_agent.tool_call_history if hasattr(pm_agent, 'tool_call_history') else None,
            )

            if not prd_result.success:
                self.current_phase = None
                return AgentResult(
                    success=False,
                    output="PRD creation failed",
                    artifacts=combined_artifacts,
                    tool_calls=all_tool_calls,
                )

            # Update context with PRD output for TRD creation
            full_context["prd_output"] = prd_result.output
            full_context["prd_artifacts"] = prd_result.artifacts

        # Step 2: Dev Lead creates TRD based on PRD
        dev_lead_agent = self.design_build_agents.get(DesignBuildRole.DEV_LEAD)
        if dev_lead_agent:
            self.formatter.format_agent_start(
                agent_name="Dev Lead",
                phase_or_role="TRD Creation",
                mode=dev_lead_agent.mode.value,
                description="Creating Technical Requirements Document based on PRD",
            )

            trd_input = f"""Based on the Product Requirements Document (PRD) and business study, create a comprehensive Technical Requirements Document (TRD).

PRD Summary:
{full_context.get('prd_output', '')}

Business Study Context:
{full_context.get('business_study_report', '')}

Feasibility Context:
{full_context.get('feasibility_report', user_input)}

Create the TRD with:
1. Executive Summary (technical perspective)
2. System Overview & Key Features
3. Architecture Design (type, components, data flow, tech stack)
4. Functional Requirements (with acceptance criteria)
5. Non-Functional Requirements (performance, security, reliability, scalability)
6. API Specifications
7. Data Models
8. Security Requirements (auth, authorization, data protection, compliance)
9. Testing Requirements (unit, integration, e2e, coverage targets)
10. Deployment Requirements (environments, infrastructure, CI/CD, monitoring)
11. Dependencies
12. Known Limitations
13. Future Considerations

Use the generate_technical_requirements_document tool to create the formal TRD."""

            trd_result = dev_lead_agent.run(trd_input, full_context)
            combined_output.append(f"\n## TRD Creation\n{trd_result.output}")
            combined_artifacts["trd"] = trd_result.artifacts
            all_tool_calls.extend(trd_result.tool_calls or [])

            self.formatter.format_agent_result(
                phase_or_role="TRD Creation",
                success=trd_result.success,
                output=trd_result.output,
                artifacts=trd_result.artifacts,
                tool_calls=dev_lead_agent.tool_call_history if hasattr(dev_lead_agent, 'tool_call_history') else None,
            )

            if not trd_result.success:
                self.current_phase = None
                return AgentResult(
                    success=False,
                    output="TRD creation failed",
                    artifacts=combined_artifacts,
                    tool_calls=all_tool_calls,
                )

            full_context["trd_output"] = trd_result.output
            full_context["trd_artifacts"] = trd_result.artifacts

        # Step 3: Get approval from Dev Lead and Test Lead before syncing to Jira/Confluence
        approval_granted = False
        if self.config.interactive:
            self.console.print("\n[bold cyan]═══ PRD/TRD Approval Required ═══[/bold cyan]")
            self.console.print("\n[yellow]The following documents have been created:[/yellow]")
            self.console.print("  • Product Requirements Document (PRD)")
            self.console.print("  • Technical Requirements Document (TRD)")
            self.console.print("\n[yellow]These documents require approval from Dev Lead and Test Lead[/yellow]")
            self.console.print("[yellow]before being pushed to Jira and Confluence.[/yellow]\n")

            # Show summary of documents
            if full_context.get("prd_artifacts"):
                self.console.print("[dim]PRD Summary:[/dim]")
                prd_sections = full_context.get("prd_artifacts", {}).get("sections_included", {})
                if prd_sections:
                    features_count = prd_sections.get("features", 0)
                    self.console.print(f"  - Features defined: {features_count}")

            if full_context.get("trd_artifacts"):
                self.console.print("[dim]TRD Summary:[/dim]")
                trd_sections = full_context.get("trd_artifacts", {}).get("sections_included", {})
                if trd_sections:
                    func_req = trd_sections.get("functional_requirements", 0)
                    nfr_req = trd_sections.get("non_functional_requirements", 0)
                    self.console.print(f"  - Functional requirements: {func_req}")
                    self.console.print(f"  - Non-functional requirements: {nfr_req}")

            self.console.print("")
            approval_granted = Confirm.ask(
                "[bold]Dev Lead & Test Lead: Do you approve these documents for Jira/Confluence sync?[/bold]"
            )
        else:
            # In non-interactive mode, auto-approve
            approval_granted = True

        # Step 4: Sync to Jira and Confluence if approved and integrations are enabled
        sync_results = {}
        if approval_granted:
            combined_output.append("\n## Document Approval")
            combined_output.append("✓ PRD and TRD approved by Dev Lead and Test Lead")

            # Check if Jira/Confluence integrations are available
            jira_tool = self.tool_registry.get("jira_create_issue")
            confluence_tool = self.tool_registry.get("confluence_create_page")

            if jira_tool or confluence_tool:
                self.console.print("\n[bold cyan]═══ Syncing to Jira/Confluence ═══[/bold cyan]")

                # Sync PRD to Confluence
                if confluence_tool:
                    self.formatter.format_progress(1, 2, "Pushing PRD to Confluence")
                    prd_sync = self._sync_prd_to_confluence(full_context)
                    sync_results["confluence_prd"] = prd_sync
                    if prd_sync.get("success"):
                        combined_output.append(f"✓ PRD synced to Confluence (Page ID: {prd_sync.get('page_id', 'N/A')})")
                    else:
                        combined_output.append(f"⚠ PRD Confluence sync: {prd_sync.get('error', 'Failed')}")

                    # Sync TRD to Confluence
                    self.formatter.format_progress(2, 2, "Pushing TRD to Confluence")
                    trd_sync = self._sync_trd_to_confluence(full_context)
                    sync_results["confluence_trd"] = trd_sync
                    if trd_sync.get("success"):
                        combined_output.append(f"✓ TRD synced to Confluence (Page ID: {trd_sync.get('page_id', 'N/A')})")
                    else:
                        combined_output.append(f"⚠ TRD Confluence sync: {trd_sync.get('error', 'Failed')}")

                # Create Jira issues from requirements
                if jira_tool:
                    self.formatter.format_progress(1, 1, "Creating Jira issues from requirements")
                    jira_sync = self._sync_requirements_to_jira(full_context)
                    sync_results["jira"] = jira_sync
                    if jira_sync.get("success"):
                        created_count = jira_sync.get("created_count", 0)
                        combined_output.append(f"✓ {created_count} requirements synced to Jira")
                    else:
                        combined_output.append(f"⚠ Jira sync: {jira_sync.get('error', 'Failed')}")

                combined_artifacts["sync_results"] = sync_results
            else:
                combined_output.append("\n[Note: Jira/Confluence integrations not enabled. Documents saved locally only.]")
        else:
            combined_output.append("\n## Document Approval")
            combined_output.append("✗ Documents not approved - Jira/Confluence sync skipped")
            combined_output.append("  Please review and re-run the PRD_TRD phase after addressing concerns.")

        self.current_phase = None

        # Combine results
        final_result = AgentResult(
            success=True,
            output="\n".join(combined_output),
            artifacts=combined_artifacts,
            tool_calls=all_tool_calls,
            requires_next_phase=approval_granted,  # Only proceed if approved
            next_phase_input={
                "prd_output": full_context.get("prd_output", ""),
                "trd_output": full_context.get("trd_output", ""),
                "prd_artifacts": full_context.get("prd_artifacts", {}),
                "trd_artifacts": full_context.get("trd_artifacts", {}),
                "approval_granted": approval_granted,
                "sync_results": sync_results,
            },
        )

        self.results[DSDMPhase.PRD_TRD] = final_result
        return final_result

    def _sync_prd_to_confluence(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sync PRD to Confluence."""
        try:
            confluence_tool = self.tool_registry.get("confluence_create_dsdm_doc")
            if not confluence_tool:
                confluence_tool = self.tool_registry.get("confluence_create_page")

            if not confluence_tool:
                return {"success": False, "error": "Confluence tools not available"}

            # Get project name from context
            prd_artifacts = context.get("prd_artifacts", {})
            project_name = prd_artifacts.get("project_name", "Project")

            # Get space key from environment or use default
            import os
            space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "PROJ")

            # Build PRD content for Confluence
            prd_output = context.get("prd_output", "")
            content_sections = {
                "Executive Summary": prd_artifacts.get("executive_summary", "See PRD document"),
                "Problem Statement": prd_artifacts.get("problem_statement", "See PRD document"),
                "Features": f"Total features defined: {prd_artifacts.get('sections_included', {}).get('features', 0)}",
                "Full Document": prd_output[:2000] + "..." if len(prd_output) > 2000 else prd_output,
            }

            if confluence_tool.name == "confluence_create_dsdm_doc":
                result = confluence_tool.handler(
                    space_key=space_key,
                    doc_type="business_requirements",
                    project_name=project_name,
                    content_sections=content_sections,
                )
            else:
                # Use basic page creation
                content = f"<h1>{project_name} - Product Requirements Document</h1>"
                content += f"<p>{prd_output}</p>"
                result = confluence_tool.handler(
                    space_key=space_key,
                    title=f"{project_name} - PRD",
                    content=content,
                )

            import json
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sync_trd_to_confluence(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sync TRD to Confluence."""
        try:
            confluence_tool = self.tool_registry.get("confluence_create_dsdm_doc")
            if not confluence_tool:
                confluence_tool = self.tool_registry.get("confluence_create_page")

            if not confluence_tool:
                return {"success": False, "error": "Confluence tools not available"}

            # Get project name from context
            trd_artifacts = context.get("trd_artifacts", {})
            project_name = trd_artifacts.get("project_name", "Project")

            # Get space key from environment or use default
            import os
            space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "PROJ")

            # Build TRD content for Confluence
            trd_output = context.get("trd_output", "")
            content_sections = {
                "Architecture Overview": trd_artifacts.get("architecture", {}).get("type", "See TRD document"),
                "Functional Requirements": f"Total: {trd_artifacts.get('sections_included', {}).get('functional_requirements', 0)}",
                "Non-Functional Requirements": f"Total: {trd_artifacts.get('sections_included', {}).get('non_functional_requirements', 0)}",
                "Full Document": trd_output[:2000] + "..." if len(trd_output) > 2000 else trd_output,
            }

            if confluence_tool.name == "confluence_create_dsdm_doc":
                result = confluence_tool.handler(
                    space_key=space_key,
                    doc_type="technical_design",
                    project_name=project_name,
                    content_sections=content_sections,
                )
            else:
                # Use basic page creation
                content = f"<h1>{project_name} - Technical Requirements Document</h1>"
                content += f"<p>{trd_output}</p>"
                result = confluence_tool.handler(
                    space_key=space_key,
                    title=f"{project_name} - TRD",
                    content=content,
                )

            import json
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _sync_requirements_to_jira(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sync requirements from PRD/TRD to Jira as issues."""
        try:
            bulk_create_tool = self.tool_registry.get("jira_bulk_create_requirements")
            if not bulk_create_tool:
                create_tool = self.tool_registry.get("jira_create_issue")
                if not create_tool:
                    return {"success": False, "error": "Jira tools not available"}

            import os
            project_key = os.environ.get("JIRA_PROJECT_KEY", "PROJ")

            # Extract requirements from PRD artifacts
            prd_artifacts = context.get("prd_artifacts", {})
            features = prd_artifacts.get("features", [])

            if not features:
                # If no structured features, create a single epic for the PRD
                return {"success": True, "created_count": 0, "message": "No structured features to sync"}

            # Build requirements list for bulk creation
            requirements = []
            for feature in features if isinstance(features, list) else []:
                if isinstance(feature, dict):
                    req = {
                        "summary": feature.get("name", feature.get("id", "Feature")),
                        "description": feature.get("description", ""),
                        "priority": _moscow_to_jira_priority(feature.get("priority", "should_have")),
                        "issue_type": "Story",
                    }
                    requirements.append(req)

            if bulk_create_tool and requirements:
                result = bulk_create_tool.handler(
                    project_key=project_key,
                    requirements=requirements,
                )
                import json
                return json.loads(result)
            else:
                return {"success": True, "created_count": 0, "message": "No requirements to create"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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

    def load_trd_from_file(self, file_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load a TRD file from the directory and parse its content."""
        import os
        import json
        trd_content = None
        if not file_path:
            # Try to find a TRD file in the current directory or a known location
            candidates = [
                "TRD.md", "trd.md", "TRD.json", "trd.json",
                "docs/TRD.md", "docs/trd.md", "docs/TRD.json", "docs/trd.json"
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    file_path = candidate
                    break
        if not file_path or not os.path.exists(file_path):
            self.console.print(f"[red]TRD file not found at: {file_path or 'default locations'}[/red]")
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                if file_path.endswith(".json"):
                    trd_content = json.load(f)
                else:
                    trd_content = f.read()
            self.console.print(f"[green]Loaded TRD from {file_path}[/green]")
            return {"trd_output": trd_content, "trd_file_path": file_path}
        except Exception as e:
            self.console.print(f"[red]Failed to load TRD: {e}[/red]")
            return None

    def design_build_from_trd(self, trd_context: Dict[str, Any]) -> None:
        """Run Design & Build phase/team using a TRD loaded from file."""
        self.console.print("\n[bold cyan]Design & Build from TRD[/bold cyan]\n")
        # Option to run the whole team or a specific role
        choice = Prompt.ask(
            "Run (1) Full Design & Build Team or (2) Specific Role?",
            choices=["1", "2"]
        )
        if choice == "1":
            self.run_design_build_team(user_input="Design & Build from TRD", context=trd_context)
        else:
            role_names = [r.value for r in self.DESIGN_BUILD_ROLE_ORDER if r in self.design_build_agents]
            self.console.print("\nAvailable roles:")
            for i, name in enumerate(role_names, 1):
                self.console.print(f"  {i}. {name.replace('_', ' ').title()}")
            role_choice = Prompt.ask("Select role", choices=[str(i) for i in range(1, len(role_names) + 1)])
            role = DesignBuildRole(role_names[int(role_choice) - 1])
            self.run_design_build_role(role, user_input="Design & Build from TRD", context=trd_context)

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
            self.console.print("7. Design & Build from TRD in directory")
            self.console.print("8. Exit")

            choice = Prompt.ask("Select option", choices=[str(i) for i in range(1, 9)])

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
                file_path = Prompt.ask("Enter TRD file path (leave blank to auto-detect)", default="")
                trd_context = self.load_trd_from_file(file_path if file_path else None)
                if trd_context:
                    self.design_build_from_trd(trd_context)
            elif choice == "8":
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
