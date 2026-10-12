const fs = require("fs");
const h = require("../web/handoff.js");
const state = h.normalize(JSON.parse(fs.readFileSync("demo/project-state.json", "utf8")));
for (const t of ["claude", "gemma"]) {
  const out = h.render(state, t, { projectName: "Pocket Ledger" });
  fs.writeFileSync(`demo/generated-handoff-${t}.md`, out);
  console.log(t, h.estimateTokens(out), "tokens est.");
}
