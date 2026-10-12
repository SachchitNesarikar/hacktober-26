"""Multi-agent extraction. Small local models do better with one narrow job than with a 13-field
form, so the work is split between specialists, then a reconciler and a deterministic grounding
check clean up. Every agent is the same open-weight model with a different brief."""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from . import llm, schema
from .parse import chunk, render_transcript

COMMON = ("You read a conversation between a developer and an AI assistant. Record only facts stated or clearly "
          "implied in it; never invent. If a later message reverses an earlier one, keep only the latest truth. "
          "One short sentence per item; use empty lists when nothing applies. Return JSON only, matching the schema.\n")

AGENTS = [
    {"name": "Archivist", "fields": ["goal", "architecture", "files", "current_state"],
     "brief": "You are the Archivist. Capture what the project is for, how it is built, which files/components exist "
              "and what each does, and the honest current state of the work."},
    {"name": "Rules keeper", "fields": ["constraints", "user_preferences", "do_not_change"],
     "brief": "You are the Rules keeper. Capture hard constraints (stack, platform, deadline, licence), the developer's "
              "working preferences, and anything the developer said must NOT be changed or touched. Be strict: "
              "do_not_change is only for explicit prohibitions or invariants."},
    {"name": "Decision analyst", "fields": ["decisions", "failed_attempts"],
     "brief": "You are the Decision analyst. Capture choices that were MADE (with the reason) and approaches that were "
              "TRIED AND ABANDONED (with why they failed). An abandoned approach is never a decision."},
    {"name": "Work tracker", "fields": ["recent_changes", "known_bugs", "open_tasks", "next_action"],
     "brief": "You are the Work tracker. Capture what changed recently, bugs found and not yet fixed, unfinished work, "
              "and the single most useful next action. Use GIT FACTS, when provided, as ground truth for changes."},
]

def agent_models():
    """BATON_AGENT_MODELS='{"Decision analyst":"qwen3.6:27b","Reconciler":"gemma4:31b"}' lets a bigger model
    take the hard jobs while small ones do the rest."""
    try:
        m = json.loads(os.environ.get("BATON_AGENT_MODELS", "") or "{}")
        return m if isinstance(m, dict) else {}
    except ValueError:
        return {}

def _run_agent(agent, chunks, git_summary, model, progress):
    model = agent_models().get(agent["name"], model)
    fields = agent["fields"]
    running = {f: ([] if f in schema.LIST_FIELDS else "") for f in fields}
    system = COMMON + agent["brief"]
    t0 = time.time()
    for i, c in enumerate(chunks, 1):
        prompt = ""
        if any(running.values()):
            prompt += "YOUR NOTES SO FAR (update; keep what is still true):\n" + json.dumps(running) + "\n\n"
        if git_summary and i == len(chunks) and agent["name"] in ("Work tracker", "Archivist"):
            prompt += "GIT FACTS:\n" + git_summary + "\n\n"
        prompt += f"CONVERSATION PART {i}/{len(chunks)}:\n" + render_transcript(c)
        out = schema.repair(llm.chat_json(system, prompt, schema.json_schema(fields), model))
        merged = schema.merge([{**schema.empty_state(), **running}, out])
        running = {f: merged[f] for f in fields}
        progress(agent["name"])
    return agent["name"], running, round(time.time() - t0, 1)

RECONCILE_SYSTEM = ("You are the Reconciler. Below is a project state compiled by several specialists. Clean it up WITHOUT "
                    "adding new facts: move items that are in the wrong list (e.g. an abandoned approach under decisions), "
                    "merge duplicates, and when two items contradict keep the later/more specific one. Do not drop items "
                    "unless they are duplicates or contradicted. Return the complete state as JSON matching the schema.")

def _total(state):
    return sum(len(state[f]) for f in schema.LIST_FIELDS)

def ground(state, evidence_text):
    """Deterministic check: drop 'files' whose path never appears in the conversation or git facts."""
    warnings, hay = [], evidence_text.lower()
    kept = []
    for f in state["files"]:
        path = f["path"].strip().rstrip("/")
        base = os.path.basename(path)
        if path and (path.lower() in hay or (base and base.lower() in hay)):
            kept.append(f)
        else:
            warnings.append(f"Dropped file '{f['path']}': not found in the conversation or git facts.")
    state["files"] = kept
    return state, warnings

def run_agents(msgs, model=None, git_summary=None, progress=None, workers=None):
    chunks = chunk(msgs)
    workers = workers or int(os.environ.get("BATON_WORKERS", "2"))
    total = len(AGENTS) * len(chunks) + 1
    done = {"n": 0}
    def tick(_name):
        done["n"] += 1
        if progress:
            progress(done["n"], total)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        results = list(ex.map(lambda a: _run_agent(a, chunks, git_summary, model, tick), AGENTS))
    trace, parts = [], []
    for name, part, secs in results:
        parts.append({**schema.empty_state(), **part})
        trace.append({"agent": name, "items": sum(len(v) if isinstance(v, list) else int(bool(v)) for v in part.values()), "seconds": secs})
    state = schema.merge(parts)
    warnings = []
    before = _total(state)
    try:
        rec = schema.repair(llm.chat_json(RECONCILE_SYSTEM, json.dumps(state), schema.json_schema(), agent_models().get("Reconciler", model)))
        if before and _total(rec) < 0.7 * before:
            warnings.append("Reconciler dropped too many items; kept the specialists' original state.")
        else:
            for f in schema.STR_FIELDS:
                rec[f] = rec[f] or state[f]
            state = rec
        trace.append({"agent": "Reconciler", "items": _total(state), "seconds": None})
    except llm.ModelError as e:
        warnings.append(f"Reconciler skipped: {e}")
    if progress:
        progress(total, total)
    evidence = "\n".join(m["text"] for m in msgs) + "\n" + (git_summary or "")
    state, w = ground(state, evidence)
    return state, trace, warnings + w
