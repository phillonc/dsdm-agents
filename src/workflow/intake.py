"""Stage 0 — intake.

Normalises whatever the caller inputted (free text, a markdown file, a dict, or
an already-built :class:`Requirement`) into the single shape the rest of the
pipeline consumes. See spec §2.

The item-extraction rule is what makes the whole workflow deterministic: every
markdown bullet becomes one requirement item, in source order, and a
description with no bullets becomes a single item. The same requirement text
therefore always produces the same PRD, TRD and TASKS documents.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .model import (
    Requirement,
    RequirementItem,
    RawRequirement,
    canonical_priority,
    numbered,
    sequence_of,
)

# "- item", "* item", "1. item", "2) item" — with any leading indentation.
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<text>.+?)\s*$")
# An inline MoSCoW marker at the end of a bullet, e.g. "... (Must)" or "[should]".
_INLINE_PRIORITY = re.compile(r"[\(\[](?P<priority>must|should|could|won'?t)(?:\s+have)?[\)\]]\s*$", re.I)


class IntakeError(ValueError):
    """Raised when the inputted requirement cannot be normalised."""


def _split_items(description: str) -> List[str]:
    """Pull the requirement items out of a description (spec §2)."""
    bullets = [
        match.group("text")
        for match in (_BULLET.match(line) for line in description.splitlines())
        if match
    ]
    if bullets:
        return bullets

    # No bullets: the description is one item. Drop markdown headings and
    # collapse whitespace so the item reads as a single sentence.
    body = " ".join(
        line.strip()
        for line in description.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    return [body] if body else []


def _item_from(raw: Any, index: int, default_priority: str, default_effort: float) -> RequirementItem:
    if isinstance(raw, dict):
        text = str(raw.get("text") or raw.get("title") or "").strip()
        if not text:
            raise IntakeError(f"requirement item #{index} has no text")
        priority = canonical_priority(raw.get("priority", default_priority), default_priority)
        try:
            effort = float(raw.get("effort", default_effort))
        except (TypeError, ValueError):
            raise IntakeError(f"requirement item {text!r} has a non-numeric effort")
        return RequirementItem(raw.get("id") or numbered("REQ", index), text, priority, effort)

    text = str(raw).strip()
    if not text:
        raise IntakeError(f"requirement item #{index} has no text")

    # An inline "(Must)" marker overrides the requirement-level priority.
    priority = default_priority
    marker = _INLINE_PRIORITY.search(text)
    if marker:
        priority = canonical_priority(marker.group("priority"), default_priority)
        text = text[: marker.start()].strip().rstrip("-–—").strip()

    return RequirementItem(numbered("REQ", index), text, priority, default_effort)


def normalise_requirement(raw: RawRequirement) -> Requirement:
    """Turn ``raw`` into a :class:`Requirement` with its items extracted.

    ``raw`` may be a free-text string (its first line is the title), a mapping,
    or an existing :class:`Requirement` (whose items are filled in if empty).
    """
    if isinstance(raw, Requirement):
        requirement = raw
        payload: Dict[str, Any] = {}
    elif isinstance(raw, dict):
        payload = dict(raw)
        title = str(payload.get("title") or "").strip()
        description = str(payload.get("description") or "").strip()
        if not title and description:
            # Allow a description-only dict: promote its first line to the title.
            title, _, description = description.partition("\n")
            title, description = title.strip().lstrip("# ").strip(), description.strip()
        if not title:
            raise IntakeError("requirement has no title")
        requirement = Requirement(
            title=title,
            description=description,
            id=str(payload.get("id") or ""),
            requester=str(payload.get("requester") or ""),
            priority=canonical_priority(payload.get("priority", "S")),
            effort=float(payload.get("effort", 1.0)),
            goals=sequence_of(payload.get("goals")),
            constraints=sequence_of(payload.get("constraints")),
            acceptance=sequence_of(payload.get("acceptance") or payload.get("acceptance_criteria")),
            out_of_scope=sequence_of(payload.get("out_of_scope")),
            assumptions=sequence_of(payload.get("assumptions")),
            stakeholders=sequence_of(payload.get("stakeholders")),
        )
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise IntakeError("requirement text is empty")
        first, _, rest = text.partition("\n")
        requirement = Requirement(
            title=first.strip().lstrip("# ").strip(),
            description=rest.strip(),
        )
        payload = {}
    else:
        raise IntakeError(f"cannot read a requirement from {type(raw).__name__}")

    if not requirement.title.strip():
        raise IntakeError("requirement has no title")

    if not requirement.items:
        explicit = payload.get("items")
        sources = explicit if explicit else _split_items(requirement.description)
        if not sources:
            # A title-only requirement is still a requirement: the title is the item.
            sources = [requirement.title]
        requirement.items = [
            _item_from(raw_item, index, requirement.priority, requirement.effort)
            for index, raw_item in enumerate(sources, start=1)
        ]

    return requirement


def requirement_from_file(path: str, **overrides: Any) -> Requirement:
    """Read a markdown/text requirement from ``path``.

    A leading ``# Heading`` becomes the title; everything after it is the
    description.
    """
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if not text.strip():
        raise IntakeError(f"requirement file is empty: {path}")

    lines = text.splitlines()
    title: Optional[str] = None
    body_start = 0
    for index, line in enumerate(lines):
        if line.strip().startswith("# "):
            title = line.strip().lstrip("# ").strip()
            body_start = index + 1
            break
        if line.strip():
            break

    payload: Dict[str, Any] = {"description": "\n".join(lines[body_start:]).strip()}
    if title:
        payload["title"] = title
    payload.update(overrides)
    return normalise_requirement(payload)
