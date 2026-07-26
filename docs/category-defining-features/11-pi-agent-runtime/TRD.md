# TRD: Pi Agent Runtime (pi.dev Adoption)

## 1. Technical Summary

Pi Agent Runtime adopts pi.dev's TypeScript packages (`pi-ai`, `pi-agent-core`, `pi-coding-agent`) as the execution engine for every DSDM agent, replacing `BaseAgent.run()` and `GitPinAgentLoop`. The strategy is **bridge-first, incremental**: existing Python tool handlers and business logic are not rewritten — they are exposed to pi.dev through a generic tool-bridge extension. Agent role definitions (system prompt, tools, model, mode) move to a single Python source of truth that generates both the existing `.github/agents/*.agent.md` files and new pi.dev Pi Package configuration. The DSDM orchestrator becomes a thinner coordinator that spawns `pi` sessions (via SDK or `--mode json`/`--mode rpc`) per phase instead of instantiating `BaseAgent` subclasses directly.

## 2. Architecture Fit

Today, `BaseAgent` (`src/agents/base_agent.py`) owns three responsibilities: system prompt assembly, the LLM chat/tool loop, and provider-specific message translation (via `src/llm/providers.py`). `DSDMOrchestrator` (`src/orchestrator/dsdm_orchestrator.py`) instantiates one `BaseAgent` subclass per phase/role, all sharing one `ToolRegistry` (`src/tools/tool_registry.py`), and sequences them per `PHASE_ORDER`. `src/rooms/` consumes `AgentResult` and `ProgressCallback` events as its only integration surface with the agent layer — it does not otherwise depend on `BaseAgent`'s internals.

pi.dev's `pi-ai` + `pi-agent-core` replace the chat/tool loop and provider translation. `ToolRegistry`, the DSDM tool handlers, and `src/rooms/` are retained as-is in Python; the seam between the two stacks is:

1. A **tool bridge** — pi.dev extension that surfaces every `ToolRegistry` tool to the LLM and forwards calls back into Python.
2. A **session runner** — Python module that replaces `DSDMOrchestrator`'s direct `agent.run()` calls with `pi` session invocations, parsing the JSON event stream back into `AgentResult`.
3. A **role-definition generator** — collapses today's duplicated `AgentConfig` / `.agent.md` definitions into one source, emitting both.

`src/rooms/` requires no structural change: it keeps consuming `AgentResult` and progress events, just from a new producer.

## 3. Proposed Components

```text
pi/
├── package.json                       # pinned pi-ai / pi-agent-core / pi-coding-agent versions + shrinkwrap
├── settings.json                      # project-level pi settings (default provider, thinking level)
├── extensions/
│   ├── dsdm-tools-bridge/
│   │   ├── index.ts                   # registerTool() for every tool the Python tool_service exposes
│   │   └── package.json
│   ├── dsdm-approval-gate/
│   │   ├── index.ts                   # tool_call hook enforcing AgentMode (Manual/Automated/Hybrid)
│   │   └── package.json
│   ├── dsdm-room-events/
│   │   ├── index.ts                   # forwards lifecycle events to the session runner's event sink
│   │   └── package.json
│   └── dsdm-mcp-client/
│       ├── index.ts                   # native MCP client, replaces the CLI-shell bridge
│       └── package.json
└── packages/                          # one generated Pi Package per DSDM role
    ├── feasibility/pi.config.json
    ├── product-manager/pi.config.json
    ├── business-study/pi.config.json
    ├── functional-model/pi.config.json
    ├── dev-lead/pi.config.json
    ├── frontend-developer/pi.config.json
    ├── backend-developer/pi.config.json
    ├── automation-tester/pi.config.json
    ├── nfr-tester/pi.config.json
    ├── pen-tester/pi.config.json
    ├── implementation/pi.config.json
    └── devops/pi.config.json

src/
├── agents/
│   └── role_definitions.py            # NEW — single source of truth for every role
├── tools/
│   └── tool_service.py                # NEW — exposes ToolRegistry over localhost HTTP/stdio for dsdm-tools-bridge
├── orchestrator/
│   ├── pi_session_runner.py           # NEW — spawns/streams `pi` sessions, maps events -> AgentResult
│   └── dsdm_orchestrator.py           # MODIFIED — calls pi_session_runner instead of agent.run() per AGENT_RUNTIME flag
└── codegen/
    └── generate_agent_artifacts.py    # NEW — role_definitions.py -> .github/agents/*.agent.md + pi/packages/*/pi.config.json

scripts/
└── generate_agents.sh                 # wraps the codegen entry point; run in CI to fail on drift
```

