// Talks to the local Baton server. Done here (not in the content script) so the chat site's CSP
// and CORS rules don't apply; the host_permissions in manifest.json allow localhost.
const DEFAULT_SERVER = "http://127.0.0.1:8765";

async function serverUrl() {
  const { server } = await chrome.storage.sync.get("server");
  return (server || DEFAULT_SERVER).replace(/\/+$/, "");
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "analyze") return;
  (async () => {
    try {
      const base = await serverUrl();
      const r = await fetch(base + "/api/analyze", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: msg.messages, mode: msg.mode })
      });
      const j = await r.json();
      sendResponse(r.ok ? { ok: true, data: j } : { ok: false, error: j.error || ("HTTP " + r.status) });
    } catch (e) {
      sendResponse({ ok: false, error: "Can't reach Baton at " + (await serverUrl()) + ". Is `python -m baton` running? (" + e.message + ")" });
    }
  })();
  return true; // async response
});
