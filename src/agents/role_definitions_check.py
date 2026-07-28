"""Structural consistency checks for role_definitions.py, exposed as a
reusable function so both `tests/test_role_definitions.py` (pytest drift
guard) and `main.py --generate-agents` (operator-facing CLI diagnostic) can
run the same checks without duplicating the logic.

This intentionally does NOT regenerate `.github/agents/*.agent.md` content.
That file's prose (Responsibilities, DSDM principles applied, working
style, ...) is hand-authored and its `tools:` frontmatter uses GitHub
Copilot CLI's own generic taxonomy, not DSDM tool names — see
`role_definitions.py`'s module docstring for why a byte-for-byte generator
would destroy real content rather than produce it. What this checks is
purely structural: every role's tools exist, every `.agent.md` a role
claims actually exists with matching frontmatter, and vice versa.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

import yaml

from .role_definitions import ROLE_DEFINITIONS
from ..tools.tool_registry import ToolRegistry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENTS_DIR = REPO_ROOT / ".github" / "agents"


@dataclass(frozen=True)
class ConsistencyIssue:
    role_id: str
    problem: str


def _agent_md_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} does not start with YAML frontmatter")
    end = text.index("\n---", 4)
    return yaml.safe_load(text[4:end]) or {}


def check_role_definitions(tool_registry: ToolRegistry) -> List[ConsistencyIssue]:
    """Return every consistency issue found; empty list means everything's clean."""
    issues: List[ConsistencyIssue] = []

    for role_id, role in ROLE_DEFINITIONS.items():
        if role.role_id != role_id:
            issues.append(ConsistencyIssue(role_id, f"dict key {role_id!r} != role.role_id {role.role_id!r}"))
        if not role.tools:
            issues.append(ConsistencyIssue(role_id, "has no tools"))
        if len(role.tools) != len(set(role.tools)):
            issues.append(ConsistencyIssue(role_id, "has duplicate tool entries"))

        missing_tools = [name for name in role.tools if tool_registry.get(name) is None]
        if missing_tools:
            issues.append(ConsistencyIssue(role_id, f"references unknown tools: {missing_tools}"))

        for target in role.handoffs:
            if target == role_id:
                issues.append(ConsistencyIssue(role_id, "hands off to itself"))
            elif target not in ROLE_DEFINITIONS:
                issues.append(ConsistencyIssue(role_id, f"hands off to unknown role {target!r}"))

        if role.agent_md_name is not None:
            path = AGENTS_DIR / f"{role.agent_md_name}.agent.md"
            if not path.exists():
                issues.append(ConsistencyIssue(role_id, f"agent_md_name={role.agent_md_name!r} but {path} does not exist"))
            else:
                frontmatter = _agent_md_frontmatter(path)
                if frontmatter.get("name") != role.agent_md_name:
                    issues.append(ConsistencyIssue(
                        role_id,
                        f"{path} frontmatter name={frontmatter.get('name')!r} != agent_md_name={role.agent_md_name!r}",
                    ))
        else:
            stray = AGENTS_DIR / f"{role_id}.agent.md"
            if stray.exists():
                issues.append(ConsistencyIssue(role_id, f"{stray} exists but agent_md_name=None"))

    known_agent_md_names: Set[str] = {role.agent_md_name for role in ROLE_DEFINITIONS.values() if role.agent_md_name}
    on_disk = {path.stem.removesuffix(".agent") for path in AGENTS_DIR.glob("*.agent.md")}
    for stray_name in sorted(on_disk - known_agent_md_names):
        issues.append(ConsistencyIssue("<unregistered>", f".github/agents/{stray_name}.agent.md exists but maps to no RoleDefinition"))

    return issues