## 4. Session & Artifact Storage Layout

pi.dev persists sessions as tree-structured JSONL under its own session directory (global `~/.pi/agent/sessions/`, or project-scoped if configured via `pi/settings.json`). DSDM cross-references each phase run's session file from the project's generated artifacts without duplicating pi's storage format:

```text
generated/<project>/
├── .pi-sessions/
│   └── <phase-or-role>-<run-id>.session-ref.json   # {"session_path": "...", "session_id": "...", "phase": "feasibility"}
├── docs/
│   └── ... (unchanged — FEASIBILITY_REPORT.md, PRODUCT_REQUIREMENTS.md, etc.)
└── ... (unchanged)
```

`.session-ref.json` is a small pointer file, not a copy of the session — it lets the Delivery Room dashboard and `room_artifacts.py` link an artifact back to the exact session/turn that produced it, which today is not possible (only the final `AgentResult.output` is kept).

## 5. Core Interfaces

### RoleDefinition (Python, `src/agents/role_definitions.py`)

```python
@dataclass
class RoleDefinition:
    role_id: str                     # e.g. "product-manager", matches .agent.md filename stem
    display_name: str                # "Product Manager"
    phase: str                       # DSDMPhase value, or "design_build_role"
    description: str                 # one-sentence purpose, used by both Copilot discovery and pi package.json
    system_prompt: str                # full system prompt body (markdown)
    tools: list[str]                  # tool names, resolved against ToolRegistry
    model: str | None                 # explicit override, else provider default resolution applies
    default_mode: AgentMode
    default_workflow_mode: WorkflowMode
    handoffs: list[str] = field(default_factory=list)  # role_ids this role can hand off to
```

This becomes the only place a role's prompt/tools/mode is authored. `generate_agent_artifacts.py` renders it into:
- `.github/agents/<role_id>.agent.md` (existing frontmatter + body format, unchanged for Copilot CLI compatibility)
- `pi/packages/<role_id>/pi.config.json` (system prompt file reference, `tools`/`--exclude-tools` allowlist, `model`)

### PiSessionResult (Python, `src/orchestrator/pi_session_runner.py`)

```python
@dataclass
class PiSessionResult:
    success: bool
    output: str
    session_id: str
    session_path: str
    artifacts: dict
    tool_calls: list[dict]           # [{name, input, result, approved_by}]
    requires_next_phase: bool
    next_phase_input: dict | None

def to_agent_result(self) -> AgentResult: ...   # adapter so DSDMOrchestrator's downstream code is unchanged
```

Parsed from `pi`'s `--mode json` event stream: `tool_call` events accumulate into `tool_calls`; the final assistant `message` event becomes `output`; a `session_end` event supplies `session_id`/`session_path`; absence of a clean `session_end` (crash, timeout) maps to `success=False`.

### Tool Bridge Protocol

`dsdm-tools-bridge` (TypeScript) calls `tool_service.py` (Python) over localhost-only HTTP at extension init and at call time:

```text
GET  http://127.0.0.1:<port>/tools
     -> [{ name, description, input_schema, requires_approval, category }, ...]
     (this is exactly ToolRegistry.to_anthropic_format(), already produced today)

POST http://127.0.0.1:<port>/tools/<name>/execute
     body: { arguments: {...}, run_context: { project, phase, role_id, session_id } }
     -> { result: "<string, same shape ToolRegistry.execute() returns today>" }
```

