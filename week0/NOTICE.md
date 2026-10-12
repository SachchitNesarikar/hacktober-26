# Attribution and originality

Baton is an **independent implementation**. No source code, README text, screenshots or branding
from any other project was copied.

While scoping the idea I looked at existing tools in the same space, for problem framing only:

| Project | What it does | Relationship to Baton |
|---|---|---|
| [prateekg7/Context-Bridge](https://github.com/prateekg7/Context-Bridge) (MIT) | Compresses a transcript into a structured context block via an MCP server, using cloud LLM providers | Closest in spirit. Baton shares the broad idea of "structured context, not a transcript" but no code. |
| [HacksonClark/handoff](https://github.com/HacksonClark/handoff) | CLI that moves sessions between coding agents' local stores | Different approach: raw session transfer. |
| [open-grove/handoff](https://github.com/open-grove/handoff) | Shareable HANDOFF.md from agent sessions | Different approach: prepared handoff documents. |
| [abubakargcx-dev/Context-Carry-Extension](https://github.com/abubakargcx-dev/Context-Carry-Extension) | Browser extension capturing chats, summarising with your own cloud API key | Different approach: browser capture + cloud summarisers. |

Licences other than Context-Bridge's were not verified. Because nothing was reused, none apply to this repository.

## What is original here
- A project-state schema that separates **decisions**, **failed attempts**, **constraints** and **do-not-change** rules (and treats later reversals as superseding earlier statements).
- Map-reduce extraction with a running state and schema-constrained decoding against a **local open-weight model** (Ollama).
- Optional Git grounding (recent commits, uncommitted changes).
- Target-specific handoff renderers with explicit "rules for the receiving AI".

Baton uses open-weight models (default: Gemma via Ollama) at run time. Model weights have their own licences/terms
(e.g. the Gemma terms of use); they are not distributed in this repository.
