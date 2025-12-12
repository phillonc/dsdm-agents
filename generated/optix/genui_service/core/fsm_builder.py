"""
FSM Builder Module

Models UI components as Finite State Machines for predictable behavior.
Based on the "Generative Interfaces for Language Models" framework.

ℳ = (𝒮, ℰ, δ, s₀)
Where:
- 𝒮 = Set of atomic interface states
- ℰ = User-triggered events (click, hover, input)
- δ = State transition function
- s₀ = Initial state
"""

from typing import List, Dict, Optional, Any
from ..models.schemas import (
    ComponentFSM,
    StateTransition,
    ComponentState,
    InteractionGraph,
    RequirementSpec,
)


# Pre-defined FSM configurations for common components
COMPONENT_FSMS = {
    "OptionsChainTable": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.FILTERING,
            ComponentState.EXPANDED,
            ComponentState.COLLAPSED,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "click_row",
            "apply_filter",
            "clear_filter",
            "change_sort",
            "change_expiration",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "click_row", ComponentState.EXPANDED),
            (ComponentState.EXPANDED, "click_row", ComponentState.COLLAPSED),
            (ComponentState.COLLAPSED, "click_row", ComponentState.EXPANDED),
            (ComponentState.READY, "apply_filter", ComponentState.FILTERING),
            (ComponentState.FILTERING, "data_loaded", ComponentState.READY),
            (ComponentState.READY, "change_sort", ComponentState.LOADING),
            (ComponentState.READY, "change_expiration", ComponentState.LOADING),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "GreeksGauges": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.UPDATING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "data_update",
            "update_complete",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "data_update", ComponentState.UPDATING),
            (ComponentState.UPDATING, "update_complete", ComponentState.READY),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "PayoffDiagram": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.HOVERING,
            ComponentState.ZOOMING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "mouse_enter",
            "mouse_leave",
            "zoom_in",
            "zoom_out",
            "reset_zoom",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "mouse_enter", ComponentState.HOVERING),
            (ComponentState.HOVERING, "mouse_leave", ComponentState.READY),
            (ComponentState.READY, "zoom_in", ComponentState.ZOOMING),
            (ComponentState.ZOOMING, "zoom_out", ComponentState.READY),
            (ComponentState.ZOOMING, "reset_zoom", ComponentState.READY),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "VolatilitySurface": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.ROTATING,
            ComponentState.ZOOMING,
            ComponentState.HOVERING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "drag_start",
            "drag_end",
            "zoom_in",
            "zoom_out",
            "mouse_enter",
            "mouse_leave",
            "reset_view",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "drag_start", ComponentState.ROTATING),
            (ComponentState.ROTATING, "drag_end", ComponentState.READY),
            (ComponentState.READY, "zoom_in", ComponentState.ZOOMING),
            (ComponentState.ZOOMING, "zoom_out", ComponentState.READY),
            (ComponentState.READY, "mouse_enter", ComponentState.HOVERING),
            (ComponentState.HOVERING, "mouse_leave", ComponentState.READY),
            (ComponentState.READY, "reset_view", ComponentState.LOADING),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "PositionCard": {
        "states": [
            ComponentState.COLLAPSED,
            ComponentState.EXPANDED,
            ComponentState.LOADING,
            ComponentState.ERROR,
        ],
        "events": [
            "click_expand",
            "click_collapse",
            "refresh",
            "data_loaded",
            "error",
        ],
        "transitions": [
            (ComponentState.COLLAPSED, "click_expand", ComponentState.EXPANDED),
            (ComponentState.EXPANDED, "click_collapse", ComponentState.COLLAPSED),
            (ComponentState.COLLAPSED, "refresh", ComponentState.LOADING),
            (ComponentState.EXPANDED, "refresh", ComponentState.LOADING),
            (ComponentState.LOADING, "data_loaded", ComponentState.COLLAPSED),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
        ],
        "initial_state": ComponentState.COLLAPSED,
    },
    "StrategyBuilder": {
        "states": [
            ComponentState.READY,
            ComponentState.DRAGGING,
            ComponentState.VALIDATING,
            ComponentState.CONFIRMED,
            ComponentState.ERROR,
        ],
        "events": [
            "drag_start",
            "drag_end",
            "drop_leg",
            "remove_leg",
            "validate",
            "confirm",
            "reset",
            "error",
        ],
        "transitions": [
            (ComponentState.READY, "drag_start", ComponentState.DRAGGING),
            (ComponentState.DRAGGING, "drag_end", ComponentState.READY),
            (ComponentState.DRAGGING, "drop_leg", ComponentState.VALIDATING),
            (ComponentState.VALIDATING, "validate", ComponentState.READY),
            (ComponentState.READY, "confirm", ComponentState.CONFIRMED),
            (ComponentState.CONFIRMED, "reset", ComponentState.READY),
            (ComponentState.VALIDATING, "error", ComponentState.ERROR),
            (ComponentState.ERROR, "reset", ComponentState.READY),
        ],
        "initial_state": ComponentState.READY,
    },
    "AlertConfigurator": {
        "states": [
            ComponentState.READY,
            ComponentState.VALIDATING,
            ComponentState.CONFIRMED,
            ComponentState.ERROR,
        ],
        "events": [
            "input_change",
            "validate",
            "create",
            "reset",
            "error",
        ],
        "transitions": [
            (ComponentState.READY, "input_change", ComponentState.VALIDATING),
            (ComponentState.VALIDATING, "validate", ComponentState.READY),
            (ComponentState.READY, "create", ComponentState.CONFIRMED),
            (ComponentState.CONFIRMED, "reset", ComponentState.READY),
            (ComponentState.VALIDATING, "error", ComponentState.ERROR),
            (ComponentState.ERROR, "reset", ComponentState.READY),
        ],
        "initial_state": ComponentState.READY,
    },
    "EarningsCalendar": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.FILTERING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "filter_change",
            "date_select",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "filter_change", ComponentState.FILTERING),
            (ComponentState.FILTERING, "data_loaded", ComponentState.READY),
            (ComponentState.READY, "date_select", ComponentState.LOADING),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "GEXHeatmap": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.HOVERING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "mouse_enter",
            "mouse_leave",
            "expiration_change",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "mouse_enter", ComponentState.HOVERING),
            (ComponentState.HOVERING, "mouse_leave", ComponentState.READY),
            (ComponentState.READY, "expiration_change", ComponentState.LOADING),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "FlowTicker": {
        "states": [
            ComponentState.LOADING,
            ComponentState.STREAMING,
            ComponentState.PAUSED,
            ComponentState.ERROR,
        ],
        "events": [
            "connected",
            "pause",
            "resume",
            "filter_change",
            "disconnect",
            "error",
            "retry",
        ],
        "transitions": [
            (ComponentState.LOADING, "connected", ComponentState.STREAMING),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.STREAMING, "pause", ComponentState.PAUSED),
            (ComponentState.PAUSED, "resume", ComponentState.STREAMING),
            (ComponentState.STREAMING, "filter_change", ComponentState.LOADING),
            (ComponentState.STREAMING, "disconnect", ComponentState.LOADING),
            (ComponentState.ERROR, "retry", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
    "QuoteCard": {
        "states": [
            ComponentState.LOADING,
            ComponentState.READY,
            ComponentState.UPDATING,
            ComponentState.ERROR,
        ],
        "events": [
            "data_loaded",
            "price_update",
            "refresh",
            "error",
        ],
        "transitions": [
            (ComponentState.LOADING, "data_loaded", ComponentState.READY),
            (ComponentState.LOADING, "error", ComponentState.ERROR),
            (ComponentState.READY, "price_update", ComponentState.UPDATING),
            (ComponentState.UPDATING, "data_loaded", ComponentState.READY),
            (ComponentState.READY, "refresh", ComponentState.LOADING),
            (ComponentState.ERROR, "refresh", ComponentState.LOADING),
        ],
        "initial_state": ComponentState.LOADING,
    },
}

# Intent to component mapping
INTENT_COMPONENT_MAP = {
    "options_chain": ["OptionsChainTable", "QuoteCard"],
    "greeks_display": ["GreeksGauges", "PositionCard"],
    "payoff_diagram": ["PayoffDiagram", "StrategyBuilder"],
    "volatility_surface": ["VolatilitySurface"],
    "strategy_builder": ["StrategyBuilder", "PayoffDiagram"],
    "strategy_comparison": ["PayoffDiagram", "GreeksGauges"],
    "portfolio_view": ["PositionCard", "GreeksGauges"],
    "educational": ["PayoffDiagram", "GreeksGauges"],
    "earnings_calendar": ["EarningsCalendar"],
    "flow_analysis": ["FlowTicker", "OptionsChainTable"],
    "alert_setup": ["AlertConfigurator"],
    "gex_analysis": ["GEXHeatmap", "QuoteCard"],
    "quote_view": ["QuoteCard"],
    "general_view": ["QuoteCard", "OptionsChainTable"],
}


class FSMBuilder:
    """
    Builds Finite State Machines for UI components based on requirements.
    """

    def __init__(self):
        """Initialize the FSM builder."""
        self._component_fsms = COMPONENT_FSMS
        self._intent_map = INTENT_COMPONENT_MAP

    def build_component_fsm(
        self,
        component_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ComponentFSM:
        """
        Build an FSM for a specific component.

        Args:
            component_name: Name of the component
            config: Optional configuration overrides

        Returns:
            ComponentFSM instance
        """
        if component_name not in self._component_fsms:
            # Return a generic FSM for unknown components
            return self._build_generic_fsm(component_name)

        fsm_def = self._component_fsms[component_name]

        transitions = [
            StateTransition(
                from_state=from_state,
                event=event,
                to_state=to_state,
            )
            for from_state, event, to_state in fsm_def["transitions"]
        ]

        return ComponentFSM(
            component_name=component_name,
            states=fsm_def["states"],
            events=fsm_def["events"],
            transitions=transitions,
            initial_state=fsm_def["initial_state"],
        )

    def _build_generic_fsm(self, component_name: str) -> ComponentFSM:
        """Build a generic FSM for unknown components."""
        return ComponentFSM(
            component_name=component_name,
            states=[
                ComponentState.LOADING,
                ComponentState.READY,
                ComponentState.ERROR,
            ],
            events=["data_loaded", "error", "retry"],
            transitions=[
                StateTransition(
                    from_state=ComponentState.LOADING,
                    event="data_loaded",
                    to_state=ComponentState.READY,
                ),
                StateTransition(
                    from_state=ComponentState.LOADING,
                    event="error",
                    to_state=ComponentState.ERROR,
                ),
                StateTransition(
                    from_state=ComponentState.ERROR,
                    event="retry",
                    to_state=ComponentState.LOADING,
                ),
            ],
            initial_state=ComponentState.LOADING,
        )

    def build_interaction_graph(
        self,
        requirements: RequirementSpec,
        components: Optional[List[str]] = None
    ) -> InteractionGraph:
        """
        Build an interaction graph for the UI based on requirements.

        The graph models high-level interaction flows as 𝒢 = (𝒱, 𝒯)
        where nodes are interface views and edges are transitions.

        Args:
            requirements: Parsed requirements
            components: Optional list of components to include

        Returns:
            InteractionGraph instance
        """
        # Get components from requirements if not provided
        if not components:
            components = self.get_components_for_intent(requirements.intent)

        # Build nodes (each component is a node)
        nodes = components.copy()

        # Add view-level nodes
        if requirements.educational:
            nodes.append("TutorialView")
        if requirements.comparison:
            nodes.append("ComparisonView")

        # Build edges based on likely user flows
        edges = []

        # Connect main component to secondary components
        if len(components) > 1:
            for i in range(len(components) - 1):
                edges.append({
                    "from": components[i],
                    "to": components[i + 1],
                    "event": "navigate"
                })

        # Add common interaction edges
        for component in components:
            # All components can transition to error view
            edges.append({
                "from": component,
                "to": "ErrorView",
                "event": "error"
            })
            # Error view can retry back to component
            edges.append({
                "from": "ErrorView",
                "to": component,
                "event": "retry"
            })

        # Add tutorial transitions for educational content
        if requirements.educational and "TutorialView" in nodes:
            edges.append({
                "from": components[0],
                "to": "TutorialView",
                "event": "help"
            })
            edges.append({
                "from": "TutorialView",
                "to": components[0],
                "event": "dismiss"
            })

        return InteractionGraph(nodes=nodes, edges=edges)

    def get_components_for_intent(self, intent: str) -> List[str]:
        """
        Get recommended components for a given intent.

        Args:
            intent: The detected intent

        Returns:
            List of component names
        """
        return self._intent_map.get(intent, ["QuoteCard"])

    def get_all_component_names(self) -> List[str]:
        """Get list of all available component names."""
        return list(self._component_fsms.keys())

    def get_fsm_for_requirements(
        self,
        requirements: RequirementSpec
    ) -> Dict[str, ComponentFSM]:
        """
        Build FSMs for all components needed by requirements.

        Args:
            requirements: Parsed requirements

        Returns:
            Dictionary mapping component names to their FSMs
        """
        components = self.get_components_for_intent(requirements.intent)
        return {
            component: self.build_component_fsm(component)
            for component in components
        }


# Create singleton instance
fsm_builder = FSMBuilder()
