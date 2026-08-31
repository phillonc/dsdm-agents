"""Lane routing — how a functional requirement finds its delivery lanes.

Routing is a case-insensitive keyword match, anchored at a word boundary
(spec §4.1). The anchor matters: an unanchored ``"ui"`` also matches *build*
and *requirement*, which would route almost everything to the frontend. Keywords
still match forward, so ``"auth"`` covers *authentication* and *authorised*.

Routing is intentionally simple and inspectable: a reader of the TRD can tell
exactly why a requirement landed in a lane, and the result never changes
between runs.
"""

from __future__ import annotations

import re
from typing import Dict, Pattern, Tuple

from .model import BACKEND, DATA, DEVOPS, FRONTEND, LANE_ORDER, SECURITY

#: Lane → the words that route a requirement into it (spec §4.1).
LANE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    FRONTEND: (
        "ui", "screen", "page", "view", "form", "button", "layout", "css",
        "react", "mobile", "browser", "dashboard", "navigation", "accessib",
    ),
    BACKEND: (
        "api", "endpoint", "service", "server", "logic", "workflow",
        "integration", "webhook", "queue", "job", "process", "account",
        "register", "registration", "notification", "email", "payment",
        "calculate", "validate", "rule",
    ),
    DATA: (
        "data", "database", "schema", "model", "migration", "store", "persist",
        "record", "report", "analytics", "index", "search",
    ),
    SECURITY: (
        "auth", "login", "log in", "sign in", "sign-in", "permission", "role",
        "encrypt", "gdpr", "consent", "audit", "token", "secret", "credential",
        "pii", "password",
    ),
    DEVOPS: (
        "deploy", "ci", "cd", "pipeline", "monitor", "alert", "infrastructure",
        "scale", "availability", "backup", "release",
    ),
}

#: Where a requirement goes when it matches nothing (spec §4.1).
DEFAULT_LANE = BACKEND


def _anchored(word: str) -> Pattern[str]:
    """A word-boundary-anchored, forward-matching pattern for one keyword."""
    return re.compile(r"\b" + re.escape(word), re.IGNORECASE)


_LANE_PATTERNS: Dict[str, Tuple[Tuple[str, Pattern[str]], ...]] = {
    lane: tuple((word, _anchored(word)) for word in words)
    for lane, words in LANE_KEYWORDS.items()
}


def lanes_for(text: str) -> Tuple[str, ...]:
    """Return the lanes ``text`` routes to, in canonical lane order.

    Never returns an empty tuple — an unmatched requirement falls to
    :data:`DEFAULT_LANE` rather than being dropped.
    """
    subject = str(text)
    matched = tuple(
        lane
        for lane in LANE_ORDER
        if lane in _LANE_PATTERNS
        and any(pattern.search(subject) for _, pattern in _LANE_PATTERNS[lane])
    )
    return matched or (DEFAULT_LANE,)


def routing_reason(text: str, lane: str) -> Tuple[str, ...]:
    """The keywords that put ``text`` in ``lane`` — used to explain a routing."""
    subject = str(text)
    return tuple(
        word for word, pattern in _LANE_PATTERNS.get(lane, ()) if pattern.search(subject)
    )
