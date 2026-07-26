/**
 * dsdm-approval-gate — pi.dev extension
 *
 * Reimplements BaseAgent._should_approve_tool (src/agents/base_agent.py) at
 * the pi.dev extension layer, per
 * docs/category-defining-features/11-pi-agent-runtime/TRD.md section 6.
 * PAR-PRD-FR-005 (PRD.md) requires Manual/Automated/Hybrid tool-approval
 * semantics to survive the migration to pi.dev — this extension is what
 * makes that true for tools registered by dsdm-tools-bridge. Without it,
 * every DSDM tool call executes unconditionally regardless of AgentMode.
 *
 * Mode resolution (DSDM_AGENT_MODE env var, default "automated" — matching
 * both AgentConfig's own default and main.py's --mode default):
 *   - automated: nothing is gated (parity with AgentMode.AUTOMATED -> True).
 *   - manual:    every DSDM-bridged tool call requires approval.
 *   - hybrid:    only tools whose manifest entry has requires_approval=true
 *                require approval; everything else runs immediately.
 *
 * Approval channel:
 *   - Interactive or RPC mode (ctx.hasUI === true): prompts via
 *     ctx.ui.confirm(), exactly like BaseAgent's approval_callback.
 *   - Print mode / JSON mode (ctx.hasUI === false): there is no synchronous
 *     human channel yet. BaseAgent denies when approval_callback is None
 *     (base_agent.py:242-249); this extension does the same until Phase 3's
 *     pi_session_runner.py wires a headless callback. Fail closed, not open.
 *
 * Only tools present in the DSDM manifest (i.e. registered by
 * dsdm-tools-bridge) are gated. Built-in pi tools (read/bash/edit/write/...)
 * and any other extension's tools are left untouched — BaseAgent never saw
 * those tools either, so there is no legacy behavior to preserve for them.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

type DsdmAgentMode = "automated" | "manual" | "hybrid";

interface DsdmToolManifestEntry {
	name: string;
	requires_approval: boolean;
}

const DEFAULT_BRIDGE_URL = "http://127.0.0.1:8787";

function bridgeUrl(): string {
	return (process.env.DSDM_BRIDGE_URL ?? DEFAULT_BRIDGE_URL).replace(/\/+$/, "");
}

function resolveAgentMode(raw: string | undefined): DsdmAgentMode {
	const normalized = (raw ?? "automated").trim().toLowerCase();
	if (normalized === "manual" || normalized === "hybrid" || normalized === "automated") {
		return normalized;
	}
	return "automated";
}

async function fetchRequiresApprovalMap(base: string): Promise<Map<string, boolean>> {
	let response: Response;
	try {
		response = await fetch(`${base}/tools`);
	} catch (cause) {
		throw new Error(
			`dsdm-approval-gate: could not reach the Python tool service at ${base}. ` +
				`Start it with 'python -m src.tools.tool_service' (see TRD section 5). Cause: ${cause}`,
		);
	}
	if (!response.ok) {
		throw new Error(`dsdm-approval-gate: GET ${base}/tools returned HTTP ${response.status}`);
	}
	const payload = (await response.json()) as { tools: DsdmToolManifestEntry[] };
	return new Map(payload.tools.map((tool) => [tool.name, tool.requires_approval]));
}

/** Exported for the extension's own test harness (index.test.ts) — pure gating decision, no I/O. */
export function needsApproval(mode: DsdmAgentMode, toolRequiresApproval: boolean): boolean {
	if (mode === "automated") return false;
	if (mode === "manual") return true;
	return toolRequiresApproval; // hybrid
}

export default async function dsdmApprovalGate(pi: ExtensionAPI) {
	const mode = resolveAgentMode(process.env.DSDM_AGENT_MODE);

	// AUTOMATED gates nothing — skip the manifest fetch and registering a handler entirely.
	if (mode === "automated") {
		return;
	}

	const requiresApproval = await fetchRequiresApprovalMap(bridgeUrl());

	pi.on("tool_call", async (event, ctx) => {
		const name = event.toolName;
		if (!requiresApproval.has(name)) {
			// Not a DSDM-bridged tool; out of scope for this gate.
			return;
		}

		if (!needsApproval(mode, requiresApproval.get(name) === true)) {
			return;
		}

		if (ctx.hasUI) {
			const approved = await ctx.ui.confirm(
				"DSDM approval required",
				`Allow '${name}' to run with ${JSON.stringify(event.input)}?`,
			);
			if (!approved) {
				return { block: true, reason: `Tool execution denied: ${name} (requires approval)` };
			}
			return;
		}

		// No interactive or RPC channel — fail closed, matching BaseAgent's
		// approval_callback=None behavior (base_agent.py:244, :249).
		return {
			block: true,
			reason:
				`Tool execution denied: ${name} (requires approval; no interactive approval channel ` +
				"available in headless mode — run interactively, via --mode rpc, or wait for the " +
				"Phase 3 session-runner callback)",
		};
	});
}