`tool_service.py` wraps the existing, unmodified `ToolRegistry.execute()` — no tool handler changes. The extension registers one pi tool per entry returned by `GET /tools`, using `input_schema` directly as the tool's JSON Schema (pi.dev's tool registration accepts JSON Schema, so no format conversion is required beyond what `ToolRegistry` already produces).

## 6. Tool Interface (New Tools/Extensions)

| Component | Responsibility |
|---|---|
| `dsdm-tools-bridge` | Fetches the tool manifest from `tool_service`, calls `registerTool()` per tool, forwards execution over HTTP |
| `dsdm-approval-gate` | Hooks `tool_call` lifecycle event; for `Manual`/`Hybrid` roles, blocks pending an approval signal (stdin prompt in interactive mode, or a callback into the session runner in headless/JSON/RPC mode) before allowing execution to proceed — reimplements `BaseAgent._should_approve_tool` at the extension layer |
| `dsdm-room-events` | Forwards `tool_call`, `tool_result`, `session_start`, `session_end` events to the session runner's event sink, which drives the same updates `room_progress.py` makes today |
| `dsdm-mcp-client` | Native MCP client; exposes configured MCP servers (from `.github/copilot/mcp-config.json`) as pi tools directly, replacing the `mcp_call_tool`/`mcp_run_command` CLI-shell tools in `src/tools/integrations/mcp_tools.py` |

## 7. Role → Pi Package Mapping

| Role | Current Python class | Current `.agent.md` | New Pi Package | Tool allowlist source |
|---|---|---|---|---|
| Feasibility | `FeasibilityAgent` | `feasibility.agent.md` | `pi/packages/feasibility` | `RoleDefinition.tools` (feasibility category) |
| Product Manager | `ProductManagerAgent` | `product-manager.agent.md` | `pi/packages/product-manager` | prd_trd category |
| Business Study | `BusinessStudyAgent` | `business-study.agent.md` | `pi/packages/business-study` | business_study category |
| Functional Model | `FunctionalModelAgent` | `functional-model.agent.md` | `pi/packages/functional-model` | functional_model category |
| Dev Lead | `DevLeadAgent` | `dev-lead.agent.md` | `pi/packages/dev-lead` | design_build + prd_trd (TRD) |
| Frontend Developer | `FrontendDeveloperAgent` | `frontend-developer.agent.md` | `pi/packages/frontend-developer` | design_build |
| Backend Developer | `BackendDeveloperAgent` | `backend-developer.agent.md` | `pi/packages/backend-developer` | design_build |
| Automation Tester | `AutomationTesterAgent` | `automation-tester.agent.md` | `pi/packages/automation-tester` | design_build + devops (test/coverage) |
| NFR Tester | `NFRTesterAgent` | `nfr-tester.agent.md` | `pi/packages/nfr-tester` | devops (perf/accessibility) |
| Penetration Tester | `PenTesterAgent` | `pen-tester.agent.md` | `pi/packages/pen-tester` | devops (security_check) |
| Implementation | `ImplementationAgent` | `implementation.agent.md` | `pi/packages/implementation` | implementation category |
| DevOps | `DevOpsAgent` | `devops.agent.md` | `pi/packages/devops` | devops (28 tools) |
| Git Pin Coder / Reviewer | `GitPinCodingAgent`, `GitPinReviewAgent` | *(none today)* | `pi/packages/git-pin-coder`, `pi/packages/git-pin-reviewer` | design_build, parallel-tool-call enabled |

Model resolution replaces `get_model_for_phase()`'s Claude-only table: each `RoleDefinition.model` is either an explicit override or `None`, in which case `pi_session_runner` resolves a default from `pi/settings.json`'s configured provider — fixing PAR-PRD-FR-004 by construction, since there is no longer a Claude-specific fallback path.

## 8. Phase Execution Algorithm (`pi_session_runner.run_phase`)

1. Resolve the `RoleDefinition` for the requested phase/role.
2. Check `AGENT_RUNTIME` (global default) and any per-phase override; if `legacy`, delegate to the existing `BaseAgent` path unchanged and return early.
3. Compose the session invocation:
   - SDK path (preferred, avoids per-call subprocess overhead): `createAgentSession({ extensions: [...], systemPrompt, tools: allowlist, model, provider })` from `pi-agent-core`, run from a small long-lived Node process the Python runner talks to over stdio JSON-RPC (`--mode rpc`-equivalent embedding).
   - Subprocess fallback: `pi -e ./pi/packages/<role> --model <resolved> --provider <resolved> --mode json -p "<input>"`.
