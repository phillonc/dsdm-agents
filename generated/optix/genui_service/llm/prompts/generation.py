"""
Generation prompt builder for UI synthesis.
"""

from typing import Optional, Dict, Any
from ...models.schemas import (
    RequirementSpec,
    ComponentFSM,
    GenerationContext,
    UserPreferences,
    ExpertiseLevel,
    ThemeMode,
)
from .system import GENUI_SYSTEM_PROMPT


def get_generation_prompt(
    requirements: RequirementSpec,
    fsm: Optional[Dict[str, ComponentFSM]] = None,
    context: Optional[GenerationContext] = None,
    preferences: Optional[UserPreferences] = None,
    previous_html: Optional[str] = None,
    previous_score: Optional[float] = None,
    iteration: int = 1,
) -> str:
    """
    Build the generation prompt for UI synthesis.

    Args:
        requirements: Parsed requirements
        fsm: Component FSM definitions
        context: Generation context
        preferences: User preferences
        previous_html: HTML from previous iteration (for refinement)
        previous_score: Score from previous iteration
        iteration: Current iteration number

    Returns:
        Complete prompt string
    """
    sections = [GENUI_SYSTEM_PROMPT]

    # Add requirements section
    sections.append(build_requirements_section(requirements))

    # Add context section if provided
    if context:
        sections.append(build_context_section(context))

    # Add preferences section if provided
    if preferences:
        sections.append(build_preferences_section(preferences))

    # Add FSM section if provided
    if fsm:
        sections.append(build_fsm_section(fsm))

    # Add refinement section if this is an iteration
    if iteration > 1 and previous_html:
        sections.append(build_refinement_section(
            previous_html=previous_html,
            previous_score=previous_score,
            iteration=iteration,
        ))

    # Add generation instructions
    sections.append(build_generation_instructions(requirements))

    return "\n\n".join(sections)


def build_requirements_section(requirements: RequirementSpec) -> str:
    """Build the requirements section of the prompt."""
    lines = ["## Requirements"]

    lines.append(f"- **Intent**: {requirements.intent}")

    if requirements.symbol:
        lines.append(f"- **Primary Symbol**: {requirements.symbol}")

    if requirements.symbols:
        lines.append(f"- **Symbols**: {', '.join(requirements.symbols)}")

    if requirements.target_data:
        lines.append(f"- **Data Types**: {', '.join(requirements.target_data)}")

    if requirements.visualizations:
        lines.append(f"- **Visualizations**: {', '.join(requirements.visualizations)}")

    if requirements.interactions:
        lines.append(f"- **Interactions**: {', '.join(requirements.interactions)}")

    if requirements.filters:
        filters_str = ", ".join(f"{k}={v}" for k, v in requirements.filters.items())
        lines.append(f"- **Filters**: {filters_str}")

    if requirements.time_range:
        lines.append(f"- **Time Range**: {requirements.time_range}")

    if requirements.expiration:
        lines.append(f"- **Expiration**: {requirements.expiration}")

    if requirements.educational:
        lines.append("- **Educational**: Yes - include explanations and tooltips")

    if requirements.comparison:
        lines.append("- **Comparison**: Yes - show side-by-side comparison")

    return "\n".join(lines)


def build_context_section(context: GenerationContext) -> str:
    """Build the context section of the prompt."""
    lines = ["## Context"]

    if context.symbol:
        lines.append(f"- **Symbol**: {context.symbol}")

    if context.current_price:
        lines.append(f"- **Current Price**: ${context.current_price:.2f}")

    if context.positions:
        lines.append("- **User Positions**:")
        for pos in context.positions[:5]:  # Limit to first 5
            pos_str = f"  - {pos.symbol}"
            if pos.strike:
                pos_str += f" {pos.strike}"
            if pos.option_type:
                pos_str += f" {pos.option_type}"
            if pos.quantity:
                pos_str += f" x{pos.quantity}"
            lines.append(pos_str)

    if context.watchlist:
        lines.append(f"- **Watchlist**: {', '.join(context.watchlist[:10])}")

    if context.market_status:
        lines.append(f"- **Market Status**: {context.market_status}")

    return "\n".join(lines)


