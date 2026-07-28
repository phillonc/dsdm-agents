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
- When a role is configured for the private vLLM provider (PAR-PRD-FR-014/015/016, section 22), there is **no automatic fallback** to a hosted provider on connection failure — `_resolve_provider()` either resolves to `dsdm-vllm` or the session fails outright. Silently falling back to a public provider on a private-endpoint failure would be a data-exfiltration bug, not a resilience feature.
- The generated per-run `models.json` (section 22) contains the private endpoint URL and, if configured, a bearer token. It is written to a per-run temp directory scoped to that one `pi` subprocess invocation and is never committed, logged, or reused across a different role's run.

## 14. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| PAR-TRD-NFR-001 | Tool-bridge round-trip overhead vs. today's in-process `ToolRegistry.execute()` call | < 50ms p95 added latency per tool call on localhost |
| PAR-TRD-NFR-002 | Session-runner availability of a clean `AgentResult` on process crash or timeout | 100% — partial state always recoverable from the session file, never a silent hang |
| PAR-TRD-NFR-003 | Design & Build parallel throughput (tools/sec) after migration vs. `ThroughputMetrics` baseline | ≥ 100% of legacy `GitPinPipeline` baseline |
| PAR-TRD-NFR-004 | Generated `.agent.md`/Pi Package drift | 0 — CI fails the build if generated output differs from committed files |
| PAR-TRD-NFR-005 | Provider switch correctness | 100% of phases request the model/provider configured in `pi/settings.json` or the phase override, never a hardcoded fallback |
| PAR-TRD-NFR-006 | Private-endpoint isolation for vLLM-configured roles | 0 outbound requests to any public provider domain when `LLM_PROVIDER=vllm`; connection failure surfaces as a failed phase, never a fallback request elsewhere |

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
- `pi/` — npm workspace pinning `@earendil-works/pi-coding-agent@0.82.1`; `pi/extensions/dsdm-tools-bridge` fetches the manifest at extension-init time and dynamically calls `pi.registerTool()` once per tool, converting each JSON-Schema `input_schema` into a `typebox` parameter schema (including `StringEnum` for string enums, per pi.dev's Google-provider-compatibility requirement).
- **Live verification**: with the bridge unreachable, `pi` correctly reports `Failed to load extension: dsdm-tools-bridge: could not reach the Python tool service...`. With the bridge running the full 79-tool DSDM registry, the same invocation loads cleanly and proceeds all the way to a real Anthropic API call (which fails only on the deliberately-invalid API key used for the test, with a normal `401 authentication_error` — i.e. every one of the 79 tools' converted schemas was accepted by pi's real tool registration, not just plausible-looking code).
- `scripts/spike_feasibility_bridge.py` — Phase 0 spike harness; `--check` (free, no LLM calls) verifies the environment end-to-end and passes in this repo; `--live` runs the actual legacy-vs-pi.dev Feasibility comparison but requires a real `ANTHROPIC_API_KEY`, which was not available in the environment this was built in, so the live comparison itself is still outstanding.
- **Corrected README.md and TECHNICAL_REQUIREMENTS.md**: both listed two Feasibility tools (`estimate_resources`, `check_dsdm_suitability`) that don't exist in `ToolRegistry` at all. Fixed to match `FeasibilityAgent`'s real `AgentConfig.tools` list. Their tool inventories elsewhere in these two documents have not been independently re-verified and should not yet be trusted as ground truth for role definitions in Phase 2 without the same check.
- **Re-pinned to `@earendil-works/*`**: `@mariozechner/pi-coding-agent`/`pi-ai`/`pi-agent-core`/`pi-tui` are deprecated upstream in favor of the `@earendil-works` scope (same maintainer, same API — the extension code and behavior are unchanged). `pi/package.json` and `pi/extensions/dsdm-tools-bridge/package.json` now pin `@earendil-works/pi-coding-agent@0.82.1` / `pi-ai@0.82.1`, and re-verified live against the same load/unload test above with identical results.
- **Known issue, not yet resolved**: `npm audit` reports one high-severity DoS advisory (`GHSA-mh99-v99m-4gvg`, unbounded regex expansion) in `brace-expansion@5.0.7`, pulled in transitively via `@earendil-works/pi-coding-agent → minimatch`, used only by pi's own CLI internals (not reachable through `dsdm-tools-bridge` or `tool_service.py`). A `package.json` `overrides` pin to the fixed `5.0.8` did not take effect in this environment across several attempts (`npm ls` labels the edge `overridden` but still installs `5.0.7`) — left unpinned rather than shipping a non-functional override that would misrepresent the fix as applied. Re-check with `npm audit` once `pi-coding-agent` bumps its own `minimatch`/`brace-expansion` dependency, or retry the override outside this sandbox's npm proxy.

## 17. Phase 3 Started Early: `dsdm-approval-gate` (verified)

`PAR-PRD-FR-005` (preserve Manual/Automated/Hybrid tool-approval semantics) was identified as an unenforced gap after Phase 1 shipped: `dsdm-tools-bridge` executed every tool call unconditionally, with no equivalent to `BaseAgent._should_approve_tool`. Rather than leave a Must-have requirement unmet while the rest of Phase 3 (`pi_session_runner.py`, orchestrator cutover) is still unbuilt, `dsdm-approval-gate` (originally scoped for Phase 3, see section 6) was pulled forward and implemented on its own, since it only depends on the Phase 1 bridge, not on the session runner.

- `pi/extensions/dsdm-approval-gate/index.ts` hooks pi's `tool_call` lifecycle event. Mode comes from `DSDM_AGENT_MODE` (`automated` default / `manual` / `hybrid`); `automated` registers no handler at all — zero overhead, matching `AgentMode.AUTOMATED` always returning `True`. `hybrid` gates only tools whose bridge manifest entry has `requires_approval: true`; `manual` gates every DSDM-bridged tool. Only tools present in the manifest are touched — built-in pi tools (`read`/`bash`/`edit`/`write`/...) are untouched, since `BaseAgent` never saw those either.
- Approval channel: `ctx.ui.confirm()` when `ctx.hasUI` is true (interactive and RPC mode, confirmed via pi's own docs). In headless print/JSON mode, there is no synchronous human channel yet — it **fails closed** (blocks), exactly matching `BaseAgent`'s behavior when `approval_callback` is `None` (`base_agent.py:244`, `:249`). A headless approval channel is Phase 3's `pi_session_runner.py` to build, not this extension.
- `pi/extensions/dsdm-approval-gate/index.test.ts` — 10 tests, run via `node --experimental-strip-types` (no LLM, no pi CLI, no jiti needed): the pure mode/requires_approval decision table, handler wiring for automated (no-op), hybrid, and manual modes, non-DSDM tool passthrough, and both interactive-confirm branches (approve/decline) with an exact legacy-parity message check on decline.
- **Live verification**: with both `dsdm-tools-bridge` and `dsdm-approval-gate` loaded against the real bridge, `DSDM_AGENT_MODE` unset (automated) and `hybrid` both load cleanly and proceed to a real (auth-rejected) Anthropic call — proving the gate's manifest fetch and `tool_call` registration work against the live 79-tool registry, not just the stub harness. With a broken bridge URL and `DSDM_AGENT_MODE=manual`, `pi` reports the gate's own `Failed to load extension: dsdm-approval-gate: could not reach...` error, distinct from `dsdm-tools-bridge`'s equivalent message.
- **Not yet exercised**: an actual blocked tool call during a live LLM turn — that requires a real `ANTHROPIC_API_KEY` to get the model to attempt a gated tool, which is unavailable in this environment (same gap noted in section 16 for the spike's `--live` mode).

## 18. Self-Consistency Fix: `FeasibilityAgent.FEASIBILITY_TOOLS`

`scripts/spike_feasibility_bridge.py` originally hardcoded its own copy of `FeasibilityAgent`'s tool list — the exact "two sources that can drift" problem this migration exists to eliminate (see section 9's role → Pi Package duplication risk), reproduced inside the migration's own tooling. Fixed by hoisting the list out of `FeasibilityAgent.__init__` into a module-level `FEASIBILITY_TOOLS` constant in `src/agents/feasibility_agent.py` (mirroring the existing `FEASIBILITY_SYSTEM_PROMPT` constant), which the harness now imports directly. The harness derives its narrower `SPIKE_SCOPE_TOOLS` (Jira/Confluence excluded by design) by filtering `FEASIBILITY_TOOLS` against what's actually registered in its own scoped `ToolRegistry`, rather than guessing from name prefixes — an initial `jira_`/`confluence_` prefix-based filter missed `sync_work_item_status`, caught by re-running `--check` after the fix.

## 19. Design Corrections: Sections 3 and 6 Don't Match Real pi.dev Primitives

Building Phase 2/3 against pi.dev's actual docs (`docs/extensions.md`, `docs/json.md`, `docs/rpc.md`, `docs/packages.md` from the installed `@earendil-works/pi-coding-agent` package) surfaced two places where this TRD's original speculative design (written before Phase 1 existed) doesn't correspond to anything pi.dev actually has:

- **`pi/packages/<role>/pi.config.json` (section 3) is not a real pi.dev concept.** "Pi Packages" bundle *extensions, skills, prompt templates, and themes* — there is no persona/role bundle format. A "role" in pi.dev is just a specific CLI invocation: `--system-prompt`, `--tools`, `--model`, `--provider`. Phase 2/3 do not create `pi/packages/`; `pi_session_runner.py` (section 22) builds the invocation directly from a `RoleDefinition`, the same way `scripts/spike_feasibility_bridge.py` already did for Feasibility alone.
- **`dsdm-room-events` (section 6/7) is not needed as a separate TypeScript extension.** `pi --mode rpc` already streams `tool_execution_start` / `tool_execution_end` / `agent_end` as JSON lines on stdout. `pi_session_runner.py` parses that stream directly into the same `ProgressCallback`/`ProgressInfo` shape `BaseAgent` already produces, so `src/rooms/room_progress.py` needs zero changes to keep working. No extension, no indirection.
- **`--mode json`, not `--mode rpc`, was the wrong choice for section 8's "Phase Execution Algorithm."** JSON mode is one-shot and leaves `ctx.hasUI` false for the entire run — under JSON mode, `dsdm-approval-gate` would *always* fail closed, with no way to actually grant an approval headlessly. pi.dev's own RPC docs confirm `ctx.hasUI` is `true` in RPC mode specifically, because dialog methods (`ctx.ui.confirm()`, etc.) work via a documented "extension UI protocol": an `extension_ui_request` on stdout that the client answers with an `extension_ui_response` on stdin. `pi_session_runner.py` uses `--mode rpc` and implements exactly this round-trip, wired to the same `approval_callback` shape `BaseAgent`/`DSDMOrchestrator` already use for Rich's `Confirm.ask`.

These are corrected in place in this document's earlier sections' *intent* (tool bridge, approval gate, room integration, phase execution) but section 3's file tree and section 8's mode choice are now historical/superseded by what's described in sections 20–22 below — kept rather than rewritten so the record of what was originally proposed vs. what pi.dev actually supports stays visible.

## 20. Phase 2 (verified): `src/agents/role_definitions.py`

`RoleDefinition` (PAR-PRD-FR-002) is built and populated for all 15 DSDM roles (6 phase agents, 6 Design & Build sub-roles, the phase-level `DesignBuildAgent`, and the 2 Git Pin roles) — the design-build sub-roles and Git Pin roles all use `phase="design_build"`, matching their real `AgentConfig.phase` value; PRD_TRD's Product Manager role is included as `product-manager`.

- **No content was re-typed.** Every `RoleDefinition.system_prompt`/`.tools` value is imported from the same module-level constant each agent class's own `AgentConfig(...)` call already uses. Getting there required a mechanical refactor across all 14 remaining agent modules (Feasibility already had this shape — see section 18): each module's inline `tools=[...]` list was hoisted to a `<ROLE>_TOOLS` constant and the `AgentConfig(tools=...)` call now references it — pure extraction, verified as a pure extraction by running the full test suite before and after (identical pass count) and by importing every hoisted constant directly and checking tool counts against the original inline lists.
- **`tests/test_role_definitions.py`** (12 tests) is the drift guard PAR-PRD-FR-002 calls for, scoped honestly: it does **not** attempt a byte-for-byte comparison against `.github/agents/*.agent.md` (that file's `tools:` frontmatter is GitHub Copilot CLI's own generic taxonomy — `read`/`write`/`edit`/`search`/`execute` — not DSDM tool names, and its `description:` prose is independently hand-authored, richer, and never meant to match `AgentConfig.description` word-for-word). What it does check, and what actually caught real bugs while being built:
  - Every tool every role references resolves in the real `ToolRegistry` (`include_jira=True, include_confluence=True, include_devops=True`) — passes today for all 15 roles, meaning the mechanical hoist above didn't introduce a single typo across ~250 tool-name entries.
  - Every role with an `agent_md_name` has a real `.github/agents/<name>.agent.md` file whose frontmatter `name:` matches; every `.agent.md` file on disk maps back to a registered role (would catch a new Copilot CLI role landing without a `RoleDefinition`, or vice versa).
  - `dev-lead` and `design-build`'s `handoffs` all reference real role_ids; no role hands off to itself.
- **Found by building this, not by inspection**: `ImplementationAgent.__init__`'s own default is `AgentMode.HYBRID`, not `MANUAL` as README.md and `main.py`'s CLI override imply — `RoleDefinition.implementation.default_mode` is set to `HYBRID` to match the class's real default, with a comment explaining the discrepancy is a deployment-policy override layered on top by `main.py`, not a second definition of the role's intrinsic default.

## 21. Phase 3 (verified, partial): `pi_session_runner.py` and the `AGENT_RUNTIME` cutover

`src/orchestrator/pi_session_runner.py` implements PAR-PRD-FR-003: spawns `pi --mode rpc` with `dsdm-tools-bridge` and `dsdm-approval-gate` loaded, drives the RPC protocol, and returns a `PiSessionResult` with a `.to_agent_result()` adapter so `DSDMOrchestrator` can use it as a drop-in replacement for `agent.run()`.

**A real, load-bearing bug was found and fixed while building the test harness, not by inspection.** The initial `_JsonlReader` implementation read the child's stdout with `stream.read(4096)`. `io.BufferedReader.read(size)` loops the underlying raw read until it accumulates `size` bytes *or hits EOF* — it does not return early just because a partial chunk is all that is currently available. This is harmless for a child that emits everything and exits (the retry loop's second read hits EOF immediately and returns what's buffered) but is a **guaranteed deadlock** for a child that pauses mid-stream without exiting — exactly what happens waiting for an `extension_ui_response`: the parent blocks forever trying to fill a 4096-byte buffer that will never arrive, while the child blocks forever waiting for a reply the parent never sends because it never returned from `read()`. Confirmed by direct reproduction (a hand-rolled client using the same `cmd`/`env` construction, with `FAKE_PI_DEBUG` tracing showing the child had already flushed two events and was correctly blocked waiting for the response — the parent just never read them) and fixed by switching to `stream.read1(4096)`, which makes at most one underlying read call and returns whatever is available, matching the streaming semantics the protocol actually needs (and what the Node.js reference client's chunk-based `stream.on("data", ...)` naturally does). Every test in `tests/test_pi_session_runner.py` that exercises the confirm round-trip is a regression test for this specific bug.
- **`tests/fake_pi_rpc.py`** — a small script that speaks the documented subset of the RPC protocol (reads a `prompt` command, emits `tool_execution_start`/`extension_ui_request`/`tool_execution_end`/`agent_end`, and for confirm scenarios genuinely blocks on stdin waiting for the `extension_ui_response`) stands in for the real `pi` binary via `monkeypatch.setattr(runner, "PI_BIN", FAKE_PI)`. This gives real subprocess-based integration coverage of the full event loop — including a real confirm request/response round trip — without needing the actual `pi` binary or LLM credentials.
- **`tests/test_pi_session_runner.py`** (18 tests): JSONL framing (`_JsonlReader`, including CRLF and chunked-read edge cases), `_extract_text`/`_extract_last_assistant_text`, `_resolve_provider` (including the `gemini` → `google` pi.dev naming mismatch), the missing-binary error path, the happy path, the confirm-approve and confirm-deny round trips, denial-by-default when no `approval_callback` is supplied, `extension_error` events surfacing as failure, and `ProgressCallback` events firing in the right order.
- **`DSDMOrchestrator` cutover**: `AGENT_RUNTIME=legacy|pi` (constructor arg `agent_runtime=` takes precedence over the env var; anything unrecognized falls back to `legacy`) now actually routes `run_phase()` for `feasibility`, `business_study`, `functional_model`, `design_build`, `implementation`, and `devops` through `pi_session_runner.run_role()` instead of `agent.run()` — a single `if self._use_pi_runtime(phase): ... else: ...` branch, with every surrounding line (banner display, context merging, result caching, feasibility-cache write, formatted output) untouched. `PRD_TRD` is explicitly excluded and always runs on the legacy path — `_run_prd_trd_phase`'s hardcoded two-agent (Product Manager + Dev Lead) sub-workflow hasn't been ported. A tool bridge is started lazily on first pi-routed phase and reused for the orchestrator's lifetime (`_ensure_pi_bridge`/`shutdown_pi_bridge`), backed by the same `self.tool_registry` every legacy agent already shares.
- **`tests/test_orchestrator_pi_runtime.py`** (13 tests, against the fake pi process): runtime resolution precedence (constructor > env var > default `legacy` > invalid-value fallback), phase eligibility (the six mapped phases true, `PRD_TRD` and `legacy` mode false), a full `run_phase()` round trip returning a correctly-populated `AgentResult` and caching it into `self.results`, bridge reuse across two consecutive phases (same object, not restarted), extension-load failure surfacing as `success=False`, and idempotent shutdown.
- **Live-verified separately**: constructing a real `DSDMOrchestrator` and calling `run_phase(FEASIBILITY, ..., agent_runtime="pi")` against the fake pi process end-to-end, both via explicit `agent_runtime="pi"` and via the `AGENT_RUNTIME` env var — output flows through the *unmodified* Rich formatter exactly as the legacy path does. (Constructing a full orchestrator at all — on either runtime — needs a syntactically-present API key even though `is_configured()` never validates it; this environment has none, so a dummy key was used for construction only. Also newly discovered, unrelated to this change: `FrontendDeveloperAgent` hardcodes `llm_provider=LLMProvider.GEMINI`, unlike every other agent which defaults to `LLM_PROVIDER`/Anthropic — construction needs a dummy `GEMINI_API_KEY` too.)
- **Not yet exercised**: an actual live LLM turn against the real `pi` binary — every verification above uses `tests/fake_pi_rpc.py`, which faithfully implements pi.dev's *documented* RPC protocol but has not been cross-checked turn-by-turn against the real binary's behavior with a real model. The Phase 1 live check (real `pi` CLI, real 79-tool bridge, real Anthropic 401) proves `dsdm-tools-bridge`/`dsdm-approval-gate` *load* correctly against the real CLI; a full tool-call-and-confirm turn against the real CLI still needs a real `ANTHROPIC_API_KEY`, unavailable in this environment (same gap as sections 16/17's `--live` mode).
- **Still legacy, unchanged this round**: Git Pin roles (Phase 4 — `GitPinAgentLoop`/`GitPinPipeline` untouched), native MCP client (Phase 5 — `dsdm-mcp-client` unbuilt, `mcp_call_tool` CLI-shell bridge still in place), session-tree/`.pi-sessions` artifact cross-linking (Phase 5), and retirement of `base_agent.py`'s loop / non-Anthropic `providers.py` clients (Phase 6 — nothing has reached `migrated`+bake-in yet per the PRD's Migration State Model).

## 22. Private vLLM Provider (PAR-PRD-FR-014/015/016)

### 22.1 What pi.dev actually supports (grounded in `docs/providers.md` and `docs/models.md`)

pi.dev has vLLM as a **named, first-class custom-provider case** — not something to bolt on:

> "Via `models.json`: Add Ollama, LM Studio, vLLM, or any provider that speaks a supported API (OpenAI Completions, OpenAI Responses, Anthropic Messages, Google Generative AI)."

vLLM serves an OpenAI-compatible `/v1` endpoint, so the provider is declared with `api: "openai-completions"`. There is no separate TypeScript extension needed for this — `models.json` is a config file pi reads at startup, unrelated to `dsdm-tools-bridge`/`dsdm-approval-gate`.

Config file locations (`docs/settings.md`, `docs/usage.md`):
- `~/.pi/agent/models.json` — global, user's home directory.
- `PI_CODING_AGENT_DIR` env var — overrides pi's *entire* config directory (default `~/.pi/agent`); everything pi reads (`models.json`, `settings.json`, `auth.json`, `sessions/`) moves under it.

**Design decision: generate `models.json` per invocation into a scoped `PI_CODING_AGENT_DIR`, don't hand-author a static one.** `models.json`'s `baseUrl` field has no environment-variable indirection — only `apiKey`/`headers` support the `"!command"` / env-var-name / literal resolution forms (section 11's PRD risk). Since the private endpoint URL is exactly the kind of value that must come from environment/deployment config (never hardcoded, per PAR-PRD-FR-016) and varies per environment (dev/staging/prod VPC), a static checked-in file can't hold it. `pi_session_runner.py` writes a fresh `models.json` into a per-run temp directory before spawning `pi`, and points that one subprocess's `PI_CODING_AGENT_DIR` at it — scoped to that single invocation, never touching the operator's real `~/.pi/agent/` state, and never persisted after the run.

### 22.2 Generated `models.json` shape

```json
{
  "providers": {
    "dsdm-vllm": {
      "baseUrl": "${DSDM_VLLM_BASE_URL}",
      "api": "openai-completions",
      "apiKey": "${DSDM_VLLM_API_KEY or a placeholder}",
      "compat": { "supportsDeveloperRole": false },
      "models": [{ "id": "${DSDM_VLLM_MODEL_ID}" }]
    }
  }
}
```

- `compat.supportsDeveloperRole: false` is set unconditionally: per `docs/models.md`, "some OpenAI-compatible servers do not understand the `developer` role used for reasoning-capable models... this commonly applies to Ollama, vLLM, SGLang, and similar" — vLLM is explicitly named, so this is not a guess.
- Only `id` is required per model (`docs/models.md`'s "Minimal Example" is exactly this shape for local/self-hosted servers) — no cost/context-window claims are asserted about a model this codebase doesn't control.
- No model name is hardcoded. A vLLM server is normally launched with one specific `--model <hf-repo-id>`, so the served model is whatever `DSDM_VLLM_MODEL_ID` names — this integration does not presume a specific open-weight model family.

### 22.3 Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `DSDM_VLLM_BASE_URL` | Yes, when `LLM_PROVIDER=vllm` | The private endpoint — a VPC-internal DNS name, PrivateLink/private-endpoint address, or cluster-internal Service URL (e.g. `http://vllm.internal.svc.cluster.local:8000/v1`). Never a public hostname. |
| `DSDM_VLLM_MODEL_ID` | Yes, when `LLM_PROVIDER=vllm` | The model ID the vLLM server was launched with. |
| `DSDM_VLLM_API_KEY` | No | Bearer token, if the deployment's internal auth proxy enforces one. Defaults to a placeholder (vLLM's own `--api-key` check, when enabled, still requires *a* value to be present — same pattern `docs/models.md` describes for Ollama, which "ignores it, so any value works"). |

### 22.4 Provider resolution

`pi_session_runner._resolve_provider()` (section 21) gains one more mapping: DSDM's `LLM_PROVIDER=vllm` → pi provider name `dsdm-vllm` (the custom key defined in the generated `models.json`, not a pi.dev built-in name — unlike `anthropic`/`openai`/`google`/`ollama`, which map to pi.dev's own built-in provider identifiers).

`run_role()`'s command-building step (section 8):
1. If the resolved provider is `dsdm-vllm`, create a per-run temp directory, write `models.json` into it from the three env vars above, and add `PI_CODING_AGENT_DIR=<temp dir>` to the subprocess environment.
2. Pass `--provider dsdm-vllm --model <DSDM_VLLM_MODEL_ID>` on the CLI, same as any other provider/model pair.
3. Clean up the temp directory after the subprocess exits (success or failure) — it holds the endpoint URL and token, so it does not outlive the one session that needed it.

This only affects the *one* role's subprocess invocation. Other roles in the same orchestrator run configured for a hosted provider are unaffected — `PI_CODING_AGENT_DIR` is set per-`Popen` call, not process-wide.

### 22.5 What this does not do

- Does not add retry-with-fallback-to-a-hosted-provider logic. A vLLM connection failure is a failed phase (PAR-PRD-FR-015) — silently falling back to a public provider on a private-endpoint failure would defeat the entire point of the requirement.
- Does not provision, deploy, or health-check the vLLM server itself. This is provider *plumbing* on the pi.dev/DSDM side; the GPU cluster, VPC networking, and vLLM process are assumed to already exist and be reachable at `DSDM_VLLM_BASE_URL` (PRD non-goal).
- Does not change `role_definitions.py`. Provider/endpoint selection is an orchestrator/environment-level concern (which backend serves the model), orthogonal to which role is running — no `RoleDefinition` field encodes "must run on vLLM."
