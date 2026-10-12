"""Project-state schema, JSON Schema for constrained decoding, and validation/repair."""

LIST_FIELDS = [
    "architecture", "decisions", "constraints", "user_preferences", "files",
    "recent_changes", "failed_attempts", "known_bugs", "open_tasks", "do_not_change",
]
STR_FIELDS = ["goal", "current_state", "next_action"]

# Items of these lists are objects; everything else is a plain string.
OBJECT_ITEMS = {
    "decisions": ("what", "why"),
    "failed_attempts": ("what", "why_failed"),
    "files": ("path", "note"),
}

def json_schema(fields=None):
    """JSON Schema for the full state, or for a subset of fields (used by specialist agents)."""
    fields = list(fields) if fields else STR_FIELDS + LIST_FIELDS
    props = {f: {"type": "string"} for f in STR_FIELDS if f in fields}
    for f in [x for x in LIST_FIELDS if x in fields]:
        if f in OBJECT_ITEMS:
            keys = OBJECT_ITEMS[f]
            props[f] = {"type": "array", "items": {
                "type": "object",
                "properties": {k: {"type": "string"} for k in keys},
                "required": list(keys)}}
        else:
            props[f] = {"type": "array", "items": {"type": "string"}}
    return {"type": "object", "properties": props, "required": list(props)}

def empty_state():
    s = {f: "" for f in STR_FIELDS}
    s.update({f: [] for f in LIST_FIELDS})
    return s

def _norm_item(field, item):
    if field in OBJECT_ITEMS:
        keys = OBJECT_ITEMS[field]
        if isinstance(item, dict):
            return {k: str(item.get(k, "")).strip() for k in keys}
        return {keys[0]: str(item).strip(), keys[1]: ""}
    if isinstance(item, dict):  # model returned an object where a string was expected
        item = " - ".join(str(v) for v in item.values() if v)
    return str(item).strip()

def _key(field, item):
    first = item[OBJECT_ITEMS[field][0]] if field in OBJECT_ITEMS else item
    return " ".join(first.lower().split())

def repair(raw):
    """Coerce arbitrary model output into a valid project state. Never raises."""
    out = empty_state()
    if not isinstance(raw, dict):
        return out
    for f in STR_FIELDS:
        v = raw.get(f, "")
        out[f] = v.strip() if isinstance(v, str) else str(v or "").strip()
    for f in LIST_FIELDS:
        v = raw.get(f, [])
        if isinstance(v, (str, dict)):
            v = [v]
        if not isinstance(v, list):
            v = []
        seen, items = set(), []
        for it in v:
            it = _norm_item(f, it)
            k = _key(f, it)
            if k and k not in seen:
                seen.add(k)
                items.append(it)
        out[f] = items
    return out

def merge(states):
    """Merge per-chunk states: later chunks win on scalars, lists are de-duplicated unions."""
    out = empty_state()
    for st in states:
        st = repair(st)
        for f in STR_FIELDS:
            if st[f]:
                out[f] = st[f]
        for f in LIST_FIELDS:
            have = {_key(f, i) for i in out[f]}
            for it in st[f]:
                if _key(f, it) not in have:
                    out[f].append(it)
                    have.add(_key(f, it))
    return out

def counts(state):
    return {f: len(state.get(f, [])) for f in LIST_FIELDS}
