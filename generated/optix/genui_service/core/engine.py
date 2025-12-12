"""
GenUI Engine - Main Generation Orchestrator

Coordinates the three-stage pipeline:
1. Requirement Specification - Parse query into structured requirements
2. Structured Representation - Build FSM and component graph
3. UI Code Synthesis - Generate HTML/CSS/JS with data bindings
"""

import asyncio
import time
import uuid
from typing import Optional, AsyncGenerator, Dict, Any
from datetime import datetime

from .requirement_parser import RequirementParser, requirement_parser
from .fsm_builder import FSMBuilder, fsm_builder
from .code_synthesizer import CodeSynthesizer, GeneratedUI, get_code_synthesizer
from .post_processor import PostProcessor, post_processor, ProcessedUI

from ..models.schemas import (
    GenerateUIRequest,
    GenerateUIResponse,
    RefineUIRequest,
    GenerationStatus,
    GenerationMetadata,
    GenerationContext,
    UserPreferences,
    StreamEvent,
    RequirementSpec,
    ComponentFSM,
)
from ..config import settings


class GenerationResult:
    """Result of a complete generation."""

    def __init__(
        self,
        generation_id: str,
        status: GenerationStatus,
        html: Optional[str],
        metadata: GenerationMetadata,
        generation_time_ms: int,
    ):
        self.generation_id = generation_id
        self.status = status
        self.html = html
        self.metadata = metadata
        self.generation_time_ms = generation_time_ms
        self.created_at = datetime.utcnow()


