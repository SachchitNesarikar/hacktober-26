/* Baton content script. Adds a small floating panel to Claude / ChatGPT / Gemini.
 * DOM selectors are the fragile part: these sites change their markup. If capture finds
 * nothing, the panel falls back to your text selection. Fix adapters below, nothing else. */
(function () {
  var H = self.BatonHandoff;
  var host = location.hostname;

  // Return [{role, text}] in page order.
  function scrapeBySelectors(sel, roleOf) {
    // keep only leaf matches: drop any element that wraps another matching element
    var nodes = Array.prototype.slice.call(document.querySelectorAll(sel)).filter(function (n) {
      return !n.querySelector(sel);
    });
    return nodes.map(function (n) { return { role: roleOf(n), text: (n.innerText || "").trim() }; })
      .filter(function (m) { return m.text; });
  }

  var ADAPTERS = {
    claude: {
      match: /(^|\.)claude\.ai$/,
      scrape: function () {
        return scrapeBySelectors('[data-testid="user-message"], .font-claude-message, [data-testid="assistant-message"]',
          function (n) { return n.matches('[data-testid="user-message"]') ? "user" : "assistant"; });
      },
      composer: function () { return document.querySelector('div[contenteditable="true"]'); }
    },
    chatgpt: {
      match: /(^|\.)(chatgpt\.com|chat\.openai\.com)$/,
      scrape: function () {
        return scrapeBySelectors("[data-message-author-role]",
          function (n) { return n.getAttribute("data-message-author-role") === "user" ? "user" : "assistant"; });
      },
      composer: function () { return document.querySelector("#prompt-textarea"); }
    },
    gemini: {
      match: /(^|\.)gemini\.google\.com$/,
      scrape: function () {
        return scrapeBySelectors("user-query, model-response",
          function (n) { return n.tagName.toLowerCase() === "user-query" ? "user" : "assistant"; });
      },
      composer: function () { return document.querySelector('rich-textarea div[contenteditable="true"]') || document.querySelector("rich-textarea"); }
    }
  };
  var adapter = Object.keys(ADAPTERS).map(function (k) { return ADAPTERS[k]; }).filter(function (a) { return a.match.test(host); })[0];
  if (!adapter || !H) return;

  function capture() {
    var msgs = [];
    try { msgs = adapter.scrape(); } catch (e) { msgs = []; }
    if (msgs.length) return { msgs: msgs, source: "page" };
    var sel = String(getSelection() || "").trim();
    return sel ? { msgs: [{ role: "user", text: sel }], source: "selection" } : { msgs: [], source: "none" };
  }

  function insert(text) {
    var c = adapter.composer();
    if (!c) return false;
    c.focus();
    if (c.tagName === "TEXTAREA" || c.tagName === "INPUT") {
      c.value = text; c.dispatchEvent(new Event("input", { bubbles: true })); return true;
    }
    return document.execCommand("insertText", false, text); // works for contenteditable composers
  }

  // ---- UI (shadow DOM so site CSS can't leak in) ----
  var root = document.createElement("div");
  root.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:2147483647;font:13px system-ui,sans-serif";
  var sh = root.attachShadow({ mode: "open" });
  sh.innerHTML = '<style>button,select{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid #888;background:#fff;color:#111;cursor:pointer}' +
    '.fab{background:#c2410c;color:#fff;border:0;font-weight:700;box-shadow:0 2px 8px #0004}' +
    '.p{display:none;width:310px;background:#fffdf8;color:#111;border:1px solid #ccc;border-radius:12px;padding:12px;margin-bottom:8px;box-shadow:0 6px 24px #0004}' +
    '.p.open{display:block}.r{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.s{margin-top:8px;color:#555;min-height:18px}.e{color:#b91c1c}' +
    'table{width:100%;margin-top:8px;border-collapse:collapse}td{padding:1px 0}td:last-child{text-align:right;font-weight:700}</style>' +
    '<div class="p" id="p"><b>Baton</b> <span style="color:#777">hand off this project</span>' +
    '<div class="r"><select id="mode"><option value="single">Single pass</option><option value="agents">Multi-agent</option></select>' +
    '<button id="go">Capture &amp; analyze</button></div><div class="s" id="s"></div><div id="m"></div>' +
    '<div class="r" id="ho" style="display:none"><select id="t"></select><button id="copy">Copy</button><button id="ins">Insert into chat</button></div></div>' +
    '<button class="fab" id="fab">Baton</button>';
  document.documentElement.appendChild(root);
  var $ = function (id) { return sh.getElementById(id); };
  Object.keys(H.TARGETS).forEach(function (k) { var o = document.createElement("option"); o.value = k; o.textContent = H.TARGETS[k].label; $("t").appendChild(o); });
  var state = null;
  function status(msg, err) { $("s").textContent = msg; $("s").className = "s" + (err ? " e" : ""); }
  function handoff() { return H.render(state, $("t").value, { projectName: document.title.replace(/\s*[-|–].*$/, "") }); }

  $("fab").onclick = function () { $("p").classList.toggle("open"); };
  $("go").onclick = function () {
    var cap = capture();
    if (!cap.msgs.length) return status("Couldn't find the conversation on this page. Select the chat text and try again.", true);
    $("go").disabled = true;
    status("Analyzing " + cap.msgs.length + (cap.source === "selection" ? " selected block" : " messages") + " with your local model…");
    chrome.runtime.sendMessage({ type: "analyze", messages: cap.msgs, mode: $("mode").value }, function (res) {
      $("go").disabled = false;
      if (chrome.runtime.lastError || !res) return status("Extension error: " + (chrome.runtime.lastError && chrome.runtime.lastError.message), true);
      if (!res.ok) return status(res.error, true);
      state = H.normalize(res.data.state);
      var c = H.counts(state), rows = [["Decisions", "decisions"], ["Constraints", "constraints"], ["Failed attempts", "failed_attempts"], ["Do not change", "do_not_change"], ["Open tasks", "open_tasks"]];
      $("m").innerHTML = "<table>" + rows.map(function (r) { return "<tr><td>✓ " + r[0] + "</td><td>" + c[r[1]] + "</td></tr>"; }).join("") + "</table>";
      $("ho").style.display = "flex";
      status("Done" + ((res.data.warnings || []).length ? " (" + res.data.warnings.length + " warning(s))" : "") + ". Open a new chat in any AI, then insert.");
    });
  };
  $("copy").onclick = function () { navigator.clipboard.writeText(handoff()).then(function () { status("Copied."); }, function () { status("Clipboard blocked; use Insert.", true); }); };
  $("ins").onclick = function () { status(insert(handoff()) ? "Inserted. Review it, then send." : "No chat box found here; use Copy.", false); };
})();
