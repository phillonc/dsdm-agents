"""Tests for the AGENT_RUNTIME=legacy|pi cutover in DSDMOrchestrator.

Phase 3 of the Pi Agent Runtime migration (PAR-PRD-FR-012). Constructing a
full DSDMOrchestrator eagerly builds every legacy agent, each of which
builds a real LLM client — that only needs a non-empty API key string to
construct (LLMConfig.is_configured() never validates it), so dummy keys are
enough here; the pi-runtime path never touches the network at all, it talks
to a fake `pi --mode rpc` process (tests/fake_pi_rpc.py), same as
test_pi_session_runner.py.
"""

from pathlib import Path

import pytest

import src.orchestrator.pi_session_runner as runner
from src.orchestrator import DSDMOrchestrator, DSDMPhase

FAKE_PI = Path(__file__).resolve().parent / "fake_pi_rpc.py"


@pytest.fixture(autouse=True)
def _fake_pi_binary(monkeypatch):
    monkeypatch.setattr(runner, "PI_BIN", FAKE_PI)


@pytest.fixture(autouse=True)
def _dummy_llm_keys(monkeypatch):
    # FrontendDeveloperAgent hardcodes llm_provider=LLMProvider.GEMINI (pre-existing,
    # unrelated to this change); every other agent defaults to Anthropic. Both need a
    # non-empty key to construct, even though the pi-runtime path never calls out.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy-test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini-key")
    monkeypatch.delenv("AGENT_RUNTIME", raising=False)


@pytest.fixture
def orchestrator_kwargs():
    return dict(show_progress=False, include_devops=False, include_jira=False, include_confluence=False, include_mcp=False)


def _new_orchestrator(kwargs, **overrides):
    return DSDMOrchestrator(**{**kwargs, **overrides})


# -- agent_runtime resolution -----------------------------------------------------
def test_default_agent_runtime_is_legacy(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs)
    assert orch.agent_runtime == "legacy"
    orch.shutdown_pi_bridge()


def test_explicit_constructor_arg_wins(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    assert orch.agent_runtime == "pi"
    orch.shutdown_pi_bridge()


def test_env_var_sets_runtime_when_no_constructor_arg(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME", "pi")
    orch = _new_orchestrator(orchestrator_kwargs)
    assert orch.agent_runtime == "pi"
    orch.shutdown_pi_bridge()


def test_constructor_arg_overrides_env_var(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME", "pi")
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="legacy")
    assert orch.agent_runtime == "legacy"
    orch.shutdown_pi_bridge()


def test_unrecognized_value_falls_back_to_legacy(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="not-a-real-runtime")
    assert orch.agent_runtime == "legacy"
    orch.shutdown_pi_bridge()


# -- phase eligibility --------------------------------------------------------------
def test_pi_runtime_covers_the_six_mapped_phases(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    for phase in (
        DSDMPhase.FEASIBILITY,
        DSDMPhase.BUSINESS_STUDY,
        DSDMPhase.FUNCTIONAL_MODEL,
        DSDMPhase.DESIGN_BUILD,
        DSDMPhase.IMPLEMENTATION,
        DSDMPhase.DEVOPS,
    ):
        assert orch._use_pi_runtime(phase) is True, phase
    orch.shutdown_pi_bridge()


def test_prd_trd_never_routes_through_pi(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    assert orch._use_pi_runtime(DSDMPhase.PRD_TRD) is False
    orch.shutdown_pi_bridge()


def test_legacy_runtime_never_routes_through_pi(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="legacy")
    assert orch._use_pi_runtime(DSDMPhase.FEASIBILITY) is False
    orch.shutdown_pi_bridge()


# -- end-to-end run_phase() through the fake pi subprocess --------------------------
def test_run_phase_via_pi_returns_agent_result_and_caches_it(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("FAKE_PI_SCENARIO", "happy_path")
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    try:
        result = orch.run_phase(DSDMPhase.FEASIBILITY, "Build a widget", skip_fast_path=True)
        assert result.success is True
        assert result.output == "Analysis complete."
        assert orch.results[DSDMPhase.FEASIBILITY] is result
        assert orch.current_phase is None  # cleared after the run, same as the legacy path
    finally:
        orch.shutdown_pi_bridge()


def test_run_phase_via_pi_reuses_the_same_bridge_across_phases(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("FAKE_PI_SCENARIO", "happy_path")
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    try:
        orch.run_phase(DSDMPhase.FEASIBILITY, "Build a widget", skip_fast_path=True)
        bridge_1 = orch._pi_bridge
        assert bridge_1 is not None

        orch.run_phase(DSDMPhase.BUSINESS_STUDY, "Build a widget")
        bridge_2 = orch._pi_bridge

        assert bridge_1 is bridge_2
    finally:
        orch.shutdown_pi_bridge()


def test_run_phase_via_pi_surfaces_extension_load_error(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("FAKE_PI_SCENARIO", "extension_load_error")
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    try:
        result = orch.run_phase(DSDMPhase.FEASIBILITY, "Build a widget", skip_fast_path=True)
        assert result.success is False
    finally:
        orch.shutdown_pi_bridge()


def test_shutdown_pi_bridge_is_idempotent(orchestrator_kwargs, monkeypatch):
    monkeypatch.setenv("FAKE_PI_SCENARIO", "happy_path")
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="pi")
    orch.run_phase(DSDMPhase.FEASIBILITY, "Build a widget", skip_fast_path=True)
    orch.shutdown_pi_bridge()
    assert orch._pi_bridge is None
    orch.shutdown_pi_bridge()  # must not raise
    assert orch._pi_bridge is None


def test_shutdown_pi_bridge_before_any_pi_use_is_a_noop(orchestrator_kwargs):
    orch = _new_orchestrator(orchestrator_kwargs, agent_runtime="legacy")
    orch.shutdown_pi_bridge()  # never started a bridge; must not raise
    assert orch._pi_bridge is None
