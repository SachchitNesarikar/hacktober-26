/* Baton handoff renderer. Pure functions, no DOM: runs in the browser (demo mode) and in Node (tests). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.BatonHandoff = factory();
})(typeof self !== "undefined" ? self : this, function () {
  var LIST_FIELDS = ["architecture", "decisions", "constraints", "user_preferences", "files",
    "recent_changes", "failed_attempts", "known_bugs", "open_tasks", "do_not_change"];

  var TARGETS = {
    claude: { label: "Claude", style: "xml", intro: "You are taking over an in-progress software project from another AI assistant." },
    gemini: { label: "Gemini", style: "md", intro: "You are taking over an in-progress software project from another AI assistant." },
    gpt: { label: "ChatGPT / GPT", style: "md", intro: "You are taking over an in-progress software project from another AI assistant." },
    gemma: { label: "Local Gemma (compact)", style: "compact", intro: "Continue this software project. Another assistant worked on it before you." },
    agent: { label: "Coding agent file (AGENTS.md)", style: "agentsmd", intro: "Project memory for coding agents. Read before changing anything." }
  };

  function str(v) { return v == null ? "" : String(v).trim(); }
  function item(field, it) {
    if (field === "decisions") return str(it.what) + (str(it.why) ? " (why: " + str(it.why) + ")" : "");
    if (field === "failed_attempts") return str(it.what) + (str(it.why_failed) ? " (failed because: " + str(it.why_failed) + ")" : "");
    if (field === "files") return str(it.path) + (str(it.note) ? ": " + str(it.note) : "");
    return str(it);
  }
  function items(state, f) { return (state[f] || []).map(function (x) { return item(f, x); }).filter(Boolean); }

  var SECTIONS = [
    ["do_not_change", "DO NOT CHANGE", "hard rules"],
    ["constraints", "Constraints", ""],
    ["user_preferences", "How the developer likes to work", ""],
    ["architecture", "Architecture", ""],
    ["decisions", "Decisions already made (do not re-litigate)", ""],
    ["failed_attempts", "Already tried and failed (do not repeat)", ""],
    ["files", "Key files", ""],
    ["recent_changes", "Recent changes", ""],
    ["known_bugs", "Known bugs", ""],
    ["open_tasks", "Open tasks", ""]
  ];

  var RULES = [
    "Treat DO NOT CHANGE items and decisions as binding unless the developer explicitly reverses them.",
    "Do not retry anything listed under 'Already tried and failed' without a new reason.",
    "If something you need is missing from this memory, ask the developer instead of guessing.",
    "Start by restating the goal and next action in two sentences, then continue the work."
  ];

  function heading(style, text) {
    if (style === "xml") return null;
    return (style === "compact" ? "" : "## ") + text + (style === "compact" ? ":" : "");
  }

  function render(state, targetKey, opts) {
    opts = opts || {};
    var t = TARGETS[targetKey] || TARGETS.gpt;
    var name = str(opts.projectName);
    var out = [];
    var compact = t.style === "compact";
    var maxItems = compact ? 6 : 50;

    if (t.style === "xml") {
      out.push("<handoff>");
      out.push(t.intro);
      out.push("<project>" + (name || "Untitled project") + "</project>");
      out.push("<goal>" + str(state.goal) + "</goal>");
      SECTIONS.forEach(function (s) {
        var list = items(state, s[0]).slice(0, maxItems);
        if (!list.length) return;
        out.push("<" + s[0] + ">\n" + list.map(function (x) { return "- " + x; }).join("\n") + "\n</" + s[0] + ">");
      });
      out.push("<current_state>" + str(state.current_state) + "</current_state>");
      out.push("<next_action>" + str(state.next_action) + "</next_action>");
      out.push("<rules>\n" + RULES.map(function (r) { return "- " + r; }).join("\n") + "\n</rules>");
      out.push("</handoff>");
      return out.join("\n");
    }

    if (t.style === "agentsmd") out.push("# " + (name ? name + " " : "") + "Project Memory");
    else out.push(compact ? t.intro : "# Project handoff" + (name ? ": " + name : ""));
    if (!compact) out.push(t.intro);
    out.push("");
    out.push(heading(t.style, "Goal"));
    out.push(str(state.goal) || "(not captured)");
    out.push("");
    SECTIONS.forEach(function (s) {
      var list = items(state, s[0]).slice(0, maxItems);
      if (!list.length) return;
      out.push(heading(t.style, s[1]));
      list.forEach(function (x) { out.push("- " + x); });
      out.push("");
    });
    out.push(heading(t.style, "Current state"));
    out.push(str(state.current_state) || "(not captured)");
    out.push("");
    out.push(heading(t.style, "Next action"));
    out.push(str(state.next_action) || "(not captured)");
    out.push("");
    out.push(heading(t.style, "Rules for you"));
    RULES.forEach(function (r) { out.push("- " + r); });
    return out.join("\n").replace(/\n{3,}/g, "\n\n").trim() + "\n";
  }

  function estimateTokens(text) { return Math.ceil((text || "").length / 4); }

  function counts(state) {
    var c = {};
    LIST_FIELDS.forEach(function (f) { c[f] = (state[f] || []).length; });
    return c;
  }

  /* Fill a missing/partial state defensively so the UI never crashes on odd model output. */
  function normalize(state) {
    var s = { goal: str(state && state.goal), current_state: str(state && state.current_state), next_action: str(state && state.next_action) };
    LIST_FIELDS.forEach(function (f) { s[f] = Array.isArray(state && state[f]) ? state[f] : []; });
    return s;
  }

  return { TARGETS: TARGETS, LIST_FIELDS: LIST_FIELDS, render: render, estimateTokens: estimateTokens, counts: counts, normalize: normalize };
});
