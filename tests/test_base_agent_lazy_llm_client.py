"""BaseAgent must not require a configured LLM provider just to be constructed.

Regression test for the fix that makes LLM client construction lazy
(src/agents/base_agent.py). Before this fix, DSDMOrchestrator's
_initialize_agents()/_initialize_design_build_agents() — which always
construct one BaseAgent per phase/role regardless of AGENT_RUNTIME — would
raise ValueError at construction time for any environment without a
legacy hosted-provider API key configured, even when every phase was
routed through pi.dev/a private vLLM endpoint that has nothing to do with
that legacy provider.
"""

import pytest

from src.agents.base_agent import AgentConfig, AgentResult, BaseAgent
from src.agents.feasibility_agent import FeasibilityAgent
from src.tools.tool_registry import ToolRegistry


class _MinimalAgent(BaseAgent):
    """Smallest concrete BaseAgent subclass, for exercising __init__ directly."""

    def _process_output(self, output: str) -> AgentResult:
        return AgentResult(success=True, output=output)


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture(autouse=True)
def _no_llm_env(monkeypatch):
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(var, raising=False)


def test_construction_succeeds_with_zero_llm_env_vars(registry):
    agent = FeasibilityAgent(registry)
    assert agent.name == "Feasibility Agent"
    assert agent.mode is not None


def test_llm_client_is_not_built_at_construction_time(registry):
    agent = FeasibilityAgent(registry)
    assert agent._llm_client is None


def test_llm_client_property_raises_on_first_access_when_unconfigured(registry):
    agent = FeasibilityAgent(registry)
    with pytest.raises(ValueError, match="not properly configured"):
        _ = agent.llm_client


def test_llm_client_property_builds_once_configured(registry, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy-test-key")
    agent = FeasibilityAgent(registry)
    client = agent.llm_client
    assert client is not None
    assert agent.llm_client is client  # cached, not rebuilt


def test_explicit_llm_client_is_used_without_lazy_construction(registry):
    sentinel = object()
    config = AgentConfig(
        name="Minimal",
        description="test double",
        phase="feasibility",
        system_prompt="n/a",
        tools=[],
    )
    agent = _MinimalAgent(config, registry, llm_client=sentinel)
    assert agent.llm_client is sentinel
