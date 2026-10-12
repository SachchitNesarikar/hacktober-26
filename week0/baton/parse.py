"""Turn many conversation formats into a list of {role, text} messages."""
import json
import re

ROLE_ALIASES = {"human": "user", "user": "user", "you": "user", "me": "user",
                "assistant": "assistant", "claude": "assistant", "chatgpt": "assistant",
                "gpt": "assistant", "gemini": "assistant", "ai": "assistant", "model": "assistant"}

# "User:" / "**Human**:" / "## Assistant" / "### Claude" at line start
_ROLE_LINE = re.compile(
    r"^\s*(?:#{1,4}\s*)?(?:\*\*)?\s*(human|user|you|me|assistant|claude|chatgpt|gpt|gemini|ai|model)\s*(?:\*\*)?\s*(?::|\n|$)\s*(?:\*\*)?",
    re.IGNORECASE)

def _role_of(m):
    author = m.get("author")
    role = m.get("role") or m.get("sender")
    if not role and isinstance(author, dict):
        role = author.get("role")
    return ROLE_ALIASES.get(str(role or "").lower())

def _from_json(obj):
    if isinstance(obj, dict):
        for key in ("chat_messages", "messages", "conversation"):
            if isinstance(obj.get(key), list):
                return _from_json(obj[key])
        if isinstance(obj.get("mapping"), dict):  # ChatGPT export
            nodes = [n for n in obj["mapping"].values() if n.get("message")]
            nodes.sort(key=lambda n: (n["message"].get("create_time") or 0))
            return _from_json([n["message"] for n in nodes])
        return []
    msgs = []
    if isinstance(obj, list):
        for m in obj:
            if not isinstance(m, dict):
                continue
            text = m.get("text") if m.get("text") is not None else m.get("content")
            if isinstance(text, dict):  # ChatGPT: {"parts": [...]}
                text = "\n".join(str(p) for p in text.get("parts", []) if isinstance(p, str))
            if isinstance(text, list):  # content blocks
                text = "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in text)
            role = _role_of(m)
            if role and isinstance(text, str) and text.strip():
                msgs.append({"role": role, "text": text.strip()})
    return msgs

def parse_conversation(raw):
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw[0] in "[{":
        try:
            msgs = _from_json(json.loads(raw))
            if msgs:
                return msgs
        except (ValueError, TypeError):
            pass
    msgs, role, buf = [], None, []
    def flush():
        if role and "".join(buf).strip():
            msgs.append({"role": role, "text": "\n".join(buf).strip()})
    for line in raw.splitlines():
        m = _ROLE_LINE.match(line)
        if m:
            flush()
            role, buf = ROLE_ALIASES[m.group(1).lower()], [line[m.end():]]
        else:
            buf.append(line)
    flush()
    if not msgs:  # unlabeled paste: treat as a single block of context
        msgs = [{"role": "user", "text": raw}]
    return msgs

def render_transcript(msgs):
    return "\n\n".join(f"[{m['role'].upper()}]\n{m['text']}" for m in msgs)

def chunk(msgs, max_chars=9000):
    """Group whole messages into chunks of roughly max_chars; split oversize messages."""
    chunks, cur, size = [], [], 0
    for m in msgs:
        text = m["text"]
        while len(text) > max_chars:
            part, text = text[:max_chars], text[max_chars:]
            if cur:
                chunks.append(cur); cur, size = [], 0
            chunks.append([{"role": m["role"], "text": part}])
        if size + len(text) > max_chars and cur:
            chunks.append(cur); cur, size = [], 0
        cur.append({"role": m["role"], "text": text}); size += len(text)
    if cur:
        chunks.append(cur)
    return chunks