4. Stream events. For each `tool_call` event, `dsdm-approval-gate` intercepts per the role's `AgentMode` before the call reaches `dsdm-tools-bridge`.
5. For each `tool_result` event, `dsdm-room-events` forwards it to the runner's event sink, which calls the same room-state update functions `room_progress.py` calls today.
6. On `session_end`, assemble `PiSessionResult` from the accumulated events; on stream error/timeout without a clean `session_end`, mark `success=False` and preserve the partial session file for debugging.
7. Call `.to_agent_result()` and return — `DSDMOrchestrator.run_phase()`'s downstream code (merging `next_phase_input`, storing `self.results[phase]`) is otherwise unchanged.

## 9. Agent Integration Notes

### FeasibilityAgent
`feasibility_optimizer.py`'s `_try_quick_feasibility` heuristic fast-path is preserved and runs **before** a pi.dev session is even started — it is cheap, deterministic, and unrelated to the LLM loop, so there is no reason to route it through pi.dev.

### ProductManagerAgent / DevLeadAgent (PRD/TRD phase)
`_run_prd_trd_phase`'s two-step, hardcoded prompt templates move into `RoleDefinition.system_prompt` for the `product-manager` and `dev-lead` roles respectively; the Confluence/Jira sync calls that currently follow (`_sync_prd_to_confluence`, etc.) remain direct Python calls against tool handlers — they do not need to go through an LLM session at all and are unaffected by this migration.

### Design & Build roles
Each role becomes an independent pi.dev session. Sequential team runs (`run_design_build_team`) call `pi_session_runner.run_phase` once per role in order, exactly as today.

### Git Pin Coder / Reviewer
Replaces `GitPinAgentLoop`'s in-process parallel tool executor with two mechanisms pi.dev provides natively:
- **Within a session**, pi.dev's own handling of multi-tool-call LLM turns provides the parallel `file_write` behavior `GitPinCodingAgent`'s system prompt currently has to explicitly request.
- **Across roles**, `GitPinPipeline`'s `ThreadPoolExecutor`+`depends_on` model is replaced by the session runner spawning one OS process per role concurrently (`asyncio.gather` over `pi_session_runner.run_phase` calls), resolving `depends_on` edges before submission exactly as `GitPinPipeline` does today. `ThroughputDashboard` is retained, fed from the same `ThroughputMetrics`-shaped data now sourced from pi.dev's event stream instead of the custom loop.

### Delivery Room
No change to `delivery_room.py`, `room_state.py`, `room_events.py`, `room_dashboard.py`, `room_health.py`, `room_templates.py`, or `room_artifacts.py`. `room_progress.py`'s responsibilities move into `dsdm-room-events` + the session runner's event sink, but the room-state mutation functions themselves are called the same way.

## 10. CLI Commands

Existing `main.py` flags are unchanged in behavior. New maintenance flags:

```bash
# Regenerate .agent.md + Pi Package files from role_definitions.py
python main.py --generate-agents

# Validate the pi.dev install, pinned version, and extension health
python main.py --pi-doctor

# Force a specific phase onto the legacy or pi runtime for this run only
python main.py --phase feasibility --input "..." --agent-runtime pi
python main.py --phase feasibility --input "..." --agent-runtime legacy
```

`AGENT_RUNTIME` env var sets the default; `--agent-runtime` overrides it per invocation.

## 11. Tests

New:
- `tests/test_pi_session_runner.py` — session-to-`AgentResult` mapping, including crash/partial-stream handling.
- `tests/test_tools_bridge.py` — `tool_service.py` manifest and execute endpoints against the real `ToolRegistry`, including error propagation.
- `tests/test_role_definitions_codegen.py` — asserts generated `.agent.md`/`pi.config.json` files exactly match what `generate_agent_artifacts.py` would produce from the current `role_definitions.py` (drift guard, run in CI).
- `tests/test_approval_gate.py` — Manual/Automated/Hybrid behavior parity between the legacy `_should_approve_tool` and the new extension-level gate, for the same tool/mode matrix.

