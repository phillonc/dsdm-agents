/**
 * dsdm-tools-bridge — pi.dev extension
 *
 * Phase 1 of the Pi Agent Runtime migration
 * (docs/category-defining-features/11-pi-agent-runtime/TRD.md, sections 5 & 6).
 *
 * At startup this extension fetches the tool manifest from the Python
 * `tool_service.py` bridge (GET /tools — exactly `ToolRegistry.to_anthropic_format()`
 * plus `requires_approval`/`category`) and calls `pi.registerTool()` once per
 * entry. No DSDM tool handler logic is reimplemented here: every call is
 * forwarded to `POST /tools/<name>/execute`, which runs the real Python
 * handler via `ToolRegistry.execute()`.
 *
 * Out of scope for Phase 1 (see TRD section 6 / Implementation Plan Phase 3):
 * - Manual/Automated/Hybrid approval gating — lands in the separate
 *   `dsdm-approval-gate` extension. `requires_approval` is surfaced in the
 *   tool description for now, but nothing blocks on it yet.
 * - Delivery Room event forwarding — lands in `dsdm-room-events`.
 *
 * Start the bridge before loading this extension:
 *   python -m src.tools.tool_service
 * It prints the bound port; point this extension at it via DSDM_BRIDGE_URL
 * (defaults to http://127.0.0.1:8787).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

interface DsdmToolManifestEntry {
	name: string;
	description: string;
	input_schema: JsonSchema;
	requires_approval: boolean;
	category: string;
}

interface JsonSchema {
	type?: string;
	description?: string;
	properties?: Record<string, JsonSchema>;
	required?: string[];
	items?: JsonSchema;
	enum?: unknown[];
}

const DEFAULT_BRIDGE_URL = "http://127.0.0.1:8787";

function bridgeUrl(): string {
	return (process.env.DSDM_BRIDGE_URL ?? DEFAULT_BRIDGE_URL).replace(/\/+$/, "");
}

/** Converts one JSON-Schema property (as produced by Tool.to_anthropic_format()) to a typebox schema. */
function propertyToTypebox(schema: JsonSchema | undefined): any {
	if (!schema || typeof schema !== "object") return Type.Unknown();

	const opts = schema.description ? { description: schema.description } : undefined;

	// Google-compatible enums: pi.dev docs require StringEnum over Type.Union/Type.Literal.
	if (Array.isArray(schema.enum) && schema.enum.every((value) => typeof value === "string")) {
		return StringEnum(schema.enum as string[], opts);
	}

	switch (schema.type) {
		case "string":
			return Type.String(opts);
		case "integer":
			return Type.Integer(opts);
		case "number":
			return Type.Number(opts);
		case "boolean":
			return Type.Boolean(opts);
		case "array":
			return Type.Array(propertyToTypebox(schema.items), opts);
		case "object":
			return objectToTypebox(schema);
		default:
			// Unrecognized/absent type (e.g. free-form dict params some DSDM tools accept).
			return Type.Unknown(opts);
	}
}

/** Converts a JSON-Schema object ({type: "object", properties, required}) to Type.Object(...). */
function objectToTypebox(schema: JsonSchema): any {
	const properties = schema.properties ?? {};
	const required = new Set(schema.required ?? []);
	const fields: Record<string, any> = {};

	for (const [key, propertySchema] of Object.entries(properties)) {
		const converted = propertyToTypebox(propertySchema);
		fields[key] = required.has(key) ? converted : Type.Optional(converted);
	}

	return Type.Object(fields);
}

async function fetchManifest(base: string): Promise<DsdmToolManifestEntry[]> {
	let response: Response;
	try {
		response = await fetch(`${base}/tools`);
	} catch (cause) {
		throw new Error(
			`dsdm-tools-bridge: could not reach the Python tool service at ${base}. ` +
				`Start it with 'python -m src.tools.tool_service' (see TRD section 5). Cause: ${cause}`,
		);
	}
	if (!response.ok) {
		throw new Error(`dsdm-tools-bridge: GET ${base}/tools returned HTTP ${response.status}`);
	}
	const payload = (await response.json()) as { tools: DsdmToolManifestEntry[] };
	return payload.tools;
}

function runContext(): Record<string, string | null> {
	return {
		phase: process.env.DSDM_PHASE ?? null,
		role_id: process.env.DSDM_ROLE_ID ?? null,
		project: process.env.DSDM_PROJECT ?? null,
	};
}

export default async function dsdmToolsBridge(pi: ExtensionAPI) {
	const base = bridgeUrl();
	const manifest = await fetchManifest(base);

	for (const tool of manifest) {
		pi.registerTool({
			name: tool.name,
			label: tool.name,
			description: `${tool.description} (DSDM category: ${tool.category}${
				tool.requires_approval ? "; requires approval" : ""
			})`,
			parameters: objectToTypebox(tool.input_schema),
			async execute(_toolCallId, params) {
				let response: Response;
				try {
					response = await fetch(`${base}/tools/${encodeURIComponent(tool.name)}/execute`, {
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({ arguments: params, run_context: runContext() }),
					});
				} catch (cause) {
					throw new Error(`dsdm-tools-bridge: '${tool.name}' could not reach ${base}. Cause: ${cause}`);
				}

				if (!response.ok) {
					const body = await response.text();
					throw new Error(`dsdm-tools-bridge: '${tool.name}' failed with HTTP ${response.status}: ${body}`);
				}

				const payload = (await response.json()) as { result: string };
				return {
					content: [{ type: "text", text: payload.result }],
					details: { dsdmCategory: tool.category, requiresApproval: tool.requires_approval },
				};
			},
		});
	}
}
