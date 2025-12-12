"""
Code Synthesizer Module

Generates executable HTML/CSS/JS from structured requirements and FSM state.
Uses iterative refinement with generation-evaluation cycles.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..models.schemas import (
    RequirementSpec,
    ComponentFSM,
    GenerationContext,
    UserPreferences,
    ThemeMode,
    ExpertiseLevel,
)
from ..llm.providers import LLMProvider, get_llm_provider
from ..llm.prompts.generation import get_generation_prompt
from ..config import settings


class GeneratedUI:
    """Container for generated UI output."""

    def __init__(
        self,
        html: str,
        metadata: Dict[str, Any],
        score: float = 0.0,
        iteration: int = 1,
    ):
        self.html = html
        self.metadata = metadata
        self.score = score
        self.iteration = iteration


class CodeSynthesizer:
    """
    Generates executable HTML/CSS/JS from structured representation.
    Uses iterative refinement with generation-evaluation cycles.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize the code synthesizer.

        Args:
            llm_provider: Optional LLM provider instance
        """
        self._llm = llm_provider

    async def get_llm(self) -> LLMProvider:
        """Get or create the LLM provider."""
        if self._llm is None:
            self._llm = await get_llm_provider()
        return self._llm

    async def synthesize(
        self,
        requirements: RequirementSpec,
        fsm: Optional[Dict[str, ComponentFSM]] = None,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None,
        max_iterations: int = None,
        target_score: float = None,
    ) -> GeneratedUI:
        """
        Generate UI code from requirements using iterative refinement.

        Args:
            requirements: Structured requirements
            fsm: Component FSM definitions
            context: Generation context (symbol, positions, etc.)
            preferences: User UI preferences
            max_iterations: Maximum refinement iterations
            target_score: Target quality score (0-100)

        Returns:
            GeneratedUI with HTML/CSS/JS code
        """
        max_iterations = max_iterations or settings.max_iterations
        target_score = target_score or settings.target_score

        best_candidate = None
        best_score = 0.0

        for iteration in range(1, max_iterations + 1):
            # Generate candidate
            candidate = await self._generate_candidate(
                requirements=requirements,
                fsm=fsm,
                context=context,
                preferences=preferences,
                previous=best_candidate,
                iteration=iteration,
            )

            # Evaluate candidate
            score = await self._evaluate_candidate(candidate, requirements)
            candidate.score = score
            candidate.iteration = iteration

            if score > best_score:
                best_candidate = candidate
                best_score = score

            # Check if we've reached target score
            if score >= target_score:
                break

        return best_candidate

    async def _generate_candidate(
        self,
        requirements: RequirementSpec,
        fsm: Optional[Dict[str, ComponentFSM]],
        context: Optional[GenerationContext],
        preferences: Optional[UserPreferences],
        previous: Optional[GeneratedUI],
        iteration: int,
    ) -> GeneratedUI:
        """Generate a UI candidate."""
        llm = await self.get_llm()

        # Build the generation prompt
        prompt = get_generation_prompt(
            requirements=requirements,
            fsm=fsm,
            context=context,
            preferences=preferences,
            previous_html=previous.html if previous else None,
            previous_score=previous.score if previous else None,
            iteration=iteration,
        )

        # Generate with LLM
        response = await llm.generate(
            prompt=prompt,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

        # Extract HTML from response
        html = self._extract_html(response.content)

        # Build metadata
        metadata = {
            "query_parsed": {
                "intent": requirements.intent,
                "symbol": requirements.symbol,
                "symbols": requirements.symbols,
                "filters": requirements.filters,
            },
            "components_used": self._extract_components(html),
            "data_subscriptions": self._build_data_subscriptions(requirements),
            "llm_provider": response.provider,
            "llm_model": response.model,
            "token_count": response.token_count,
            "iteration_count": iteration,
        }

        return GeneratedUI(
            html=html,
            metadata=metadata,
        )

    def _extract_html(self, content: str) -> str:
        """Extract HTML from LLM response."""
        # Look for HTML code block
        if "```html" in content:
            start = content.find("```html") + 7
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        # Look for generic code block
        if "```" in content:
            start = content.find("```") + 3
            # Skip language identifier if present
            newline = content.find("\n", start)
            if newline > start and newline - start < 20:
                start = newline + 1
            end = content.find("```", start)
            if end > start:
                return content[start:end].strip()

        # Look for DOCTYPE
        if "<!DOCTYPE" in content or "<html" in content:
            start = content.find("<!DOCTYPE")
            if start == -1:
                start = content.find("<html")
            end = content.rfind("</html>")
            if end > start:
                return content[start:end + 7].strip()

        # Return as-is if no markers found
        return content.strip()

    def _extract_components(self, html: str) -> List[str]:
        """Extract component names used in the HTML."""
        components = []
        component_markers = [
            "OptionsChainTable",
            "GreeksGauges",
            "PayoffDiagram",
            "VolatilitySurface",
            "PositionCard",
            "StrategyBuilder",
            "AlertConfigurator",
            "EarningsCalendar",
            "GEXHeatmap",
            "FlowTicker",
            "QuoteCard",
        ]

        for marker in component_markers:
            if marker.lower() in html.lower() or marker in html:
                components.append(marker)

        return components if components else ["CustomComponent"]

    def _build_data_subscriptions(
        self,
        requirements: RequirementSpec
    ) -> List[str]:
        """Build list of data subscriptions needed."""
        subscriptions = []

        # Add quote subscription for primary symbol
        if requirements.symbol:
            subscriptions.append(f"quote:{requirements.symbol}")

        # Add additional subscriptions based on data needs
        if "options_chain" in requirements.target_data:
            if requirements.symbol:
                subscriptions.append(f"options_chain:{requirements.symbol}")

        if "flow" in requirements.target_data:
            if requirements.symbol:
                subscriptions.append(f"flow:{requirements.symbol}")
            else:
                subscriptions.append("flow:market")

        if "gex" in requirements.target_data:
            if requirements.symbol:
                subscriptions.append(f"gex:{requirements.symbol}")

        # Add subscriptions for additional symbols
        if requirements.symbols:
            for symbol in requirements.symbols[1:]:  # Skip first (primary)
                subscriptions.append(f"quote:{symbol}")

        return subscriptions

    async def _evaluate_candidate(
        self,
        candidate: GeneratedUI,
        requirements: RequirementSpec
    ) -> float:
        """
        Evaluate a generated UI candidate.

        Scores based on:
        - Functional: Does it address the query?
        - Interactive: Are interactions appropriate?
        - Aesthetic: Does it follow the design system?
        """
        score = 0.0
        checks = []

        html_lower = candidate.html.lower()

        # Functional checks (40% weight)
        functional_checks = []

        # Check for required data presence
        if requirements.symbol:
            functional_checks.append(
                requirements.symbol.lower() in html_lower
            )

        # Check for appropriate visualizations
        for viz in requirements.visualizations:
            if viz == "table":
                functional_checks.append("<table" in html_lower)
            elif viz == "chart":
                functional_checks.append(
                    "chart" in html_lower or "canvas" in html_lower
                )
            elif viz == "card":
                functional_checks.append("card" in html_lower)

        # Check for data bindings
        functional_checks.append("{{data:" in html_lower or "data-" in html_lower)

        if functional_checks:
            functional_score = sum(functional_checks) / len(functional_checks) * 40
        else:
            functional_score = 20  # Base score

        # Interactive checks (35% weight)
        interactive_checks = []

        # Check for loading states
        interactive_checks.append("loading" in html_lower)

        # Check for error handling
        interactive_checks.append("error" in html_lower)

        # Check for interactions
        for interaction in requirements.interactions:
            if interaction == "click":
                interactive_checks.append(
                    "onclick" in html_lower or
                    "click" in html_lower or
                    "addeventlistener" in html_lower
                )
            elif interaction == "hover":
                interactive_checks.append(
                    "hover" in html_lower or
                    ":hover" in html_lower
                )
            elif interaction == "sort":
                interactive_checks.append("sort" in html_lower)
            elif interaction == "filter":
                interactive_checks.append("filter" in html_lower)

        if interactive_checks:
            interactive_score = sum(interactive_checks) / len(interactive_checks) * 35
        else:
            interactive_score = 17.5

        # Aesthetic checks (25% weight)
        aesthetic_checks = []

        # Check for proper structure
        aesthetic_checks.append("<!doctype html>" in html_lower)
        aesthetic_checks.append("<head>" in html_lower)
        aesthetic_checks.append("<body>" in html_lower)

        # Check for styling
        aesthetic_checks.append("<style" in html_lower or "style=" in html_lower)

        # Check for OPTIX design system colors
        aesthetic_checks.append(
            "#2563eb" in html_lower or  # Primary blue
            "#0f172a" in html_lower or  # Dark background
            "var(--" in html_lower      # CSS variables
        )

        # Check for responsive design
        aesthetic_checks.append(
            "viewport" in html_lower or
            "flex" in html_lower or
            "grid" in html_lower
        )

        if aesthetic_checks:
            aesthetic_score = sum(aesthetic_checks) / len(aesthetic_checks) * 25
        else:
            aesthetic_score = 12.5

        total_score = functional_score + interactive_score + aesthetic_score

        # Store breakdown in metadata
        candidate.metadata["evaluation_breakdown"] = {
            "functional": round(functional_score, 2),
            "interactive": round(interactive_score, 2),
            "aesthetic": round(aesthetic_score, 2),
        }

        return round(total_score, 2)

    async def synthesize_refinement(
        self,
        original: GeneratedUI,
        refinement: str,
        requirements: RequirementSpec,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> GeneratedUI:
        """
        Refine an existing generated UI.

        Args:
            original: The original generated UI
            refinement: Refinement instructions
            requirements: Original requirements
            context: Generation context
            preferences: User preferences

        Returns:
            Refined GeneratedUI
        """
        llm = await self.get_llm()

        # Build refinement prompt
        prompt = f"""You are refining an existing UI for the OPTIX options trading platform.

