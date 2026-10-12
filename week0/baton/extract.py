"""Project-state extraction. Two modes: 'single' (one pass per chunk with the whole schema)
and 'agents' (specialists + reconciler, see agents.py). Both finish with a grounding check."""
import json

from . import agents, llm, schema
from .llm import ModelError
from .parse import chunk, render_transcript

SYSTEM = """You are Baton, a meticulous project historian. You read a conversation between a \
developer and an AI assistant and extract the PROJECT STATE, not a summary of the chat.

Rules:
- Only record facts that are stated or clearly implied in the conversation. Never invent files, decisions or bugs.
- "decisions": choices that were made, each with the reason (why).
- "failed_attempts": things tried and abandoned, each with why it failed. Do NOT list these as decisions.
- "do_not_change": things the developer explicitly said must be kept as they are, or that must not be touched.
- "constraints": hard requirements (platform, deadline, licence, budget, stack limits).
- "user_preferences": how the developer likes to work or be answered (style, tooling, conventions).
- "open_tasks": unfinished work. "next_action": the single most useful next step.
- If the conversation later reverses an earlier statement, keep only the latest truth.
- Keep every item to one short sentence. Use empty lists when nothing applies.
Return JSON only, matching the provided schema."""

list_models = llm.list_models

def _single(msgs, model, git_summary, progress):
    chunks = chunk(msgs)
    running = schema.empty_state()
    for i, c in enumerate(chunks, 1):
        prompt = ""
        if running["goal"] or any(running[f] for f in schema.LIST_FIELDS):
            prompt += "PROJECT STATE SO FAR (update it; keep what is still true):\n" + json.dumps(running) + "\n\n"
        if git_summary and i == len(chunks):
            prompt += "GIT FACTS (ground truth for recent_changes and files):\n" + git_summary + "\n\n"
        prompt += f"CONVERSATION PART {i}/{len(chunks)}:\n" + render_transcript(c)
        running = schema.merge([running, schema.repair(llm.chat_json(SYSTEM, prompt, schema.json_schema(), model))])
        if progress:
            progress(i, len(chunks))
    return running

def extract_state(msgs, model=None, git_summary=None, progress=None, mode="single"):
    """Returns (state, trace, warnings)."""
    if mode == "agents":
        return agents.run_agents(msgs, model, git_summary, progress)
    state = _single(msgs, model, git_summary, progress)
    evidence = "\n".join(m["text"] for m in msgs) + "\n" + (git_summary or "")
    state, warnings = agents.ground(state, evidence)
    return state, [{"agent": "Single pass", "items": sum(len(state[f]) for f in schema.LIST_FIELDS), "seconds": None}], warnings
