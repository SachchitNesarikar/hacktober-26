import json, os, subprocess, tempfile, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import baton.extract as extract
import baton.llm as llm
from baton import agents
from baton import schema, gitctx
from baton.parse import parse_conversation, chunk
from baton.server import ThreadingHTTPServer, Handler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANNED = json.load(open(os.path.join(ROOT, "demo", "project-state.json")))

class FakeOllama(BaseHTTPRequestHandler):
    mode = "good"
    calls = []
    def log_message(self, *a): pass
    def do_GET(self):
        body = json.dumps({"models": [{"name": "gemma3:4b"}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        n = int(self.headers["Content-Length"]); req = json.loads(self.rfile.read(n))
        assert req["format"]["type"] == "object"  # constrained decoding schema is sent
        props = req["format"]["properties"]
        data = {k: v for k, v in CANNED.items() if k in props}
        if FakeOllama.mode == "reconcile_empty" and len(props) > 8: data = {}
        FakeOllama.calls.append(sorted(props))
        content = json.dumps(data) if FakeOllama.mode in ("good", "reconcile_empty") else "I think the answer is: nothing"
        if FakeOllama.mode == "prose": content = "Sure! " + json.dumps(data) + " hope this helps"
        body = json.dumps({"message": {"content": content}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

def serve(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

class ParseTests(unittest.TestCase):
    def test_markdown_roles(self):
        msgs = parse_conversation(open(os.path.join(ROOT, "demo", "conversation-before.md")).read())
        self.assertGreater(len(msgs), 15); self.assertEqual(msgs[0]["role"], "user"); self.assertEqual(msgs[1]["role"], "assistant")
    def test_plain_roles(self):
        self.assertEqual([m["role"] for m in parse_conversation("User: hi\nAssistant: hello\nUser: ok")], ["user", "assistant", "user"])
    def test_json_formats(self):
        a = parse_conversation(json.dumps({"chat_messages": [{"sender": "human", "text": "q"}, {"sender": "assistant", "text": "a"}]}))
        b = parse_conversation(json.dumps([{"role": "user", "content": "q"}, {"role": "assistant", "content": [{"type": "text", "text": "a"}]}]))
        self.assertEqual(len(a), 2); self.assertEqual(b[1]["text"], "a")
    def test_unlabeled_and_empty(self):
        self.assertEqual(len(parse_conversation("just some notes")), 1); self.assertEqual(parse_conversation("  "), [])
    def test_chunking_keeps_all_text(self):
        msgs = [{"role": "user", "text": "x" * 5000} for _ in range(5)] + [{"role": "user", "text": "y" * 20000}]
        self.assertEqual(sum(len(m["text"]) for c in chunk(msgs) for m in c), 45000)

class SchemaTests(unittest.TestCase):
    def test_repair_garbage(self):
        s = schema.repair({"goal": None, "decisions": "just a string", "do_not_change": [{"a": "x", "b": "y"}], "files": [{"path": "a.py"}]})
        self.assertEqual(s["decisions"][0]["what"], "just a string"); self.assertEqual(s["do_not_change"], ["x - y"]); self.assertEqual(schema.repair("nope"), schema.empty_state())
    def test_merge_dedupes_and_latest_scalar_wins(self):
        m = schema.merge([{"goal": "a", "constraints": ["Offline", "x"]}, {"goal": "b", "constraints": ["offline  "]}])
        self.assertEqual(m["goal"], "b"); self.assertEqual(m["constraints"], ["Offline", "x"])

class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.fake = serve(FakeOllama); os.environ.pop("BATON_PROVIDER", None); os.environ["BATON_BASE_URL"] = "http://127.0.0.1:%d" % self.fake.server_port; FakeOllama.mode = "good"
    def tearDown(self): self.fake.shutdown()
    def test_extract_end_to_end(self):
        st, trace, warns = extract.extract_state(parse_conversation("User: a\nAssistant: b"))
        self.assertEqual(st["goal"], CANNED["goal"]); self.assertEqual(len(st["do_not_change"]), 4)
    def test_prose_wrapped_json_tolerated(self):
        FakeOllama.mode = "prose"; self.assertTrue(extract.extract_state(parse_conversation("User: a"))[0]["goal"])
    def test_invalid_json_raises_clean_error(self):
        FakeOllama.mode = "bad"
        with self.assertRaises(llm.ModelError): extract.extract_state(parse_conversation("User: a"))
    def test_unreachable_ollama_message(self):
        os.environ["BATON_BASE_URL"] = "http://127.0.0.1:1"
        with self.assertRaises(llm.ModelError) as c: extract.extract_state(parse_conversation("User: a"))
        self.assertIn("Cannot reach the model server", str(c.exception))

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.fake = serve(FakeOllama); os.environ.pop("BATON_PROVIDER", None); os.environ["BATON_BASE_URL"] = "http://127.0.0.1:%d" % self.fake.server_port
        FakeOllama.mode = "good"; FakeOllama.calls = []
    def tearDown(self): self.fake.shutdown()
    def conv(self): return parse_conversation(open(os.path.join(ROOT, "demo", "conversation-before.md")).read())
    def test_per_agent_model_override(self):
        os.environ["BATON_AGENT_MODELS"] = json.dumps({"Reconciler": "big-model"})
        try:
            seen = []; orig = llm.chat_json
            llm.chat_json = lambda sysm, user, sch, model=None: (seen.append(model), orig(sysm, user, sch, model))[1]
            extract.extract_state(self.conv(), model="small", mode="agents")
        finally:
            llm.chat_json = orig; os.environ.pop("BATON_AGENT_MODELS")
        self.assertEqual(seen.count("big-model"), 1); self.assertEqual(seen.count("small"), 4)
    def test_agents_use_narrow_schemas_and_merge(self):
        st, trace, warns = extract.extract_state(self.conv(), mode="agents")
        narrow = [c for c in FakeOllama.calls if len(c) < 8]
        self.assertEqual(len(narrow), 4)  # one chunk x four specialists
        self.assertTrue(any(c == ["decisions", "failed_attempts"] for c in narrow))
        self.assertEqual([t["agent"] for t in trace][-1], "Reconciler")
        self.assertEqual(len(st["failed_attempts"]), 3); self.assertEqual(len(st["do_not_change"]), 4)
    def test_reconciler_that_drops_items_is_ignored(self):
        FakeOllama.mode = "reconcile_empty"
        st, trace, warns = extract.extract_state(self.conv(), mode="agents")
        self.assertEqual(len(st["decisions"]), 4)
        self.assertTrue(any("Reconciler dropped" in w for w in warns))
    def test_grounding_drops_invented_files(self):
        s = schema.repair({"files": [{"path": "src/lib/db.js", "note": "x"}, {"path": "src/ghost.py", "note": "y"}]})
        s, w = agents.ground(s, "we edited db.js today")
        self.assertEqual([f["path"] for f in s["files"]], ["src/lib/db.js"]); self.assertEqual(len(w), 1)

class OpenAICompatTests(unittest.TestCase):
    """llama.cpp / LM Studio / llamafile style server; first rejects json_schema to test the fallback."""
    def setUp(self):
        outer = self
        outer.seen = []
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def _j(self, code, obj):
                b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
            def do_GET(self): self._j(200, {"data": [{"id": "qwen-local"}]})
            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.seen.append((req.get("response_format", {}).get("type"), self.headers.get("Authorization")))
                if req.get("response_format", {}).get("type") == "json_schema": return self._j(400, {"error": "unsupported"})
                self._j(200, {"choices": [{"message": {"content": "```json\n" + json.dumps(CANNED) + "\n```"}}]})
        self.fake = serve(H)
        os.environ.update(BATON_PROVIDER="openai", BATON_BASE_URL="http://127.0.0.1:%d/v1" % self.fake.server_port, BATON_API_KEY="k123")
    def tearDown(self):
        self.fake.shutdown()
        for k in ("BATON_PROVIDER", "BATON_BASE_URL", "BATON_API_KEY"): os.environ.pop(k, None)
    def test_fallback_key_and_models(self):
        st, _, _ = extract.extract_state(parse_conversation("User: a"))
        self.assertEqual(st["goal"], CANNED["goal"])
        self.assertEqual([t for t, _ in self.seen], ["json_schema", "json_object"]); self.assertEqual(self.seen[0][1], "Bearer k123")
        self.assertEqual(llm.list_models(), ["qwen-local"])

class EvalTests(unittest.TestCase):
    def test_score_and_misfile_detection(self):
        import sys; sys.path.insert(0, os.path.join(ROOT, "scripts")); import eval_models
        perfect = eval_models.score(CANNED, CANNED)
        self.assertEqual(perfect["avg_recall"], 1.0); self.assertEqual(perfect["misfiled"], 0)
        bad = json.loads(json.dumps(CANNED)); bad["decisions"].append({"what": "Workbox generateSW precaching", "why": "x"}); bad["do_not_change"] = []
        r = eval_models.score(bad, CANNED)
        self.assertEqual(r["recall"]["do_not_change"], 0.0); self.assertEqual(r["misfiled"], 1); self.assertLess(r["avg_recall"], 1.0)

class GitTests(unittest.TestCase):
    def test_summary_and_non_repo(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): gitctx.summarize_repo(d)
            run = lambda *a: subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)
            run("init"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
            open(os.path.join(d, "a.txt"), "w").write("1"); run("add", "."); run("commit", "-m", "first commit")
            open(os.path.join(d, "b.txt"), "w").write("2")
            s = gitctx.summarize_repo(d)
            self.assertIn("first commit", s); self.assertIn("b.txt", s)

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.fake = serve(FakeOllama); os.environ.pop("BATON_PROVIDER", None); os.environ["BATON_BASE_URL"] = "http://127.0.0.1:%d" % self.fake.server_port; FakeOllama.mode = "good"
        self.srv = serve(Handler); self.base = "http://127.0.0.1:%d" % self.srv.server_port
    def tearDown(self): self.fake.shutdown(); self.srv.shutdown(); os.environ.pop("BATON_BASE_URL", None)
    def post(self, body):
        req = urllib.request.Request(self.base + "/api/analyze", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    def test_pages_and_health(self):
        self.assertIn(b"Baton", urllib.request.urlopen(self.base + "/").read())
        self.assertIn(b"BatonHandoff", urllib.request.urlopen(self.base + "/handoff.js").read())
        self.assertIn(b"goal", urllib.request.urlopen(self.base + "/demo/project-state.json").read())
        h = json.loads(urllib.request.urlopen(self.base + "/api/health").read()); self.assertTrue(h["ollama"]); self.assertEqual(h["models"], ["gemma3:4b"])
    def test_path_traversal_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as c: urllib.request.urlopen(self.base + "/demo/../../etc/passwd")
        self.assertEqual(c.exception.code, 404)
    def test_analyze_ok_empty_and_bad_repo(self):
        conv = open(os.path.join(ROOT, "demo", "conversation-before.md")).read()
        code, j = self.post({"conversation": conv}); self.assertEqual(code, 200); self.assertEqual(j["counts"]["failed_attempts"], 3)
        self.assertEqual(self.post({"conversation": "  "})[0], 400)
        code, j = self.post({"conversation": conv, "repo_path": "/nonexistent"}); self.assertEqual(code, 400); self.assertIn("git", j["error"].lower())
    def test_agents_mode_and_extension_messages_payload(self):
        code, j = self.post({"messages": [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "yo"}], "mode": "agents"})
        self.assertEqual(code, 200); self.assertEqual(j["mode"], "agents"); self.assertEqual(j["trace"][0]["agent"], "Archivist")
    def test_repo_reads_can_be_disabled(self):
        os.environ["BATON_DISABLE_REPO"] = "1"
        try: self.assertEqual(self.post({"conversation": "User: hi", "repo_path": "/tmp"})[0], 403)
        finally: os.environ.pop("BATON_DISABLE_REPO")
    def test_model_down_returns_502(self):
        os.environ["BATON_BASE_URL"] = "http://127.0.0.1:1"; self.assertEqual(self.post({"conversation": "User: hi"})[0], 502)

if __name__ == "__main__":
    unittest.main()
