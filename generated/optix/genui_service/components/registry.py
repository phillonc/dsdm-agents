"""
Component Registry

Registry of pre-built, optimized UI components for options trading.
LLM can compose these components or generate custom variations.
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
from ..models.schemas import ComponentInfo


# Component definitions
COMPONENT_DEFINITIONS = {
    "OptionsChainTable": {
        "name": "OptionsChainTable",
        "description": "Interactive options chain with calls/puts, Greeks, and real-time data. Supports sorting, filtering, and row expansion.",
        "props": ["symbol", "expiration", "columns", "onStrikeSelect", "highlightATM", "showVolume"],
        "fsm_states": ["loading", "ready", "filtering", "expanded", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/options_chain_preview.png",
    },
    "GreeksGauges": {
        "name": "GreeksGauges",
        "description": "Visual gauges displaying Delta, Gamma, Theta, Vega with color-coded risk levels and animated updates.",
        "props": ["greeks", "ranges", "format", "showLabels", "animated"],
        "fsm_states": ["loading", "ready", "updating", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/greeks_gauges_preview.png",
    },
    "PayoffDiagram": {
        "name": "PayoffDiagram",
        "description": "Strategy payoff P&L chart showing profit/loss across price range with breakeven points and max profit/loss markers.",
        "props": ["legs", "underlying_range", "current_price", "showBreakeven", "showMaxPL"],
        "fsm_states": ["loading", "ready", "hovering", "zooming", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/payoff_diagram_preview.png",
    },
    "VolatilitySurface": {
        "name": "VolatilitySurface",
        "description": "3D implied volatility surface visualization with rotation, zoom, and strike/expiration tooltips.",
        "props": ["symbol", "expirations", "strikes", "colorScale", "showGrid"],
        "fsm_states": ["loading", "ready", "rotating", "zooming", "hovering", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/vol_surface_preview.png",
    },
    "PositionCard": {
        "name": "PositionCard",
        "description": "Single position summary card with expandable details, P&L display, and Greeks.",
        "props": ["position", "show_greeks", "show_pnl", "expandable"],
        "fsm_states": ["collapsed", "expanded", "loading", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/position_card_preview.png",
    },
    "StrategyBuilder": {
        "name": "StrategyBuilder",
        "description": "Drag-drop strategy leg builder with real-time payoff preview and validation.",
        "props": ["symbol", "available_legs", "on_change", "maxLegs"],
        "fsm_states": ["idle", "dragging", "validating", "confirmed", "error"],
        "category": "interactive",
        "preview_url": "https://cdn.optix.io/components/strategy_builder_preview.png",
    },
    "AlertConfigurator": {
        "name": "AlertConfigurator",
        "description": "Price/condition alert setup interface with multiple condition types and notification options.",
        "props": ["symbol", "alert_types", "on_create", "existing_alerts"],
        "fsm_states": ["idle", "configuring", "validating", "created", "error"],
        "category": "interactive",
        "preview_url": "https://cdn.optix.io/components/alert_config_preview.png",
    },
    "EarningsCalendar": {
        "name": "EarningsCalendar",
        "description": "Upcoming earnings calendar with IV rank display and event filtering.",
        "props": ["symbols", "date_range", "show_iv", "groupBy"],
        "fsm_states": ["loading", "ready", "filtered", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/earnings_calendar_preview.png",
    },
    "GEXHeatmap": {
        "name": "GEXHeatmap",
        "description": "Gamma exposure heatmap showing dealer positioning across strikes with gamma flip line.",
        "props": ["symbol", "expiration", "color_scale", "showFlipLine"],
        "fsm_states": ["loading", "ready", "hovering", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/gex_heatmap_preview.png",
    },
    "FlowTicker": {
        "name": "FlowTicker",
        "description": "Real-time unusual options flow ticker with filtering and intent classification.",
        "props": ["symbols", "min_premium", "flow_types", "maxItems"],
        "fsm_states": ["loading", "streaming", "paused", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/flow_ticker_preview.png",
    },
    "QuoteCard": {
        "name": "QuoteCard",
        "description": "Real-time stock quote card with price, change, and market data.",
        "props": ["symbol", "showExtended", "showChart", "compact"],
        "fsm_states": ["loading", "ready", "updating", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/quote_card_preview.png",
    },
    "PortfolioSummary": {
        "name": "PortfolioSummary",
        "description": "Portfolio overview with total value, P&L, and aggregate Greeks.",
        "props": ["accounts", "groupBy", "showGreeks", "showAllocations"],
        "fsm_states": ["loading", "ready", "error"],
        "category": "data",
        "preview_url": "https://cdn.optix.io/components/portfolio_summary_preview.png",
    },
    "IVRankGauge": {
        "name": "IVRankGauge",
        "description": "IV Rank/Percentile gauge with historical context.",
        "props": ["symbol", "showHistory", "period"],
        "fsm_states": ["loading", "ready", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/iv_rank_gauge_preview.png",
    },
    "StrategyComparison": {
        "name": "StrategyComparison",
        "description": "Side-by-side strategy comparison with metrics and payoff diagrams.",
        "props": ["strategies", "metrics", "showPayoffs"],
        "fsm_states": ["loading", "ready", "error"],
        "category": "visualization",
        "preview_url": "https://cdn.optix.io/components/strategy_comparison_preview.png",
    },
    "TradingEducation": {
        "name": "TradingEducation",
        "description": "Educational component with animated explanations and interactive examples.",
        "props": ["topic", "level", "showExamples", "interactive"],
        "fsm_states": ["loading", "ready", "interactive", "error"],
        "category": "educational",
        "preview_url": "https://cdn.optix.io/components/trading_education_preview.png",
    },
}


class ComponentRegistry:
    """
    Registry of pre-built UI components for options trading.
    Provides component metadata, templates, and validation.
    """

    def __init__(self):
        """Initialize the component registry."""
        self._components = COMPONENT_DEFINITIONS
        self._templates_path = Path(__file__).parent / "templates"

    def list_components(self) -> List[ComponentInfo]:
        """
        List all available components.

        Returns:
            List of ComponentInfo objects
        """
        return [
            ComponentInfo(
                name=comp["name"],
                description=comp["description"],
                props=comp["props"],
                preview_url=comp.get("preview_url"),
                fsm_states=comp["fsm_states"],
                category=comp.get("category"),
            )
            for comp in self._components.values()
        ]

    def get_component(self, name: str) -> Optional[ComponentInfo]:
        """
        Get a specific component by name.

        Args:
            name: Component name

        Returns:
            ComponentInfo or None if not found
        """
        if name not in self._components:
            return None

        comp = self._components[name]
        return ComponentInfo(
            name=comp["name"],
            description=comp["description"],
            props=comp["props"],
            preview_url=comp.get("preview_url"),
            fsm_states=comp["fsm_states"],
            category=comp.get("category"),
        )

    def get_components_by_category(self, category: str) -> List[ComponentInfo]:
        """
        Get components by category.

        Args:
            category: Category name (data, visualization, interactive, educational)

        Returns:
            List of ComponentInfo objects in the category
        """
        return [
            ComponentInfo(
                name=comp["name"],
                description=comp["description"],
                props=comp["props"],
                preview_url=comp.get("preview_url"),
                fsm_states=comp["fsm_states"],
                category=comp.get("category"),
            )
            for comp in self._components.values()
            if comp.get("category") == category
        ]

    def get_component_template(self, name: str) -> Optional[str]:
        """
        Get the HTML template for a component.

        Args:
            name: Component name

        Returns:
            HTML template string or None
        """
        template_file = self._templates_path / f"{name.lower()}.html"
        if template_file.exists():
            return template_file.read_text()

        # Return a basic template if file doesn't exist
        return self._generate_basic_template(name)

    def _generate_basic_template(self, name: str) -> str:
        """Generate a basic template for a component."""
        comp = self._components.get(name)
        if not comp:
            return None

        props_attrs = " ".join(f'data-{p}=""' for p in comp["props"])
        states = ", ".join(comp["fsm_states"])

        return f'''<!-- {name} Component Template -->
<div class="optix-component {name.lower()}" {props_attrs} data-state="loading">
  <div class="component-loading">
    <div class="spinner"></div>
    <span>Loading {name}...</span>
  </div>
  <div class="component-content" style="display: none;">
    <!-- Component content rendered here -->
  </div>
  <div class="component-error" style="display: none;">
    <span class="error-icon">⚠️</span>
    <span class="error-message">Failed to load component</span>
    <button class="retry-btn">Retry</button>
  </div>
</div>

<style>
.{name.lower()} {{
  background: var(--optix-bg-card, #1E293B);
  border-radius: var(--optix-radius-md, 8px);
  padding: var(--optix-space-md, 16px);
}}

.{name.lower()} .component-loading {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: var(--optix-text-muted, #94A3B8);
}}

.{name.lower()} .spinner {{
  width: 20px;
  height: 20px;
  border: 2px solid var(--optix-border, #334155);
  border-top-color: var(--optix-primary, #2563EB);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}}

@keyframes spin {{
  to {{ transform: rotate(360deg); }}
}}
</style>

<script>
// {name} FSM States: {states}
(function() {{
  const component = document.querySelector('.{name.lower()}');
  const dataBridge = window.OPTIXDataBridge || {{ request: async () => ({{}}), subscribe: () => {{}} }};

  let state = 'loading';

  function setState(newState) {{
    state = newState;
    component.dataset.state = newState;

    const loading = component.querySelector('.component-loading');
    const content = component.querySelector('.component-content');
    const error = component.querySelector('.component-error');

    loading.style.display = newState === 'loading' ? 'flex' : 'none';
    content.style.display = newState === 'ready' ? 'block' : 'none';
    error.style.display = newState === 'error' ? 'flex' : 'none';
  }}

  async function init() {{
    try {{
      // Fetch component data
      const data = await dataBridge.request('{name.lower()}', {{}});
      renderContent(data);
      setState('ready');
    }} catch (e) {{
      console.error('{name} error:', e);
      setState('error');
    }}
  }}

  function renderContent(data) {{
    const content = component.querySelector('.component-content');
    // Render component content based on data
    content.innerHTML = '<p>Component loaded</p>';
  }}

  // Retry button
  component.querySelector('.retry-btn')?.addEventListener('click', () => {{
    setState('loading');
    init();
  }});

  // Initialize
  init();
}})();
</script>
'''

    def validate_props(self, name: str, props: Dict[str, Any]) -> List[str]:
        """
        Validate props for a component.

        Args:
            name: Component name
            props: Props to validate

        Returns:
            List of validation error messages
        """
        errors = []
        comp = self._components.get(name)

        if not comp:
            errors.append(f"Unknown component: {name}")
            return errors

        valid_props = set(comp["props"])
        provided_props = set(props.keys())

        # Check for unknown props
        unknown = provided_props - valid_props
        if unknown:
            errors.append(f"Unknown props: {', '.join(unknown)}")

        return errors

    def get_component_names(self) -> List[str]:
        """Get list of all component names."""
        return list(self._components.keys())


# Create singleton instance
component_registry = ComponentRegistry()
