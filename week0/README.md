# Baton

**When one AI runs out, the project shouldn't.**
Baton extracts the *state* of your project from an AI-assistant conversation using a **local open-weight model** and turns it into a compact handoff any other AI can continue from.

```
conversation  ->  local open-weight model (Gemma via Ollama)  ->  structured project state  ->  handoff for Claude / Gemini / GPT / local model / AGENTS.md
```

## Story
I was building an offline expense tracker for a friend (a bakery owner with bad signal at the market) with an AI assistant, and hit its usage limit mid-task. What I lost wasn't the chat. It was the project's evolving context: decisions and their reasons, experiments that failed, rules like "money is integer cents, never floats," and the half-finished task. A new AI would repeat the failures and "fix" the things I had said to leave alone.

Baton keeps that context out of any one provider's hands and never requires a cloud service to do it.

## What it does
1. **Ingest** Claude/ChatGPT exports (JSON), markdown or plain text (`Human:` / `Assistant:`), or an unlabeled paste.
2. **Extract** project state with a local model, schema-constrained (decisions + why, failed attempts + why, constraints, do-not-change rules, bugs, open tasks, and next action). Long chats are processed in chunks with a running state so later messages can reverse earlier ones.
3. **Optionally ground in Git:** point at a local repo and include its recent commits and uncommitted changes.
4. **Hand off:** render for Claude (XML), Gemini, GPT, a compact variant for small local models, or an `AGENTS.md`. Copy or download.

The memory panel shows what survived (counts and inspectable lists) so you can sanity-check before handing off.

**Testing, deployment, and model picks: see [`TESTING_AND_DEPLOY.md`](TESTING_AND_DEPLOY.md).**

## Browser extension (no more pasting)
`extension/` is a Manifest V3 extension for **claude.ai, chatgpt.com, and gemini.google.com**. It adds a floating **Baton** button:
*Capture & analyze* reads the open conversation, sends it to your local Baton server (`python -m baton`), shows the project-memory counts, and *Insert into chat* drops the handoff into the composer of a **new** chat in any of the three. Install: `chrome://extensions` -> Developer mode -> **Load unpacked** -> select `extension/`.

## Models: with and without Ollama
Baton works with any server that can chat with an open-weight model and return JSON. Pick whichever runs on your device:

| Device / situation | Use | Config |
|---|---|---|
| Mac, Windows, Linux with Ollama | Ollama | default |
| No Ollama support (older OS, unsupported GPU/CPU, locked-down PC) | **llamafile** (one executable + a GGUF file) or **llama.cpp** `llama-server` | `BATON_PROVIDER=openai BATON_BASE_URL=http://127.0.0.1:8080/v1` |
| Prefer a GUI | **LM Studio** / **Jan** local server | `BATON_PROVIDER=openai BATON_BASE_URL=http://127.0.0.1:1234/v1` |
| Android / tablet / Chromebook | Run Baton + llama.cpp on a laptop or home PC and open it over your LAN (`HOST=0.0.0.0`, trusted network only), or llama.cpp in Termux on a recent Android phone with a ~1-3B model | same as above |
| Weak hardware, don't mind leaving the machine | A **hosted open-weight model** (Together, Groq, HF Inference...) via its OpenAI-compatible URL | add `BATON_API_KEY=...` |

Small models (1-4B) do better in **Multi-agent** mode, where four specialists (Archivist, Rules keeper, Decision analyst, Work tracker) each fill a few fields; a Reconciler fixes misfiled or duplicate items; and a deterministic check removes filenames that never appear in the chat or git.

## Quick start (llama.cpp, model downloads itself)
The scripts and Docker files below use **llama.cpp**; the model (Gemma 4 E4B, Q4_K_M) is pulled from Hugging Face on first start (several GB).

**A. One command, no Docker**
```bash
brew install llama.cpp            # macOS   (Windows: winget install llama.cpp)
bash scripts/run.sh               # Windows: powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```
Starts `llama-server -hf <model>`, waits until it is ready, then starts Baton at http://127.0.0.1:8765.

**B. Docker Compose (CPU; add `-f docker-compose.gpu.yml` for NVIDIA)**
```bash
docker compose up -d --build      # open http://localhost:8765; the first start downloads the model
```

**C. Single container (Render / Fly / VPS):** `Dockerfile.allinone` runs llama.cpp and Baton together; mount a persistent disk at `/root/.cache/llama.cpp`.

Change the model with `LLAMA_MODEL=<hf-repo>:<quant>` (e.g. `ggml-org/gemma-4-E4B-it-GGUF:Q8_0`). **Ollama still works:** `ollama pull gemma4:e4b && python -m baton`.

## Run without scripts (Python 3.9+; no pip packages)
```bash
python -m baton    # Ollama by default; for llama.cpp set BATON_PROVIDER=openai BATON_BASE_URL=http://127.0.0.1:8080/v1
```
Open the page, click **Load demo** to see the full flow instantly, or paste your own conversation and **Analyze**.

## Public demo (static, no model)
`python scripts/build_static.py` writes `docs/`. Enable GitHub Pages (Settings, Pages, deploy from `/docs`) or deploy the repo with the included `Dockerfile` / `render.yaml`. A hosted copy cannot run a local model, so it runs in **demo mode**: Load demo + handoff generation work; Analyze is disabled and says why.

## Demo data
`demo/conversation-before.md` (input), `demo/project-state.json`, and `demo/generated-handoff-{claude,gemma}.md`.
Regenerate the handoffs with `node scripts/gen-demo-handoffs.js`.

## Tests
```bash
python -m unittest discover -s tests -v    # parser, schema, extraction + agents (mock model servers), OpenAI-compatible fallback, git, HTTP
node tests/handoff.test.js                 # handoff renderer
```

## Architecture
| File | Role |
|---|---|
| `baton/parse.py` | conversation formats -> messages, chunking |
| `baton/schema.py` | project-state schema, JSON Schema for constrained decoding, repair + merge |
| `baton/llm.py` | model backends: Ollama and any OpenAI-compatible server |
| `baton/extract.py` | single-pass map-reduce extraction + grounding |
| `baton/agents.py` | multi-agent mode: specialists, reconciler, grounding check |
| `extension/` | MV3 browser extension (Claude, ChatGPT, Gemini) |
| `baton/gitctx.py` | optional repo summary |
| `baton/server.py` | stdlib HTTP server (`/api/health`, `/api/analyze`) |
| `web/` | single-page UI + `handoff.js` renderer (shared by browser and tests) |

## Privacy
In local mode, conversations go only to your own Ollama instance. The server binds to localhost by default. Don't expose it publicly; the `repo_path` option reads local repositories.

## Next steps
In-browser inference with WebLLM or transformers.js (needs WebGPU and a bundled build; MV3 forbids remote code), a Claude Code/Codex session-file importer, a verify step where the receiving AI restates the state for you to confirm, and selector tests against saved page snapshots.

## Limitations
Extraction quality depends on the model (small models miss items; review the memory panel). No browser extension, no auth, and no persistence. The UI does not yet allow editing individual items.

## Credits, license
MIT (see `LICENSE`). Independent implementation; see `NOTICE.md` for related projects and what is original.
