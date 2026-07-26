/**
 * Test harness for dsdm-approval-gate. No LLM/pi CLI dependency: drives the
 * extension's default export directly with a stub ExtensionAPI/ExtensionContext
 * and a stubbed global fetch standing in for tool_service.py's /tools manifest.
 *
 * Run with:
 *   node --experimental-strip-types index.test.ts
 */

import assert from "node:assert/strict";
import dsdmApprovalGate, { needsApproval } from "./index.ts";

type ToolCallHandler = (event: any, ctx: any) => Promise<any>;

const MANIFEST = {
	tools: [
		{ name: "analyze_requirements", requires_approval: false },
		{ name: "mcp_call_tool", requires_approval: true },
	],
};

function stubPi(): { on: (name: string, handler: ToolCallHandler) => void; handler: ToolCallHandler | null } {
	const registry: { handler: ToolCallHandler | null } = { handler: null };
	return {
		on: (name: string, handler: ToolCallHandler) => {
			if (name === "tool_call") registry.handler = handler;
		},
		get handler() {
			return registry.handler;
		},
	} as any;
}

function withStubbedFetch<T>(run: () => Promise<T>): Promise<T> {
	const original = globalThis.fetch;
	globalThis.fetch = (async (url: string) => {
		if (url.endsWith("/tools")) {
			return new Response(JSON.stringify(MANIFEST), { status: 200 });
		}
		throw new Error(`unexpected fetch: ${url}`);
	}) as typeof fetch;
	return run().finally(() => {
		globalThis.fetch = original;
	});
}

let passed = 0;
async function test(name: string, fn: () => Promise<void> | void) {
	try {
		await fn();
		passed++;
		console.log(`ok - ${name}`);
	} catch (err) {
		console.error(`FAIL - ${name}`);
		console.error(err);
		process.exitCode = 1;
	}
}

// -- pure gating table (mirrors BaseAgent._should_approve_tool's mode logic) -----
await test("needsApproval: automated never requires approval", () => {
	assert.equal(needsApproval("automated", false), false);
	assert.equal(needsApproval("automated", true), false);
});

await test("needsApproval: manual always requires approval", () => {
	assert.equal(needsApproval("manual", false), true);
	assert.equal(needsApproval("manual", true), true);
});

await test("needsApproval: hybrid follows the tool's requires_approval flag", () => {
	assert.equal(needsApproval("hybrid", false), false);
	assert.equal(needsApproval("hybrid", true), true);
});

// -- default export / tool_call handler wiring -----------------------------------
await test("automated mode registers no tool_call handler", async () => {
	process.env.DSDM_AGENT_MODE = "automated";
	const pi = stubPi();
	await dsdmApprovalGate(pi as any);
	assert.equal(pi.handler, null);
});

await test("hybrid + non-approval tool + headless: allowed (no block)", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "hybrid";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const result = await pi.handler!(
			{ toolName: "analyze_requirements", toolCallId: "1", input: {} },
			{ hasUI: false },
		);
		assert.equal(result, undefined);
	});
});

await test("hybrid + approval-required tool + headless: blocked, fail-closed", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "hybrid";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const result = await pi.handler!(
			{ toolName: "mcp_call_tool", toolCallId: "1", input: {} },
			{ hasUI: false },
		);
		assert.equal(result.block, true);
		assert.match(result.reason, /requires approval/);
		assert.match(result.reason, /headless/);
	});
});

await test("manual + any DSDM tool + headless: blocked", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "manual";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const result = await pi.handler!(
			{ toolName: "analyze_requirements", toolCallId: "1", input: {} },
			{ hasUI: false },
		);
		assert.equal(result.block, true);
	});
});

await test("non-DSDM tool name is never gated, any mode", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "manual";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const result = await pi.handler!({ toolName: "bash", toolCallId: "1", input: {} }, { hasUI: false });
		assert.equal(result, undefined);
	});
});

await test("hybrid + approval-required tool + interactive UI confirms: allowed", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "hybrid";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const ctx = { hasUI: true, ui: { confirm: async () => true } };
		const result = await pi.handler!({ toolName: "mcp_call_tool", toolCallId: "1", input: {} }, ctx);
		assert.equal(result, undefined);
	});
});

await test("hybrid + approval-required tool + interactive UI declines: blocked, legacy-parity message", async () => {
	await withStubbedFetch(async () => {
		process.env.DSDM_AGENT_MODE = "hybrid";
		const pi = stubPi();
		await dsdmApprovalGate(pi as any);
		const ctx = { hasUI: true, ui: { confirm: async () => false } };
		const result = await pi.handler!({ toolName: "mcp_call_tool", toolCallId: "1", input: {} }, ctx);
		assert.equal(result.block, true);
		assert.equal(result.reason, "Tool execution denied: mcp_call_tool (requires approval)");
	});
});

delete process.env.DSDM_AGENT_MODE;

console.log(`\n${passed} passed`);
if (process.exitCode) {
	console.error("SOME TESTS FAILED");
} else {
	console.log("ALL TESTS PASSED");
}
