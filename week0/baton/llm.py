"""Model backends. Baton only needs 'chat with a JSON schema', so it supports:

  BATON_PROVIDER=ollama   (default)  Ollama's native /api/chat
  BATON_PROVIDER=openai              any OpenAI-compatible server: llama.cpp `llama-server`,
                                     llamafile, LM Studio, Jan, vLLM, or a hosted open-weight
                                     endpoint (Together, Groq, HF Inference...) with BATON_API_KEY.

Configuration is environment-only on purpose: the HTTP API never accepts a URL to call (no SSRF).
"""
import json
import os
import urllib.error
import urllib.request

class ModelError(RuntimeError):
    pass

def cfg():
    provider = os.environ.get("BATON_PROVIDER", "ollama").lower()
    default_url = "http://localhost:11434" if provider == "ollama" else "http://127.0.0.1:8080/v1"
    return {
        "provider": provider,
        "base_url": os.environ.get("BATON_BASE_URL") or (os.environ.get("OLLAMA_URL") if provider == "ollama" else None) or default_url,
        "api_key": os.environ.get("BATON_API_KEY", ""),
        "model": os.environ.get("BATON_MODEL", "gemma4:e4b" if provider == "ollama" else "local-model"),
    }

def _http(method, url, payload=None, key="", timeout=300):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(),
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        err = ModelError(f"Model server returned HTTP {e.code}: {detail}")
        err.code = e.code
        raise err
    except urllib.error.URLError as e:
        raise ModelError(f"Cannot reach the model server at {url}: {e.reason}. "
                         "Start it (see README: Ollama, llama.cpp, LM Studio...) or fix BATON_BASE_URL.")
    except (TimeoutError, OSError) as e:
        raise ModelError(f"Model request failed: {e}")

def list_models():
    c = cfg()
    if c["provider"] == "ollama":
        return [m["name"] for m in _http("GET", c["base_url"] + "/api/tags", key=c["api_key"], timeout=3).get("models", [])]
    return [m["id"] for m in _http("GET", c["base_url"] + "/models", key=c["api_key"], timeout=3).get("data", [])]

def parse_json_loose(content):
    try:
        return json.loads(content)
    except ValueError:
        s, e = content.find("{"), content.rfind("}")  # tolerate prose or code fences around the JSON
        if s != -1 and e > s:
            try:
                return json.loads(content[s:e + 1])
            except ValueError:
                pass
    raise ModelError("The model did not return valid JSON. Try a larger model, or re-run.")

def chat_json(system, user, schema, model=None):
    c = cfg()
    model = model or c["model"]
    if c["provider"] == "ollama":
        payload = {"model": model, "stream": False, "format": schema,
                   "options": {"temperature": 0.1, "num_ctx": 8192},
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if os.environ.get("BATON_THINK", "").lower() == "false":
            payload["think"] = False  # skip reasoning traces on thinking models (Qwen3.x etc.); faster, JSON stays clean
        resp = _http("POST", c["base_url"] + "/api/chat", payload, key=c["api_key"])
        return parse_json_loose((resp.get("message") or {}).get("content", ""))
    # OpenAI-compatible: try strict schema, then json_object, then prompt-only.
    hint = "\n\nReply with JSON only, matching this JSON Schema:\n" + json.dumps(schema)
    attempts = [
        ({"type": "json_schema", "json_schema": {"name": "project_state", "schema": schema, "strict": False}}, ""),
        ({"type": "json_object"}, hint),
        (None, hint),
    ]
    last = None
    for fmt, extra in attempts:
        body = {"model": model, "temperature": 0.1,
                "messages": [{"role": "system", "content": system + extra}, {"role": "user", "content": user}]}
        if fmt:
            body["response_format"] = fmt
        try:
            resp = _http("POST", c["base_url"] + "/chat/completions", body, key=c["api_key"])
        except ModelError as e:
            if getattr(e, "code", None) in (400, 422):  # server doesn't support this response_format
                last = e
                continue
            raise
        return parse_json_loose(resp["choices"][0]["message"]["content"] or "")
    raise last