Regression (existing, must continue passing against the pi.dev-backed path once a role is `migrated`):
- `tests/test_delivery_room.py`
- `tests/test_mcp_tools.py`

## 12. Migration Path

Mirrors the PRD's phased rollout, with the `AGENT_RUNTIME` flag providing the technical rollback mechanism at every step:

1. **Spike** — Feasibility phase only, hand-wired minimal bridge, output diffed against legacy.
2. **Tools Bridge** — `dsdm-tools-bridge` ships and is exercised by the spike and by manual `pi` sessions, but no phase defaults to it yet.
3. **Unified Role Definitions** — `role_definitions.py` + generator land; CI enforces no drift against committed `.agent.md` files.
4. **Runtime Cutover** — phases/roles move `legacy` → `piloted` → `migrated` one at a time, lowest-iteration-cap phases first.
5. **Git Pin Replacement** — process-level concurrent sessions replace `GitPinAgentLoop`/`GitPinPipeline`.
6. **Native MCP + Session Tree** — `dsdm-mcp-client` replaces the CLI-shell bridge; `.pi-sessions/` pointers land in generated project output.
7. **Retirement** — delete `base_agent.py`'s loop, `git_pin_agent_core.py`, `orchestrator_extension.py`, and the OpenAI/Gemini/Ollama client code in `src/llm/providers.py` once every role has been `migrated` and stable for an agreed bake-in period.

## 13. Security and Safety

- pi.dev ships no built-in permission system by design (isolation is expected via containers/sandboxing at the deployment layer); DSDM's per-tool `requires_approval` model must be reconstructed explicitly via `dsdm-approval-gate` — it must not be assumed to exist by default.
- `tool_service.py` binds to `127.0.0.1` only, on an ephemeral port passed to the extension via environment variable at session start; it must never accept connections from outside the local machine and must never be exposed through the Delivery Room's future web UI (per the existing "no real-time web UI before the CLI/model stabilizes" non-goal in the Autonomous Delivery Room PRD).
- Secrets (`JIRA_API_TOKEN`, `CONFLUENCE_API_TOKEN`, LLM API keys) remain in the Python process's environment and are never passed into TypeScript extension code, logged in pi.dev session JSONL, or included in tool-call arguments/results that get persisted to session files.
- `pi/package.json` adopts pi-mono's own supply-chain practices — exact-version pinning and a committed shrinkwrap/lockfile — mirrored for the DSDM extension workspace, with lockfile changes reviewed like any other dependency bump.
- The MCP CLI-shell bridge's existing dry-run-by-default / `MCP_EXECUTE=1` safety gate is preserved conceptually in `dsdm-mcp-client`: destructive MCP tool calls remain `requires_approval` and route through `dsdm-approval-gate` like any other tool.

## 14. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| PAR-TRD-NFR-001 | Tool-bridge round-trip overhead vs. today's in-process `ToolRegistry.execute()` call | < 50ms p95 added latency per tool call on localhost |
| PAR-TRD-NFR-002 | Session-runner availability of a clean `AgentResult` on process crash or timeout | 100% — partial state always recoverable from the session file, never a silent hang |
| PAR-TRD-NFR-003 | Design & Build parallel throughput (tools/sec) after migration vs. `ThroughputMetrics` baseline | ≥ 100% of legacy `GitPinPipeline` baseline |
| PAR-TRD-NFR-004 | Generated `.agent.md`/Pi Package drift | 0 — CI fails the build if generated output differs from committed files |
| PAR-TRD-NFR-005 | Provider switch correctness | 100% of phases request the model/provider configured in `pi/settings.json` or the phase override, never a hardcoded fallback |

- Given the tool bridge is under load from a parallel Design & Build run, when 8 roles call tools concurrently, then `tool_service.py` serves all requests without cross-request data leakage between roles (each request carries and is scoped by `run_context`).
- Given a session crashes mid-tool-call, when the operator inspects the session file, then the last successfully completed tool call and its result are present and readable.