## Original UI
```html
{original.html}
```

## Refinement Request
{refinement}

## Requirements
- Intent: {requirements.intent}
- Symbol: {requirements.symbol}
- Visualizations: {requirements.visualizations}

## Instructions
1. Keep the overall structure and styling
2. Apply the requested refinement
3. Maintain all existing functionality
4. Ensure the UI remains complete and functional

Generate the refined HTML document:
"""

        response = await llm.generate(
            prompt=prompt,
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

        html = self._extract_html(response.content)

        # Identify changes made
        changes_made = self._identify_changes(original.html, html, refinement)

        metadata = {
            **original.metadata,
            "refinement_applied": refinement,
            "changes_made": changes_made,
            "llm_provider": response.provider,
            "llm_model": response.model,
            "token_count": response.token_count,
        }

        return GeneratedUI(
            html=html,
            metadata=metadata,
        )

    def _identify_changes(
        self,
        original_html: str,
        refined_html: str,
        refinement: str
    ) -> List[str]:
        """Identify changes made during refinement."""
        changes = []

        refinement_lower = refinement.lower()

        # Check for common refinement patterns
        if "put" in refinement_lower and "puts" not in original_html.lower():
            changes.append("added_puts_columns")
        if "call" in refinement_lower and "calls" not in original_html.lower():
            changes.append("added_calls_columns")
        if "delta" in refinement_lower:
            changes.append("added_delta_display")
        if "gamma" in refinement_lower:
            changes.append("added_gamma_display")
        if "chart" in refinement_lower:
            changes.append("added_chart")
        if "color" in refinement_lower:
            changes.append("modified_colors")
        if "sort" in refinement_lower:
            changes.append("added_sorting")
        if "filter" in refinement_lower:
            changes.append("added_filtering")

        if not changes:
            changes.append("general_refinement")

        return changes


# Create factory function
def get_code_synthesizer(
    llm_provider: Optional[LLMProvider] = None
) -> CodeSynthesizer:
    """Get a code synthesizer instance."""
    return CodeSynthesizer(llm_provider=llm_provider)
