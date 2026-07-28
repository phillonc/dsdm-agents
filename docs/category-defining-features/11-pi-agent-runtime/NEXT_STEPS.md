# Next Steps: Pi Agent Runtime Migration

This is the actionable, priority-ordered follow-up to `PRD.md`/`TRD.md` (sections 16–22 of the TRD carry the detailed build/verification log this summarizes). It reflects what's actually in the repo today, not the original aspirational plan — read this before picking up any further work here.

## Current State

| Piece | Status | Where |
|---|---|---|
| Tools bridge (`dsdm-tools-bridge`) | Built, live-verified against real `pi` CLI (79 tools) | `src/tools/tool_service.py`, `pi/extensions/dsdm-tools-bridge/` |
| Approval gate (`dsdm-approval-gate`) | Built, unit-tested; live-verified to *load* against real CLI | `pi/extensions/dsdm-approval-gate/` |
| Unified role definitions | Built, drift-guard tested (12 tests) | `src/agents/role_definitions.py`, `tests/test_role_definitions.py` |
| Session runner (RPC client) | Built, tested against a protocol-faithful fake process (29 tests) | `src/orchestrator/pi_session_runner.py` |
| Orchestrator cutover (`AGENT_RUNTIME`) | 6 of 7 phases wired (not PRD_TRD), tested (13 tests) | `src/orchestrator/dsdm_orchestrator.py` |
| Private vLLM provider | Built, config-generation tested (11 tests); no real vLLM server to verify against | `pi_session_runner.py` section 22 |
| CLI wiring (`--agent-runtime`, `--llm-provider`, `--pi-doctor`, `--generate-agents`) | Built, smoke-tested manually against the real CLI | `main.py`, `src/agents/role_definitions_check.py` |
| Lazy LLM client construction | Built, regression-tested (5 tests) | `src/agents/base_agent.py` |
| Git Pin replacement | Not started | — |
| Native MCP client | Not started | — |
| Session-tree/audit trail | Not started | — |
| Legacy code retirement | Not started (nothing has reached `migrated`+bake-in yet) | — |

