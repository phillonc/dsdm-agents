"""Drift guard for src/agents/role_definitions.py.

Phase 2 of the Pi Agent Runtime migration (PAR-PRD-FR-002). These tests
don't regenerate anything — they check that the single source of truth
(ROLE_DEFINITIONS) stays internally consistent and stays honest about its
relationship to `.github/agents/*.agent.md`, without asserting a
byte-for-byte comparison that would be meaningless (the .agent.md prose and
its `tools:` frontmatter use a different vocabulary than DSDM tool names;
see role_definitions.py's module docstring).
"""

from pathlib import Path

import yaml

from src.agents.role_definitions import ROLE_DEFINITIONS, RoleDefinition, get_role
from src.tools.dsdm_tools import create_dsdm_tool_registry

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = REPO_ROOT / ".github" / "agents"


def _full_registry():
    # include everything so no role's tools are unfairly flagged missing.
    return create_dsdm_tool_registry(include_jira=True, include_confluence=True, include_devops=True)


def test_at_least_the_known_roles_are_registered():
    assert len(ROLE_DEFINITIONS) >= 15


def test_role_ids_are_unique_and_match_dict_keys():
    for role_id, role in ROLE_DEFINITIONS.items():
        assert role.role_id == role_id


def test_every_role_has_at_least_one_tool():
    for role_id, role in ROLE_DEFINITIONS.items():
        assert role.tools, f"{role_id} has no tools"


def test_every_tool_exists_in_the_dsdm_tool_registry():
    registry = _full_registry()
    missing = {}
    for role_id, role in ROLE_DEFINITIONS.items():
        gone = [name for name in role.tools if registry.get(name) is None]
        if gone:
            missing[role_id] = gone
    assert not missing, f"Roles reference tools that don't exist in ToolRegistry: {missing}"


def test_every_tool_list_has_no_duplicates():
    for role_id, role in ROLE_DEFINITIONS.items():
        assert len(role.tools) == len(set(role.tools)), f"{role_id} has duplicate tool entries"


def test_get_role_raises_clear_error_for_unknown_id():
    try:
        get_role("does-not-exist")
    except KeyError as exc:
        assert "does-not-exist" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_get_role_returns_the_registered_definition():
    role = get_role("feasibility")
    assert isinstance(role, RoleDefinition)
    assert role.phase == "feasibility"


# -- .github/agents/*.agent.md structural drift guard -------------------------
def _agent_md_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} does not start with YAML frontmatter"
    end = text.index("\n---", 4)
    return yaml.safe_load(text[4:end])


def test_roles_with_agent_md_name_have_a_real_file_with_matching_name():
    for role_id, role in ROLE_DEFINITIONS.items():
        if role.agent_md_name is None:
            continue
        path = AGENTS_DIR / f"{role.agent_md_name}.agent.md"
        assert path.exists(), f"{role_id}: no such file {path}"
        frontmatter = _agent_md_frontmatter(path)
        assert frontmatter.get("name") == role.agent_md_name, (
            f"{role_id}: {path} frontmatter name={frontmatter.get('name')!r} "
            f"!= agent_md_name={role.agent_md_name!r}"
        )


def test_roles_without_agent_md_name_have_no_stray_file():
    # Roles intentionally without a Copilot CLI counterpart (Git Pin roles) shouldn't
    # silently gain one without role_definitions.py being updated to know about it.
    for role_id, role in ROLE_DEFINITIONS.items():
        if role.agent_md_name is not None:
            continue
        stray = AGENTS_DIR / f"{role_id}.agent.md"
        assert not stray.exists(), (
            f"{role_id}: {stray} now exists but role_definitions.py still says "
            "agent_md_name=None — update the RoleDefinition."
        )


def test_every_agent_md_file_maps_back_to_a_role():
    # The inverse of the above: every .agent.md on disk should be reachable from
    # ROLE_DEFINITIONS, so a new Copilot CLI role doesn't go un-registered here.
    known_agent_md_names = {role.agent_md_name for role in ROLE_DEFINITIONS.values() if role.agent_md_name}
    on_disk = {path.stem.removesuffix(".agent") for path in AGENTS_DIR.glob("*.agent.md")}
    assert on_disk <= known_agent_md_names, f"Unregistered .agent.md files: {on_disk - known_agent_md_names}"


# -- handoffs -------------------------------------------------------------------
def test_handoffs_reference_real_roles():
    for role_id, role in ROLE_DEFINITIONS.items():
        for target in role.handoffs:
            assert target in ROLE_DEFINITIONS, f"{role_id} hands off to unknown role {target!r}"


def test_no_role_hands_off_to_itself():
    for role_id, role in ROLE_DEFINITIONS.items():
        assert role_id not in role.handoffs
