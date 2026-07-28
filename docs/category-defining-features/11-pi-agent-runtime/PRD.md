# PRD: Pi Agent Runtime (pi.dev Adoption)

## 1. Product Summary

Pi Agent Runtime replaces the hand-rolled agent execution engines in `src/agents/` and `src/llm/` with [pi.dev](https://pi.dev/) (the `pi-mono` toolkit — `pi-ai`, `pi-agent-core`, `pi-coding-agent`, `pi-tui`) as the execution substrate for every DSDM phase agent and Design & Build role.

DSDM-specific domain logic — the 42+ tools, MoSCoW conventions, Manual/Automated/Hybrid approval model, and the Delivery Room state/event/health layer — is preserved and re-fronted as pi.dev extensions and a tool bridge, rather than rewritten. The result is one execution engine (pi.dev's) instead of two competing, self-maintained ones, one multi-provider LLM layer instead of a fragile bespoke one, and one declarative agent-definition format instead of two that silently drift.

## 2. Problem Statement

The codebase currently carries the full maintenance cost of building an agent harness, without the benefit of using one:

- **Two competing, hand-rolled agent loops** exist: `BaseAgent.run()` (`src/agents/base_agent.py`) — a manual, sequential chat/tool loop — and `GitPinAgentLoop` (`src/agents/git_pin_agent_core.py`) — a second, parallel/event-driven loop whose own docstrings say it was "adapted from pi-mono's agent-core architecture." Neither is the real framework; both must be independently debugged, tested, and extended.
- **The multi-provider LLM layer is fragile.** `src/llm/providers.py`'s Gemini client carries ~115 lines of defensive protobuf-to-dict unwrapping and leaves `print(..., file=sys.stderr)` debug statements in production code. Its phase→model routing table (`PHASE_MODELS`) is hardcoded to Claude model IDs regardless of the configured provider — so setting `LLM_PROVIDER=openai` or `gemini` does not change which model a phase actually requests. This is a live, unnoticed defect that this transformation fixes as a direct consequence of adopting `pi-ai`.
- **Two parallel, non-code-linked agent definitions** describe the same ~12 roles: Python `AgentConfig` objects with embedded system prompts (`src/agents/*.py`, `src/orchestrator/dsdm_orchestrator.py`), and `.github/agents/*.agent.md` Markdown files consumed by GitHub Copilot CLI. Every role change (a new tool, a changed responsibility) must be made twice by hand, with no mechanism to detect drift between them.
- **"Git Pin" was an acknowledged, incomplete attempt** to bring pi-mono's throughput/parallelism model into the repo, built from scratch in Python instead of adopting the actual framework. The repo pays for a parallel-execution engine (context pruning, before/after tool hooks, adaptive concurrency, throughput metrics) without any of pi.dev's upstream development, 15+ provider coverage, or extension ecosystem.
- **There is no session persistence or replay.** Conversation state lives only in an in-memory `messages` list per agent run; a crash mid-phase loses all context, and there is no way to branch or re-run a phase from a checkpoint the way pi.dev's session-tree model supports natively.

## 3. Target Users

- DSDM Agents maintainers/contributors who build and debug agent behavior
- Delivery teams running the CLI and Delivery Room workflow day to day (`main.py`)
- GitHub Copilot CLI users invoking `.github/agents/*.agent.md` / `.github/prompts/*.prompt.md`
- Platform engineers adding new LLM providers, tools, or MCP integrations

## 4. Goals

- Replace `BaseAgent.run()` and `GitPinAgentLoop` with pi.dev's agent runtime (`pi-agent-core` / `pi-coding-agent`) for all 6 DSDM phase agents and all 8 Design & Build roles (including the two Git Pin roles).
- Replace `src/llm/providers.py` with `pi-ai`'s unified multi-provider client, correcting the Anthropic-only phase-routing defect as a direct side effect.
- Collapse the two parallel agent-definition sources into one declarative source of truth, consumed by both GitHub Copilot CLI (`.agent.md`) and pi.dev (Pi Packages).
- Preserve 100% of existing DSDM tool behavior (42+ tools across feasibility, business study, design & build, implementation, DevOps, Jira/Confluence, file, room, and MCP categories) without a line-by-line TypeScript rewrite of their business logic.
- Preserve the Delivery Room state/event/health model (`src/rooms/`) and DSDM's Manual/Automated/Hybrid approval semantics unchanged from the user's point of view.
- Gain session-tree persistence (branch/fork/replay a phase) and a structured JSON event stream for orchestrator and Delivery Room integration, replacing today's in-process `ProgressCallback` as the sole signal source.
- Support running any role against an open-weight model served by a self-hosted [vLLM](https://github.com/vllm-project/vllm) instance on private GPU infrastructure, reachable only through a VPC-internal or private-endpoint URL — no public internet egress required for inference — as an operator-selectable alternative to the hosted providers above.

## 5. Non-Goals

- Rewriting all 42+ tool handlers' business logic (feasibility scoring, MoSCoW prioritization, document generators, Jira/Confluence integrations) in TypeScript in the first release — they are bridged, not reimplemented.
- Building a new UI. pi.dev's terminal UI and JSON/RPC output remain the interface; the existing Rich-based `main.py` interactive menu and Delivery Room Markdown dashboard keep working against it.
- Replacing or redesigning the Delivery Room data model (`DeliveryRoomState`, event log, health score) — it stays, and simply receives its inputs from a new event source.
- Guaranteeing byte-identical LLM outputs before and after migration. System prompt assembly, tool schema shape, and loop mechanics change, so outputs will differ even where intent is unchanged.
- Committing to a single-language (TypeScript-only) codebase. Python remains the home for DSDM domain/business logic for the foreseeable future.
- Provisioning, operating, or scaling the private GPU/vLLM infrastructure itself (Kubernetes, Terraform, GPU fleet management, model weight distribution). This migration assumes an already-running vLLM OpenAI-compatible endpoint reachable at a configured private URL; standing that endpoint up is a separate infrastructure workstream.
- Guaranteeing output quality or task parity between a hosted frontier model (Claude, GPT, Gemini) and whatever open-weight model a given vLLM deployment happens to serve. The integration is provider plumbing, not a model-capability claim.

## 6. Core User Stories

### Must Have

1. As a maintainer, I can run any DSDM phase (feasibility → implementation) through pi.dev instead of `BaseAgent.run()` and receive an `AgentResult`-equivalent output.
2. As a maintainer, I can add or change a DSDM tool once and have it available to both the orchestrated workflow and any direct pi.dev session, without maintaining a second TypeScript copy of its schema.
3. As a maintainer, I can define an agent role (system prompt, tool allowlist, model, mode) once and have both GitHub Copilot CLI and pi.dev consume the same definition.
4. As an operator, I can select an LLM provider (Anthropic, OpenAI, Gemini, Ollama, or any provider `pi-ai` supports) per phase, and every phase actually honors that selection.
5. As an operator with data-residency or cost constraints, I can point any phase at an open-weight model served by our own vLLM deployment on private GPUs, addressed only via a VPC-internal or private-endpoint URL, without any inference traffic crossing the public internet.
6. As an operator, running the Design & Build team concurrently (today's Git Pin pipeline) still works, backed by concurrently spawned pi.dev sessions instead of a custom thread pool.
7. As an operator, the Delivery Room dashboard, health score, and event log continue to update correctly when phases run through pi.dev.
8. As an operator, the Manual/Automated/Hybrid tool-approval model continues to gate the same tools it gates today.

### Should Have

1. As a maintainer, I can inspect a completed phase's full session tree, including any forks or replays, using pi.dev's native session tooling.
2. As a maintainer, MCP integrations use a native MCP-client extension instead of shelling out to an `mcp call` CLI subprocess.
3. As a maintainer, generated `.agent.md` files are produced from the single source of truth by a checked-in generator, and CI fails if they drift.
4. As an operator, I can roll a single phase back to the legacy Python loop via a feature flag if the pi.dev path regresses, without reverting the whole migration.
5. As a security reviewer, I can confirm that when a role is configured for the private vLLM provider, no fallback path silently sends its prompts or tool schemas to a public hosted provider instead.

### Could Have

1. As a maintainer, I can package a DSDM role as an installable Pi Package (npm or git) for reuse outside this repository.
2. As an operator, I can resume or branch a stalled phase session instead of restarting it from scratch.
3. As a maintainer, I can run a phase's session export as an HTML artifact for stakeholder review, using pi.dev's session export feature.

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| PAR-PRD-FR-001 | Provide a `dsdm-tools-bridge` pi.dev extension that dynamically registers every tool in the existing `ToolRegistry` as a pi tool and forwards execution to the Python tool layer | Must |
| PAR-PRD-FR-002 | Provide one declarative role-definition source (name, description, phase, system prompt, tools, model, mode) that generates both `.github/agents/*.agent.md` and pi.dev Pi Package configuration | Must |
| PAR-PRD-FR-003 | Route every DSDM phase agent and Design & Build role's execution through a pi.dev session instead of `BaseAgent.run()`, preserving `AgentResult`-equivalent output (success, output, artifacts, tool_calls, next_phase_input) | Must |
| PAR-PRD-FR-004 | Retire `src/llm/providers.py` in favor of `pi-ai`; support Anthropic, OpenAI, Gemini, and Ollama at parity, with per-phase model selection honoring the configured provider | Must |
| PAR-PRD-FR-005 | Preserve AgentMode (Manual/Automated/Hybrid) tool-approval semantics using a pi.dev tool-call lifecycle hook extension | Must |
| PAR-PRD-FR-006 | Bridge pi.dev's JSON-mode event stream into Delivery Room state updates (`room_progress.py`'s responsibilities), replacing the in-process callback as the source of truth | Must |
| PAR-PRD-FR-007 | Reimplement Git Pin's parallel Design & Build execution using concurrently spawned pi.dev sessions with dependency ordering equivalent to today's `GitPinPipeline.depends_on` | Must |
| PAR-PRD-FR-008 | Preserve Manual/Automated/Hybrid execution modes and existing `main.py` CLI flags (`--phase`, `--workflow`, `--mode`, `--room-*`, `--git-pin-pipeline`) unchanged from the operator's perspective | Must |
| PAR-PRD-FR-009 | Persist every DSDM phase run as a pi.dev session-tree JSONL file, cross-referenced from the corresponding Delivery Room artifact | Should |
| PAR-PRD-FR-010 | Replace the CLI-shell MCP bridge (`mcp_call_tool` subprocess) with a native MCP-client pi.dev extension | Should |
| PAR-PRD-FR-011 | Restructure root `AGENTS.md` so it is the actual instruction file pi.dev auto-loads, in addition to serving GitHub Copilot CLI | Must |
| PAR-PRD-FR-012 | Provide a feature flag (e.g. `AGENT_RUNTIME=legacy\|pi`) allowing any single phase to fall back to the pre-migration Python loop during rollout | Should |
| PAR-PRD-FR-013 | Deprecate and remove `git_pin_agent_core.py`'s custom loop, `orchestrator_extension.py`'s monkeypatch installer, and provider-specific protobuf/parsing hacks once pi.dev parity is verified | Should |
| PAR-PRD-FR-014 | Support a private, self-hosted vLLM provider (open-weight models on private GPUs) as a first-class `LLM_PROVIDER` option, addressed only via a VPC-internal or private-endpoint `baseUrl` — never a public internet address | Must |
| PAR-PRD-FR-015 | When the vLLM provider is selected for a role, guarantee no automatic fallback to a public hosted provider on error — the role fails closed rather than silently leaking prompts/tool schemas off the private network | Must |
| PAR-PRD-FR-016 | Treat the vLLM endpoint URL and any bearer token as environment-sourced configuration, never hardcoded or committed to the repository | Must |

## 8. Acceptance Criteria

- Given a phase is run via `python main.py --phase feasibility --input "..."`, when the pi.dev runtime executes it, then the output artifacts written to `generated/<project>/docs/` are equivalent in kind and location to today's output.
- Given a new DSDM tool is registered in `ToolRegistry`, when a pi.dev session for any role starts, then the tool is available to that session without any TypeScript change.
- Given an agent role's system prompt or tool list changes in the single source of truth, when the generator runs, then both `.github/agents/<role>.agent.md` and the corresponding Pi Package are regenerated and stay identical in content.
- Given `LLM_PROVIDER=gemini` is set, when any phase runs, then the session actually requests a Gemini model (not a hardcoded Claude model ID).
- Given a Design & Build role is configured as `AgentMode.HYBRID` with a tool marked `requires_approval`, when that tool is called during a pi.dev session, then execution pauses for approval exactly as it does today under `BaseAgent._should_approve_tool`.
- Given the Git Pin pipeline runs Frontend Developer and Backend Developer concurrently, when both complete, then Delivery Room state reflects both roles' artifacts and hand-offs, matching today's `GitPinPipeline` behavior.
- Given a phase fails mid-session, when the operator inspects the corresponding pi.dev session file, then the full tool-call and message history up to the failure point is recoverable.
- Given the `AGENT_RUNTIME` flag is set to `legacy` for a specific phase, when that phase runs, then it executes via the pre-migration `BaseAgent` path unaffected by the rest of the migration.
- Given `LLM_PROVIDER=vllm` and a private `DSDM_VLLM_BASE_URL` are configured, when any phase runs, then the session's only outbound model traffic goes to that URL — no request is made to `api.anthropic.com`, `api.openai.com`, or any other public provider domain.
- Given the vLLM endpoint is unreachable or returns an error, when a role configured for it runs, then the phase fails with a clear error rather than silently retrying against a public provider.

## 9. Migration State Model

Each DSDM phase agent and Design & Build role moves independently through:

- `legacy` — runs exclusively on `BaseAgent.run()` / `GitPinAgentLoop`, as today.
- `bridged` — tools are available through `dsdm-tools-bridge`, but the role still executes via the legacy loop (validates the bridge without touching the loop).
- `piloted` — the role executes via pi.dev behind the `AGENT_RUNTIME` flag, defaulting to `legacy`, opt-in per run.
- `migrated` — pi.dev is the default execution path for the role; `legacy` remains available only as an explicit fallback.
- `retired` — the legacy code path for that role is deleted.

Tracking this per role (rather than a single repo-wide switch) keeps the rollout incremental and reversible, consistent with DSDM's "build incrementally from firm foundations" principle.

## 10. Metrics

- 100% of existing DSDM tools reachable through the pi.dev bridge with zero handler rewrites in v1.
- Zero duplicated agent-role definitions remaining once the generator lands (single source of truth for all 12+ roles).
- 100% of phases honor `LLM_PROVIDER` for non-Anthropic providers post-migration (currently 0% — the routing table ignores it).
- ≥95% pass rate on the existing DSDM tool and Delivery Room integration tests (`tests/`) run against the pi.dev-backed path.
- `base_agent.py`'s `run()` loop (~260 lines) and `git_pin_agent_core.py` (~28 KB) fully retired by the end of the migration.
- Git Pin parallel Design & Build throughput (tools/sec) at or above the current `ThroughputMetrics` baseline after moving to process-level parallel pi.dev sessions.
- 100% of outbound model requests for a vLLM-configured role go to the configured private endpoint — zero requests observed to any public provider domain in that configuration.

## 11. Risks

- pi.dev is an actively developed external project; a pinned version and an explicit upgrade process are required to avoid breaking the bridge extension on upstream changes.
- Bridging Python tool handlers via a local RPC/HTTP boundary adds a process hop versus today's in-process function calls, with latency and failure-mode implications.
- The codebase becomes bilingual (Python domain logic, TypeScript extensions), raising the contribution bar and CI/build complexity.
- Delivery Room and MCP behavior must be revalidated against `tests/test_delivery_room.py` and `tests/test_mcp_tools.py` to catch regressions introduced by the new event source.
- pi.dev deliberately ships no built-in permission system (isolation is expected via containers); DSDM's per-tool `requires_approval` model must be reconstructed as an explicit extension hook, not assumed to come for free.
- Two independent parallel-execution mechanisms (today's `GitPinPipeline` and pi.dev's native parallel tool calls plus process-level session concurrency) must be reconciled carefully to avoid a regression in Design & Build throughput during the transition.
- Open-weight models served by a self-hosted vLLM deployment are not drop-in equivalents for Claude/GPT/Gemini on tool-calling reliability, instruction-following, or context length — a role moved to vLLM may need prompt/tool-schema adjustments or a capability-appropriate model choice, not just a provider swap.
- `models.json`'s `baseUrl` field has no environment-variable indirection (unlike `apiKey`/`headers`), so the private endpoint URL must be injected by generating the file per invocation rather than checking in a static one — an extra moving part versus the other providers, and a place a stale or leaked generated file could misdirect traffic if not scoped and cleaned up correctly.

## 12. Migration Phases

### Phase 0 — Spike
- Stand up pi.dev in the repo (pinned version) and run the Feasibility phase only through it, using a minimal hand-written tool bridge for the 3 feasibility tools.
- Compare output against the legacy path on the same input to validate the approach before broader investment.

### Phase 1 — Tools Bridge
- Ship `dsdm-tools-bridge` as a generic extension that introspects the full `ToolRegistry` and registers every tool dynamically.
- Purely additive: no phase's execution path changes yet.

### Phase 2 — Unified Role Definitions
- Introduce the single role-definition source and the generator that produces `.github/agents/*.agent.md` and Pi Packages from it.
- Wire CI to fail on drift between generated and committed files.

### Phase 3 — Runtime Cutover
- Move phases and roles from `legacy` to `piloted` to `migrated` behind `AGENT_RUNTIME`, one at a time, cheapest/lowest-risk phase first (Feasibility, given its low iteration cap).
- Add the private vLLM provider option (`LLM_PROVIDER=vllm`) alongside the hosted providers, since it uses the same pi.dev provider-resolution mechanism the cutover already depends on.

### Phase 4 — Git Pin Replacement
- Replace `GitPinAgentLoop`/`GitPinPipeline` with process-level concurrent pi.dev sessions plus a thin dependency-ordering coordinator.

### Phase 5 — Native MCP and Session Tree
- Replace the CLI-shell MCP bridge with a native MCP-client extension.
- Adopt pi.dev's session-tree storage as the canonical per-phase audit trail, cross-linked from Delivery Room artifacts.

### Phase 6 — Retirement
- Delete `base_agent.py`'s loop, `git_pin_agent_core.py`, `orchestrator_extension.py`, and the Gemini/OpenAI/Ollama client code in `src/llm/providers.py` once every role reaches `migrated` and has stayed stable for an agreed bake-in period.

## 13. Open Questions

- Should the Python tool layer be exposed to the TypeScript bridge via local HTTP, stdio JSON-RPC, or a long-lived daemon process?
- Should new DSDM tools be authored directly in TypeScript going forward, or should Python-behind-the-bridge remain the default indefinitely?
- Should Delivery Room state eventually live inside pi.dev's session-tree JSONL store, or remain the separate JSON layer it is today?
- What is the repo's version-pinning and upgrade process for the `pi/` TypeScript workspace, given pi-mono's own emphasis on shrinkwrap/exact-version supply-chain hygiene?
- Does the `AGENT_RUNTIME=legacy|pi` flag live per-phase, per-role, or both, and how long does it stay supported after a role reaches `migrated`?
- Does the private vLLM endpoint need per-role or per-project network isolation (separate VPC endpoints/security groups), or is one shared private endpoint sufficient for all DSDM traffic?

**Decided:** ~~Which roles are actually suitable candidates for a private open-weight model~~ — **every role may be configured onto vLLM/an open-weight model; there is no role-based restriction.** This is not a per-role policy encoded anywhere in `RoleDefinition` or the orchestrator — provider/endpoint selection is an environment-level setting (`LLM_PROVIDER=vllm` + `DSDM_VLLM_BASE_URL`/`DSDM_VLLM_MODEL_ID`) that applies uniformly to whichever phase is routed through `AGENT_RUNTIME=pi`, including higher-stakes roles like Dev Lead and Pen Tester. Operators who want a specific role kept on a frontier hosted provider do so by leaving that phase on `AGENT_RUNTIME=legacy` (or running a separate orchestrator invocation with a different `LLM_PROVIDER`), not via a built-in allowlist/denylist. See TRD section 22.5.
