# 2–3 minute demo script

**0:00 Hook (15s)** "I was building an expense tracker for my friend Maya when my AI assistant hit its limit. Two hours of decisions, dead ends and rules, gone."

**0:15 The mess (20s)** Open Baton, click *Load demo* (or paste a real long chat). Scroll the 20-message conversation: "Somewhere in here: cents not floats, never touch the CSV columns, three things we tried that failed."

**0:35 Extract (40s)** Local mode: click *Analyze conversation*. Show Ollama running locally and the model name in the dropdown. "Gemma reads it on my laptop. Nothing leaves this machine." Cards fill in: 4 decisions, 3 failed attempts, 4 do-not-change rules, 1 bug.

**1:15 Inspect (30s)** Click *Do not change* and *Failed attempts*. "This is state, not a summary. Notice it knows Workbox failed and *why*."

**1:45 Handoff (30s)** Choose *Claude*, then *Local Gemma (compact)*. Show the output and token estimate. Copy.

**2:15 Payoff (30s)** Paste into a fresh chat. Ask "What should we do next, and what must you not touch?" It answers: the recurring-edit task, plus cents/CSV/no-Workbox. 

**2:45 Close (10s)** "The project's memory belongs to you, not to whichever AI you were using. Baton is MIT and runs locally."
