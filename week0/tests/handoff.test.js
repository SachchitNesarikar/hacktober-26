const assert = require("assert"), fs = require("fs"), path = require("path");
const H = require("../web/handoff.js");
const state = H.normalize(JSON.parse(fs.readFileSync(path.join(__dirname, "../demo/project-state.json"), "utf8")));
for (const t of Object.keys(H.TARGETS)) {
  const out = H.render(state, t, { projectName: "Pocket Ledger" });
  assert(out.includes("integer cents"), t + ": missing do-not-change item");
  assert(out.includes("updateRecurring"), t + ": missing next action");
  assert(out.includes("Workbox"), t + ": missing failed attempt");
}
assert(H.render(state, "claude").startsWith("<handoff>"));
assert(H.estimateTokens(H.render(state, "gemma")) <= H.estimateTokens(H.render(state, "gpt")));
const empty = H.render(H.normalize(null), "gpt");  // empty/garbage state must not throw
assert(empty.includes("(not captured)"));
assert.deepStrictEqual(H.counts(state).failed_attempts, 3);
console.log("handoff.js: all tests passed");
