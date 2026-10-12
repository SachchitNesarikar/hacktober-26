"""Tiny dependency-free HTTP server: serves the UI and exposes /api/* to the extractor."""
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import extract, gitctx, llm, schema
from .parse import parse_conversation

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
DEMO = os.path.join(ROOT, "demo")
MAX_BODY = 2_000_000

class Handler(BaseHTTPRequestHandler):
    server_version = "Baton/0.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[baton] " + fmt % args + "\n")

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _file(self, base, rel):
        path = os.path.normpath(os.path.join(base, rel))
        if not path.startswith(base) or not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype + ("; charset=utf-8" if ctype.startswith("text") or "javascript" in ctype else ""))

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/health":
            try:
                models = extract.list_models()
                return self._send(200, {"ok": True, "ollama": True, "models": models, "provider": llm.cfg()["provider"],
                                        "default_model": llm.cfg()["model"]})
            except Exception as e:
                return self._send(200, {"ok": True, "ollama": False, "models": [], "provider": llm.cfg()["provider"],
                                        "default_model": llm.cfg()["model"], "detail": str(e)})
        if p.startswith("/demo/"):
            return self._file(DEMO, p[len("/demo/"):])
        self._file(WEB, "index.html" if p == "/" else p.lstrip("/"))

    def do_POST(self):
        if self.path != "/api/analyze":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n > MAX_BODY:
                return self._send(413, {"error": "Conversation too large (2 MB max)."})
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, {"error": "Invalid JSON body."})
        if isinstance(body.get("messages"), list):  # already-parsed messages (browser extension)
            msgs = [{"role": "assistant" if m.get("role") == "assistant" else "user", "text": str(m.get("text", "")).strip()}
                    for m in body["messages"] if isinstance(m, dict) and str(m.get("text", "")).strip()]
        else:
            msgs = parse_conversation(body.get("conversation", ""))
        if not msgs:
            return self._send(400, {"error": "Paste a conversation first."})
        git_summary = None
        repo = (body.get("repo_path") or "").strip()
        if repo and os.environ.get("BATON_DISABLE_REPO") == "1":
            return self._send(403, {"error": "Reading repositories is disabled on this server."})
        if repo:
            try:
                git_summary = gitctx.summarize_repo(repo)
            except ValueError as e:
                return self._send(400, {"error": str(e)})
        try:
            mode = "agents" if body.get("mode") == "agents" else "single"
            state, trace, warnings = extract.extract_state(msgs, model=body.get("model") or None,
                                                           git_summary=git_summary, mode=mode)
        except llm.ModelError as e:
            return self._send(502, {"error": str(e)})
        self._send(200, {"state": state, "counts": schema.counts(state), "messages": len(msgs),
                         "git_used": bool(git_summary), "mode": mode, "trace": trace, "warnings": warnings})

def main(argv=None):
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    srv = ThreadingHTTPServer((host, port), Handler)
    c = llm.cfg()
    print(f"Baton running at http://{host}:{port}  (provider: {c['provider']}, model: {c['model']}, server: {c['base_url']})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