## 15. Implementation Plan

### Phase 1
- `tool_service.py`, `dsdm-tools-bridge` extension, spike harness for Feasibility.
- `tests/test_tools_bridge.py`.

### Phase 2
- `role_definitions.py`, `generate_agent_artifacts.py`, CI drift check.
- `tests/test_role_definitions_codegen.py`.

### Phase 3
- `pi_session_runner.py`, `dsdm-approval-gate`, `dsdm-room-events` extensions, `AGENT_RUNTIME` flag wiring into `dsdm_orchestrator.py`.
- `tests/test_pi_session_runner.py`, `tests/test_approval_gate.py`.
- Cut over phases one at a time, starting with Feasibility.

### Phase 4
- Process-level concurrent session runner for Git Pin roles; retire `GitPinAgentLoop`/`GitPinPipeline` internals while keeping `ThroughputDashboard`'s external shape.

### Phase 5
- `dsdm-mcp-client` extension; `.pi-sessions/` artifact cross-linking; retire the `mcp_call_tool`/`mcp_run_command` CLI-shell path in `src/tools/integrations/mcp_tools.py`.

### Phase 6
- Delete `base_agent.py`'s loop, `git_pin_agent_core.py`, `orchestrator_extension.py`, and non-Anthropic clients in `src/llm/providers.py`; update `AGENTS.md` and `.github/instructions/*` to reflect the retired paths.

## 16. Phase 1 Implementation Notes (verified)

Phase 1 (`tool_service.py`, `dsdm-tools-bridge`, spike harness) has been implemented and verified against the real `pi` CLI, not just written against documentation:

- `src/tools/tool_service.py` — localhost-only `ThreadingHTTPServer` bridge (`GET /tools`, `POST /tools/<name>/execute`, `GET /health`), zero new dependencies. 13 tests in `tests/test_tools_bridge.py`, all passing.
- `pi/` — npm workspace pinning `@mariozechner/pi-coding-agent@0.73.1`; `pi/extensions/dsdm-tools-bridge` fetches the manifest at extension-init time and dynamically calls `pi.registerTool()` once per tool, converting each JSON-Schema `input_schema` into a `typebox` parameter schema (including `StringEnum` for string enums, per pi.dev's Google-provider-compatibility requirement).
- **Live verification**: with the bridge unreachable, `pi` correctly reports `Failed to load extension: dsdm-tools-bridge: could not reach the Python tool service...`. With the bridge running the full 79-tool DSDM registry, the same invocation loads cleanly and proceeds all the way to a real Anthropic API call (which fails only on the deliberately-invalid API key used for the test, with a normal `401 authentication_error` — i.e. every one of the 79 tools' converted schemas was accepted by pi's real tool registration, not just plausible-looking code).
- `scripts/spike_feasibility_bridge.py` — Phase 0 spike harness; `--check` (free, no LLM calls) verifies the environment end-to-end and passes in this repo; `--live` runs the actual legacy-vs-pi.dev Feasibility comparison but requires a real `ANTHROPIC_API_KEY`, which was not available in the environment this was built in, so the live comparison itself is still outstanding.
- **Correction to README.md**: while wiring the spike harness's tool allowlist to `FeasibilityAgent`'s real `AgentConfig.tools`, two tools README.md lists under "Feasibility Phase" (`estimate_resources`, `check_dsdm_suitability`) turned out not to exist in `ToolRegistry` at all — the README's tool inventory is aspirational/stale in places and should not be trusted as ground truth for role definitions in Phase 2.
- **Dependency note**: `npm install` reports `@mariozechner/pi-coding-agent` (and its sibling `pi-ai`/`pi-agent-core`/`pi-tui` packages) as deprecated in favor of `@earendil-works/pi-coding-agent` — the project appears to have moved npm scope after this TRD was drafted. Before Phase 2, re-pin `pi/package.json` to whichever scope is current upstream; this is a live instance of the "pinned version and upgrade process" risk called out in the PRD.
