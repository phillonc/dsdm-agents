"""
LLM prompt templates for Generative UI.
"""

from .generation import get_generation_prompt
from .system import GENUI_SYSTEM_PROMPT

__all__ = [
    "get_generation_prompt",
    "GENUI_SYSTEM_PROMPT",
]