Full test suite: 91 passing, 0 failures. (The previous pre-existing failure, `test_orchestrator_extension_registers_room_tools`, was fixed as a side effect of making `BaseAgent`'s LLM client construction lazy — see TRD section 23.)

**The single thread running through almost every "not yet verified" note in the TRD**: nothing in this migration has ever been exercised against the real `pi` binary with a real LLM call. Every test either talks to the real CLI without completing a turn (Phase 1's load/unload check) or talks to a fake process that faithfully implements pi.dev's *documented* protocol (Phases 2/3, vLLM). That gap is step 1 below for a reason — nothing after it can be trusted with full confidence until it's closed.

## Next Steps, in Order

### 1. Get real API credentials and run a live turn — do this before anything else

Everything built so far has been verified as thoroughly as possible without live model access, but "the fake process matches the documented protocol" and "the real binary actually behaves that way" are different claims. Before investing further:

- Set a real `ANTHROPIC_API_KEY` (or another supported provider's key) and run `python scripts/spike_feasibility_bridge.py --live` — the Phase 0 spike this was scaffolded for on day one but never actually run.
- Run one phase through the real orchestrator cutover: `DSDMOrchestrator(agent_runtime="pi")` → `run_phase(DSDMPhase.FEASIBILITY, ...)` against the real `pi` binary, not `tests/fake_pi_rpc.py`.
- Specifically exercise a `Hybrid`/`Manual` role so a real tool call hits `dsdm-approval-gate` and produces a real `extension_ui_request`/`extension_ui_response confirm` round trip — this exact path is what `tests/test_pi_session_runner.py`'s confirm tests protect against regressing, but only against the fake process.
- If a private vLLM/GPU endpoint is available, point `LLM_PROVIDER=vllm` at it and confirm the generated `models.json` + `PI_CODING_AGENT_DIR` wiring actually gets a real vLLM server to answer.

Fix whatever this surfaces before moving on — any real-protocol mismatch found here is higher priority than any item below.

### 2. Wire CI for the `pi/` TypeScript workspace

There is currently no CI coverage at all for `pi/extensions/*/index.test.ts` (10 passing tests, never run automatically) or for the Python side's interaction with a real `npm install`. Add a CI job that runs `npm install` in `pi/`, runs both extensions' `node --experimental-strip-types index.test.ts`, and ideally adds a `tsc --noEmit` step — no `tsconfig.json` exists yet, so extension code has only ever been verified by jiti's runtime type-stripping (which discards type errors), never statically checked.

### 3. Resolve the `brace-expansion` supply-chain advisory

`npm audit` in `pi/` reports one high-severity DoS advisory in `brace-expansion@5.0.7`, pulled in transitively via `@earendil-works/pi-coding-agent → minimatch`. Three different `package.json` `overrides` syntaxes were tried and none took effect in the sandbox this was built in (see TRD section 16) — worth retrying outside that environment, or just re-checking once `pi-coding-agent` bumps its own dependency. Low urgency (not reachable through DSDM's own code) but it's real supply-chain debt.

### 4. Port `PRD_TRD` to the pi.dev runtime

The one phase still permanently excluded from `AGENT_RUNTIME=pi` routing. `_run_prd_trd_phase()` is a hardcoded two-agent sub-workflow (Product Manager → PRD, then Dev Lead → TRD) with its own approval gate and Jira/Confluence sync calls layered on top — porting it means either running two `pi_session_runner.run_role()` calls in sequence (product-manager, then dev-lead) with the PRD output threaded into the TRD role's context, or deciding this sub-workflow is idiosyncratic enough to stay a hand-orchestrated two-call sequence permanently. Either way, decide explicitly rather than leaving it silently un-migrated.

### 5. Git Pin replacement (original Phase 4)

Replace `GitPinAgentLoop`/`GitPinPipeline`'s thread-pool-based parallel execution with concurrently spawned `pi_session_runner.run_role()` calls (`asyncio.gather` or a small `ThreadPoolExecutor` over the existing `run_role()` calls, since it already shells out to a subprocess per role) plus a thin dependency-ordering coordinator matching today's `depends_on` semantics. `git-pin-coder`/`git-pin-reviewer` are already registered in `role_definitions.py` — this is "wire them into the pi runtime," not "define them from scratch." Validate the resulting throughput against `ThroughputMetrics`' existing baseline (PAR-TRD-NFR-003) before calling this migrated.

### 6. Native MCP client (original Phase 5)

Replace `src/tools/integrations/mcp_tools.py`'s CLI-shell bridge (`mcp_call_tool` spawning an `mcp call` subprocess, dry-run-by-default behind `MCP_EXECUTE=1`) with a `dsdm-mcp-client` pi.dev extension that talks to MCP servers natively. Preserve the existing safety posture: destructive calls stay `requires_approval` and route through `dsdm-approval-gate` like any other tool (already noted as a design constraint in TRD section 13, not yet built).

### 7. Session-tree / audit-trail integration (also original Phase 5)

Cross-link each phase's pi.dev session file into the corresponding Delivery Room artifact (PAR-PRD-FR-009, still "Should," not "Must"). `pi_session_runner.py` already captures `session_id` from RPC events; the missing piece is resolving that ID to an actual session file path (pi's storage convention wasn't confirmed in this work — check `docs/sessions.md` for the exact layout) and writing the `.pi-sessions/<phase>.session-ref.json` pointer file the TRD's storage layout (section 4) describes.

### 8. Real-world vLLM verification

Section 22's implementation is verified down to "the generated `models.json` matches pi.dev's documented schema and the subprocess environment is wired correctly" — it has never talked to an actual vLLM server. Once a private GPU/vLLM deployment is available, confirm: the `openai-completions` API compatibility assumptions hold for the actual model served, `compat.supportsDeveloperRole: false` is in fact necessary (it's applied unconditionally based on pi.dev's docs naming vLLM, not from observing a real failure), and PAR-PRD-FR-015's fail-closed behavior triggers correctly on a real network-level failure (endpoint unreachable, TLS/VPC misconfiguration), not just a missing-env-var failure.

### 9. Retirement (original Phase 6) — last, and only after real bake-in

Delete `base_agent.py`'s loop, `git_pin_agent_core.py`, `orchestrator_extension.py`, and the OpenAI/Gemini/Ollama client code in `src/llm/providers.py`. Per the PRD's Migration State Model, this is only correct once every role has reached `migrated` and stayed stable for an agreed bake-in period — i.e., not before steps 1–7 above are done and steps 4–6's roles have actually been run in `pi` mode for real work, not just tests. Don't do this opportunistically alongside earlier steps; it's the one irreversible step in this whole list.

## Not blocking, but worth doing opportunistically

All three items originally listed here are now done:

- **`main.py --generate-agents`**: built as a structural drift check (`src/agents/role_definitions_check.py`), not a content generator — `.github/agents/*.agent.md` prose stays intentionally hand-authored (see `role_definitions.py`'s module docstring for why regenerating it would destroy real content rather than produce it). Checks every role's tools resolve in `ToolRegistry` and every `.agent.md` file matches its `RoleDefinition`.
- **README.md / AGENTS.md**: updated ahead of `AGENT_RUNTIME=pi` becoming any phase's default (the original gating condition), since the CLI flags and vLLM provider are now real, operator-reachable functionality worth documenting regardless of what the default is. `legacy` is still the default runtime — nothing here changed that.
- **vLLM role-suitability policy**: decided — every role may be configured onto vLLM/an open-weight model, no per-role restriction. Recorded in PRD.md section 13 and TRD section 22.5.