def build_preferences_section(preferences: UserPreferences) -> str:
    """Build the preferences section of the prompt."""
    lines = ["## User Preferences"]

    if preferences.theme:
        lines.append(f"- **Theme**: {preferences.theme.value}")

    if preferences.chart_type:
        lines.append(f"- **Chart Type**: {preferences.chart_type.value}")

    if preferences.expertise_level:
        level = preferences.expertise_level
        if level == ExpertiseLevel.BEGINNER:
            lines.append("- **Expertise**: Beginner - use simple language, more explanations")
        elif level == ExpertiseLevel.INTERMEDIATE:
            lines.append("- **Expertise**: Intermediate - standard terminology")
        else:
            lines.append("- **Expertise**: Advanced - technical details, compact display")

    if preferences.custom_color_scheme:
        lines.append("- **Custom Colors**:")
        for key, value in preferences.custom_color_scheme.items():
            lines.append(f"  - {key}: {value}")

    if preferences.accessibility_settings:
        if preferences.accessibility_settings.get("reduce_motion"):
            lines.append("- **Accessibility**: Reduce motion - minimize animations")
        if preferences.accessibility_settings.get("high_contrast"):
            lines.append("- **Accessibility**: High contrast mode")
        if preferences.accessibility_settings.get("large_text"):
            lines.append("- **Accessibility**: Large text - increase font sizes")

    return "\n".join(lines)


def build_fsm_section(fsm: Dict[str, ComponentFSM]) -> str:
    """Build the FSM section of the prompt."""
    lines = ["## Component State Machines"]

    for name, component_fsm in fsm.items():
        lines.append(f"\n### {name}")
        lines.append(f"- **States**: {', '.join(s.value for s in component_fsm.states)}")
        lines.append(f"- **Events**: {', '.join(component_fsm.events)}")
        lines.append(f"- **Initial State**: {component_fsm.initial_state.value}")

        # Show a few key transitions
        lines.append("- **Key Transitions**:")
        for trans in component_fsm.transitions[:5]:
            lines.append(
                f"  - {trans.from_state.value} --[{trans.event}]--> {trans.to_state.value}"
            )

    return "\n".join(lines)


def build_refinement_section(
    previous_html: str,
    previous_score: Optional[float],
    iteration: int,
) -> str:
    """Build the refinement section for iterative improvement."""
    lines = ["## Refinement"]

    lines.append(f"This is iteration {iteration}. The previous generation scored {previous_score or 0:.1f}/100.")

    if previous_score and previous_score < 70:
        lines.append("\n**Issues to address:**")
        lines.append("- Ensure all required data fields are present")
        lines.append("- Verify loading and error states are implemented")
        lines.append("- Check that styling matches OPTIX design system")
        lines.append("- Ensure proper accessibility attributes")

    lines.append("\n**Previous HTML (for reference):**")
    # Include a truncated version if too long
    if len(previous_html) > 2000:
        lines.append(f"```html\n{previous_html[:2000]}...[truncated]\n```")
    else:
        lines.append(f"```html\n{previous_html}\n```")

    lines.append("\nImprove upon this implementation while maintaining the core functionality.")

    return "\n".join(lines)


def build_generation_instructions(requirements: RequirementSpec) -> str:
    """Build the final generation instructions."""
    lines = ["## Task"]

    # Build specific instruction based on intent
    intent_instructions = {
        "options_chain": "Generate an interactive options chain table showing calls and puts with Greeks.",
        "greeks_display": "Generate visual gauges or displays for the Greeks (Delta, Gamma, Theta, Vega).",
        "payoff_diagram": "Generate a payoff diagram showing profit/loss across price range.",
        "volatility_surface": "Generate a 3D volatility surface visualization.",
        "strategy_builder": "Generate a strategy builder interface for constructing options strategies.",
        "strategy_comparison": "Generate a side-by-side comparison of two or more strategies.",
        "portfolio_view": "Generate a portfolio overview showing positions and aggregate Greeks.",
        "educational": "Generate an educational interface explaining the options concept with examples.",
        "earnings_calendar": "Generate an earnings calendar showing upcoming events with IV data.",
        "flow_analysis": "Generate an unusual options flow display.",
        "alert_setup": "Generate an alert configuration interface.",
        "gex_analysis": "Generate a gamma exposure (GEX) visualization.",
        "quote_view": "Generate a quote card showing real-time price information.",
        "general_view": "Generate an appropriate interface for the user's query.",
    }

    instruction = intent_instructions.get(
        requirements.intent,
        "Generate an appropriate interface for the user's query."
    )
    lines.append(instruction)

    # Add specific requirements
    if requirements.symbol:
        lines.append(f"\nUse **{requirements.symbol}** as the primary symbol with placeholder data.")

    if requirements.educational:
        lines.append("\nInclude explanatory text and tooltips appropriate for learning.")

    if requirements.comparison:
        lines.append("\nShow items side-by-side for easy comparison.")

    lines.append("\n**Output a complete HTML document wrapped in ```html code fences.**")

    return "\n".join(lines)
