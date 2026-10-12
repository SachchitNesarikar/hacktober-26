# TouchGrass — Week 1

A tiny open-AI daily mission app that turns personal goals into one real-world action.

## Files

- `public/index.html` — frontend UI and browser-local completion history/streak.
- `api/mission.js` — mission endpoint with built-in fallback missions and optional Gemma 3 4B via Hugging Face.
- `hatchable.toml` — Hatchable project metadata and optional `HF_TOKEN` secret declaration.

## AI configuration

The app works without an API token using its built-in mission library. To enable generated missions, configure `HF_TOKEN` as a server-side secret in the deployment environment. Never commit the token.

## Local structure

Place this folder as `week1/` inside your `hacktober-26` repository.