class GenUIEngine:
    """
    Main orchestrator for Generative UI generation.
    Implements the three-stage pipeline with iterative refinement.
    """

    def __init__(
        self,
        requirement_parser: Optional[RequirementParser] = None,
        fsm_builder: Optional[FSMBuilder] = None,
        code_synthesizer: Optional[CodeSynthesizer] = None,
        post_processor: Optional[PostProcessor] = None,
    ):
        """
        Initialize the GenUI Engine.

        Args:
            requirement_parser: Optional custom requirement parser
            fsm_builder: Optional custom FSM builder
            code_synthesizer: Optional custom code synthesizer
            post_processor: Optional custom post-processor
        """
        self._parser = requirement_parser
        self._fsm_builder = fsm_builder
        self._synthesizer = code_synthesizer
        self._post_processor = post_processor

    @property
    def parser(self) -> RequirementParser:
        """Get the requirement parser."""
        if self._parser is None:
            self._parser = requirement_parser
        return self._parser

    @property
    def fsm(self) -> FSMBuilder:
        """Get the FSM builder."""
        if self._fsm_builder is None:
            self._fsm_builder = fsm_builder
        return self._fsm_builder

    @property
    def synthesizer(self) -> CodeSynthesizer:
        """Get the code synthesizer."""
        if self._synthesizer is None:
            self._synthesizer = get_code_synthesizer()
        return self._synthesizer

    @property
    def processor(self) -> PostProcessor:
        """Get the post-processor."""
        if self._post_processor is None:
            self._post_processor = post_processor
        return self._post_processor

    async def generate(
        self,
        query: str,
        user_id: Optional[str] = None,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> GenerationResult:
        """
        Generate a custom UI from a natural language query.

        Args:
            query: Natural language query
            user_id: Optional user ID
            context: Optional generation context
            preferences: Optional user preferences

        Returns:
            GenerationResult with HTML and metadata
        """
        start_time = time.time()
        generation_id = str(uuid.uuid4())

        try:
            # Stage 1: Parse requirements
            requirements = await self.parser.parse(
                query=query,
                context=context,
                preferences=preferences,
            )

            # Stage 2: Build FSM
            component_fsms = self.fsm.get_fsm_for_requirements(requirements)
            interaction_graph = self.fsm.build_interaction_graph(
                requirements=requirements,
                components=list(component_fsms.keys()),
            )

            # Stage 3: Synthesize code
            generated_ui = await self.synthesizer.synthesize(
                requirements=requirements,
                fsm=component_fsms,
                context=context,
                preferences=preferences,
            )

            # Post-process
            processed = await self.processor.process(
                generated_html=generated_ui.html,
                context={
                    "requirements": requirements.model_dump(),
                    "preferences": preferences.model_dump() if preferences else None,
                },
            )

            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Build metadata
            metadata = GenerationMetadata(
                query_parsed=generated_ui.metadata.get("query_parsed"),
                components_used=generated_ui.metadata.get("components_used", []),
                data_subscriptions=generated_ui.metadata.get("data_subscriptions", []),
                evaluation_score=generated_ui.score,
                llm_provider=generated_ui.metadata.get("llm_provider"),
                llm_model=generated_ui.metadata.get("llm_model"),
                token_count=generated_ui.metadata.get("token_count"),
                iteration_count=generated_ui.metadata.get("iteration_count", 1),
            )

            return GenerationResult(
                generation_id=generation_id,
                status=GenerationStatus.COMPLETE,
                html=processed.html,
                metadata=metadata,
                generation_time_ms=generation_time_ms,
            )

        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            return GenerationResult(
                generation_id=generation_id,
                status=GenerationStatus.FAILED,
                html=None,
                metadata=GenerationMetadata(),
                generation_time_ms=generation_time_ms,
            )

    async def generate_stream(
        self,
        query: str,
        user_id: Optional[str] = None,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream UI generation progress with events.

        Args:
            query: Natural language query
            user_id: Optional user ID
            context: Optional generation context
            preferences: Optional user preferences

        Yields:
            StreamEvent objects with progress updates
        """
        start_time = time.time()
        generation_id = str(uuid.uuid4())

        try:
            # Started event
            yield StreamEvent(
                event="started",
                generation_id=generation_id,
            )

            # Stage 1: Parsing
            yield StreamEvent(
                event="parsing",
                generation_id=generation_id,
                progress=10,
                message="Parsing query...",
            )

            requirements = await self.parser.parse(
                query=query,
                context=context,
                preferences=preferences,
            )

            # Stage 2: Planning
            yield StreamEvent(
                event="planning",
                generation_id=generation_id,
                progress=25,
                message="Building component graph...",
            )

            component_fsms = self.fsm.get_fsm_for_requirements(requirements)
            interaction_graph = self.fsm.build_interaction_graph(
                requirements=requirements,
                components=list(component_fsms.keys()),
            )

            # Stage 3: Generating
            yield StreamEvent(
                event="generating",
                generation_id=generation_id,
                progress=50,
                message="Synthesizing UI code...",
            )

            generated_ui = await self.synthesizer.synthesize(
                requirements=requirements,
                fsm=component_fsms,
                context=context,
                preferences=preferences,
            )

            # Post-processing
            yield StreamEvent(
                event="post_processing",
                generation_id=generation_id,
                progress=80,
                message="Applying security sanitization...",
            )

            processed = await self.processor.process(
                generated_html=generated_ui.html,
                context={
                    "requirements": requirements.model_dump(),
                    "preferences": preferences.model_dump() if preferences else None,
                },
            )

            # Evaluating
            yield StreamEvent(
                event="evaluating",
                generation_id=generation_id,
                progress=90,
                message="Evaluating quality...",
            )

            # Small delay to show evaluation step
            await asyncio.sleep(0.1)

            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Build metadata
            metadata = GenerationMetadata(
                query_parsed=generated_ui.metadata.get("query_parsed"),
                components_used=generated_ui.metadata.get("components_used", []),
                data_subscriptions=generated_ui.metadata.get("data_subscriptions", []),
                evaluation_score=generated_ui.score,
                llm_provider=generated_ui.metadata.get("llm_provider"),
                llm_model=generated_ui.metadata.get("llm_model"),
                token_count=generated_ui.metadata.get("token_count"),
                iteration_count=generated_ui.metadata.get("iteration_count", 1),
            )

            # Complete event
            yield StreamEvent(
                event="complete",
                generation_id=generation_id,
                progress=100,
                html=processed.html,
                metadata=metadata,
            )

        except Exception as e:
            yield StreamEvent(
                event="error",
                generation_id=generation_id,
                error=str(e),
            )

    async def refine(
        self,
        generation_id: str,
        original_html: str,
        original_metadata: Dict[str, Any],
        refinement: str,
        user_id: Optional[str] = None,
        context: Optional[GenerationContext] = None,
        preferences: Optional[UserPreferences] = None,
    ) -> GenerationResult:
        """
        Refine an existing generated UI.

        Args:
            generation_id: ID of original generation
            original_html: HTML of original generation
            original_metadata: Metadata of original generation
            refinement: Refinement instructions
            user_id: Optional user ID
            context: Optional generation context
            preferences: Optional user preferences

        Returns:
            GenerationResult with refined HTML
        """
        start_time = time.time()
        new_generation_id = str(uuid.uuid4())

        try:
            # Reconstruct requirements from metadata
            query_parsed = original_metadata.get("query_parsed", {})
            requirements = RequirementSpec(
                intent=query_parsed.get("intent", "general_view"),
                target_data=[],
                symbol=query_parsed.get("symbol"),
                symbols=query_parsed.get("symbols"),
                filters=query_parsed.get("filters"),
                visualizations=[],
                interactions=[],
            )

            # Create GeneratedUI from original
            original_ui = GeneratedUI(
                html=original_html,
                metadata=original_metadata,
                score=original_metadata.get("evaluation_score", 0),
            )

            # Refine
            refined_ui = await self.synthesizer.synthesize_refinement(
                original=original_ui,
                refinement=refinement,
                requirements=requirements,
                context=context,
                preferences=preferences,
            )

            # Post-process
            processed = await self.processor.process(
                generated_html=refined_ui.html,
            )

            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Build metadata
            metadata = GenerationMetadata(
                query_parsed=refined_ui.metadata.get("query_parsed"),
                components_used=refined_ui.metadata.get("components_used", []),
                data_subscriptions=refined_ui.metadata.get("data_subscriptions", []),
                evaluation_score=refined_ui.score,
                llm_provider=refined_ui.metadata.get("llm_provider"),
                llm_model=refined_ui.metadata.get("llm_model"),
                token_count=refined_ui.metadata.get("token_count"),
                iteration_count=1,
                refinement_applied=refinement,
                changes_made=refined_ui.metadata.get("changes_made", []),
            )

            return GenerationResult(
                generation_id=new_generation_id,
                status=GenerationStatus.COMPLETE,
                html=processed.html,
                metadata=metadata,
                generation_time_ms=generation_time_ms,
            )

        except Exception as e:
            generation_time_ms = int((time.time() - start_time) * 1000)
            return GenerationResult(
                generation_id=new_generation_id,
                status=GenerationStatus.FAILED,
                html=None,
                metadata=GenerationMetadata(),
                generation_time_ms=generation_time_ms,
            )


# Create singleton instance
genui_engine = GenUIEngine()


def get_genui_engine() -> GenUIEngine:
    """Get the GenUI engine instance."""
    return genui_engine
