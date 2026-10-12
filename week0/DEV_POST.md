# DEV submission draft (edit freely, make it yours)

**Title:** I hit my AI usage limit mid-project, so I built Baton: a project-state handoff that runs on a local open model

## The friend
Your friend here is a *developer-you at 11pm* and, in the demo, Maya, a bakery owner whose expense tracker I was building
when my assistant ran out of messages. (Replace this section with your real story. It is the part judges weigh most.)

## The problem
After hours with an AI assistant, the valuable thing isn't the chat. It's the project's state: what we decided and why,
what we tried and abandoned, what must never change, what's half done. Switching AI means re-explaining all of it, and
the new AI happily repeats failed experiments or "improves" the one thing I said not to touch.

## The idea
Don't export the conversation. Extract the state.
`conversation -> open-weight model -> structured project state -> handoff for any AI`

## How it works
- Parse Claude/ChatGPT/Gemini exports or pasted text, chunk long sessions.
- Gemma (via Ollama) reads each chunk with the running state, constrained to a JSON schema, so later messages can reverse earlier ones.
- Optional: real `git log` / `git status` is fed in so recent changes are grounded in facts.
- Render a handoff tuned for Claude (XML), Gemini/GPT (markdown), a compact one for small local models, or an AGENTS.md.

## Why open + local matters
Your project history contains your architecture, your mistakes and sometimes your secrets. Extraction runs on your machine;
nothing is sent to a third party just to preserve your own context. And because the schema and renderers are plain code, you can
add a target in ten lines.

## Demo
(Embed the GIF / link the static demo: `docs/` on GitHub Pages.) Be honest about what the hosted page is: a demo of a
reference state; live extraction needs the local model.

## What I'd do next
Evaluate extraction quality across model sizes, add importers for Claude Code/Codex session files, and a "verify" pass where the
new AI restates the state and the user confirms.

## Repo
<link>. MIT. See NOTICE.md for upstream/inspiration.
