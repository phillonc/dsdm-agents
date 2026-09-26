// @earendil-works/pi-coding-agent ships an npm-shrinkwrap.json that pins
// brace-expansion@5.0.7 (GHSA-mh99-v99m-4gvg, high). A shrinkwrap inside a
// dependency wins over root "overrides", so we replace the nested copy with
// the patched version installed at the workspace root. Remove this once
// upstream ships a shrinkwrap with brace-expansion >= 5.0.8.
import { cpSync, rmSync, existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const patched = join(root, "node_modules", "brace-expansion");
const nested = join(
  root,
  "node_modules",
  "@earendil-works",
  "pi-coding-agent",
  "node_modules",
  "brace-expansion",
);

if (!existsSync(patched)) {
  console.warn("patch-brace-expansion: no root brace-expansion copy found, skipping");
  process.exit(0);
}
if (!existsSync(nested)) {
  console.log("patch-brace-expansion: no nested copy to patch, nothing to do");
  process.exit(0);
}

const version = (p) =>
  JSON.parse(readFileSync(join(p, "package.json"), "utf8")).version;

const before = version(nested);
rmSync(nested, { recursive: true, force: true });
cpSync(patched, nested, { recursive: true });
console.log(
  `patch-brace-expansion: replaced nested ${before} with ${version(nested)}`,
);
