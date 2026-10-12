# Baton: test, deploy, and pick models

## 1. Fast checks (2 minutes, no model needed)
```bash
python -m unittest discover -s tests -v      # 24 tests, uses mock model servers
node tests/handoff.test.js                   # handoff renderer
python -m baton                              # open http://127.0.0.1:8765, click "Load demo"
```
Expect: the memory panel fills (4 decisions, 3 failed attempts, 4 do-not-change...), and the handoff box shows text for each target.

## 2. Real-model test (the one that matters)
1. Easiest: `bash scripts/run.sh` (llama.cpp, auto-downloads the model), then skip to step 3. Or start a model server yourself (pick one):
   ```bash
   ollama pull gemma4:e4b && ollama serve        # Ollama
   # or llama.cpp / llamafile / LM Studio:
   BATON_PROVIDER=openai BATON_BASE_URL=http://127.0.0.1:8080/v1 python -m baton
   ```
2. `python -m baton`. The pill at the top should say **model ready (ollama)**. If it says "model server not running", the URL or port is wrong.
3. Click **Load demo**, then **Analyze conversation** (the demo text is already loaded in the box). Compare the extracted memory with `demo/project-state.json`.
4. Repeat with **Multi-agent**. Check the trace lines under the button and any warnings.
5. Git grounding: put a real repo path in "Local git repo path", analyze, and confirm the final line says "+ git history".
6. Paste a real, long chat of your own. Open **Do not change** and **Failed attempts**: these are the lists that matter most. Fix your model choice if they are empty or wrong.

### Compare models and modes automatically
```bash
python scripts/eval_models.py gemma4:e4b qwen3.5:9b --modes single agents
```
Prints and saves `eval/results.md`: rough keyword-overlap recall against the reference state, how often a failed attempt was misfiled as a decision, and time.
It is a sanity check, not a benchmark: it scores against the demo's hand-written reference and uses keyword overlap, not a semantic judge. Add `--conversation my.md --reference my_state.json` to score your own chat.

## 3. Models to try
Tags change; confirm with `ollama list` / the Ollama library before pulling.

| Goal | Try | Why / source notes |
|---|---|---|
| Default, ~8 GB VRAM or 16 GB RAM | `gemma4:e4b` | Gemma 4 (April 2026, Apache 2.0) advertises native JSON output and system prompts. Good open-source story for the challenge. |
| Very small / CPU / phone-class | `gemma4:e2b`, `phi4-mini` | Expect misses; use **Multi-agent** and read the memory panel. |
| Best JSON reliability (reported) | `qwen3.6:27b`, or the 35B-A3B MoE | One May 2026 guide ranks Qwen 3.6 top for JSON-schema output. Needs ~17-22 GB. |
| Mid-size alternative | `qwen3.5:9b`, `granite4.2:8b` | Qwen 3.5 small sizes and IBM Granite are reported to handle tools/JSON. |
| Quality ceiling, big GPU | `gemma4:31b` (~20 GB) | Largest local Gemma 4. |

Tips
- Qwen-style "thinking" models can be slow or noisy: set `BATON_THINK=false` to turn the reasoning trace off in Ollama.
- Mix models per agent, e.g. a bigger one for the hard jobs:
  ```bash
  BATON_MODEL=gemma4:e4b \
  BATON_AGENT_MODELS='{"Decision analyst":"qwen3.6:27b","Reconciler":"qwen3.6:27b"}' python -m baton
  ```
- On weak hardware set `BATON_WORKERS=1` so specialists run one at a time.

## 4. Browser extension test
1. `python -m baton` running. `chrome://extensions` -> Developer mode -> **Load unpacked** -> `extension/`.
2. Open a long chat on claude.ai, then chatgpt.com, then gemini.google.com. Click the orange **Baton** button -> **Capture & analyze**.
3. If it says it can't find the conversation, the selectors in `extension/content.js` (one `ADAPTERS` entry per site) are stale: inspect a message element and update its selector. Selecting text first also works as a fallback.
4. Open a *new* chat in another AI -> Baton -> **Insert into chat** (or **Copy** and paste). Ask: "What is the next task and what must you not change?"
5. After editing `web/handoff.js`, run `python scripts/build_extension.py` to re-sync and re-zip it.

## 5. Deploy
**A. Public static demo (recommended for the challenge).** Judges can try it with no install; Analyze is disabled there and says why.
```bash
python scripts/build_static.py              # writes docs/
git init && git add . && git commit -m "Baton" && git remote add origin <your-repo-url> && git push -u origin main
```
GitHub: Settings -> Pages -> Deploy from branch `main`, folder `/docs`. Vercel/Netlify: publish directory `docs`, no build command.

**B. Docker, demo-only on Render/Fly/etc.** `Dockerfile` + `render.yaml` serve the UI; there is no model there, so it behaves like (A). It sets `BATON_DISABLE_REPO=1` so the public server can't read repos.

**C. Self-hosted llama.cpp + Baton**
```bash
docker compose up -d --build          # GPU: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```
Open http://localhost:8765. The first start downloads the model into the `llama-cache` volume; until then the page says "model server not running". No auth: keep it on a trusted network.
Single-container hosts: build `Dockerfile.allinone` and attach a persistent disk at `/root/.cache/llama.cpp`. A free CPU host will be very slow and may not fit the model.

**Automatic Pages deploy:** `.github/workflows/ci-pages.yml` runs the tests and publishes `docs/`. In the repo set Settings -> Pages -> Source: **GitHub Actions**.

**D. Local only (the privacy story).** `python -m baton`; conversations only go to your own model server. `HOST=0.0.0.0` exposes it to your LAN, nothing more.

## 6. Pre-submission checklist
- [ ] Ran a real model end to end and replaced `demo/project-state.json` with real output (then `node scripts/gen-demo-handoffs.js` and `python scripts/build_static.py`)
- [ ] Recorded the demo (see `DEMO_SCRIPT.md`) and saved `eval/results.md` for the write-up
- [ ] Tested the extension on at least one site, or say in the post that it is a prototype
- [ ] Repo public, MIT license and `NOTICE.md` present, Pages link works
- [ ] DEV post drafted from `DEV_POST.md`, with your own story in the "friend" section

## 7. Troubleshooting
| Symptom | Fix |
|---|---|
| "Cannot reach the model server" | Start Ollama/llama.cpp; check `BATON_BASE_URL` (Ollama `:11434`, llama.cpp `:8080/v1`, LM Studio `:1234/v1`). |
| "The model did not return valid JSON" | Use a bigger model, try Multi-agent, or set `BATON_THINK=false`. |
| Empty lists for a long chat | Small context: ask for a model with larger context or lower `chunk(max_chars)` in `baton/parse.py`. |
| Very slow | CPU only: use `gemma4:e2b`, `BATON_WORKERS=1`, Single pass. |
| Extension: "Can't reach Baton" | Server not running, or change the URL in the extension options and grant its host permission. |
