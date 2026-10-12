"""Compare models/modes on a conversation with a reference state. Usage:

  python scripts/eval_models.py gemma4:e4b qwen3.5:9b --modes single agents
  python scripts/eval_models.py gemma4:e4b --conversation my_chat.md --reference my_state.json

Scores are a rough, keyword-overlap recall of reference items (not a semantic judge), plus how many
reference *failed attempts* were misfiled as decisions, and wall-clock time. Use it to pick a model
and to see whether multi-agent mode helps; do not quote it as a benchmark."""
import argparse, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from baton import extract, llm, schema            # noqa: E402
from baton.parse import parse_conversation        # noqa: E402

STOP = set("the a an and or of to in on for with is are was be it its this that not never do does did from by as at".split())
SCORED = ["do_not_change", "failed_attempts", "decisions", "constraints", "open_tasks", "known_bugs", "user_preferences"]

def _words(text):
    return {w for w in re.findall(r"[a-z0-9_.\-]+", text.lower()) if len(w) > 2 and w not in STOP}

def _flat(field, item):
    return " ".join(str(v) for v in item.values()) if isinstance(item, dict) else str(item)

def _hit(ref, cands, thresh=0.5):
    rw = _words(ref)
    return bool(rw) and any(len(rw & _words(c)) / len(rw) >= thresh for c in cands)

def score(state, reference):
    """Returns {'recall': {field: 0..1}, 'avg_recall': float, 'misfiled': int}."""
    state, reference = schema.repair(state), schema.repair(reference)
    recall = {}
    for f in SCORED:
        refs = [_flat(f, i) for i in reference[f]]
        if refs:
            got = [_flat(f, i) for i in state[f]]
            recall[f] = sum(_hit(r, got) for r in refs) / len(refs)
    # a failed attempt reported as a decision is the classic small-model mistake
    failed = [_flat("failed_attempts", i) for i in reference["failed_attempts"]]
    misfiled = sum(_hit(d, failed, 0.7) for d in (_flat("decisions", i) for i in state["decisions"]))
    avg = sum(recall.values()) / len(recall) if recall else 0.0
    return {"recall": recall, "avg_recall": avg, "misfiled": misfiled}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--modes", nargs="+", default=["single", "agents"], choices=["single", "agents"])
    ap.add_argument("--conversation", default=os.path.join(ROOT, "demo", "conversation-before.md"))
    ap.add_argument("--reference", default=os.path.join(ROOT, "demo", "project-state.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "eval", "results.md"))
    a = ap.parse_args()
    msgs = parse_conversation(open(a.conversation, encoding="utf-8").read())
    ref = json.load(open(a.reference, encoding="utf-8"))
    rows = []
    for m in a.models:
        for mode in a.modes:
            t0 = time.time()
            try:
                state, _, warns = extract.extract_state(msgs, model=m, mode=mode)
                sc = score(state, ref)
                rows.append((m, mode, f"{sc['avg_recall']*100:.0f}%", sc["misfiled"], len(warns), f"{time.time()-t0:.0f}s",
                             " ".join(f"{k[:6]}={v*100:.0f}" for k, v in sc["recall"].items())))
            except llm.ModelError as e:
                rows.append((m, mode, "ERROR", "-", "-", f"{time.time()-t0:.0f}s", str(e)[:80]))
            print(rows[-1], flush=True)
    head = "| model | mode | avg recall | misfiled | warnings | time | per-field recall % |\n|---|---|---|---|---|---|---|\n"
    table = head + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write("# Model comparison (keyword-overlap recall; rough)\n\n" + table + "\n")
    print("\n" + table + f"\n\nSaved to {a.out}")

if __name__ == "__main__":
    main()
