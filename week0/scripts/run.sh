#!/usr/bin/env bash
# One command, no Docker: start llama.cpp (downloads the model on first run), wait until it's ready, start Baton.
#   macOS: brew install llama.cpp     Windows: use scripts/run.ps1     Linux: install llama.cpp, or use Docker
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${LLAMA_MODEL:-ggml-org/gemma-4-E4B-it-GGUF:Q4_K_M}"
LPORT="${LLAMA_PORT:-8080}"; CTX="${LLAMA_CTX:-8192}"; WAIT="${BATON_WAIT:-1800}"
LOG="${LLAMA_LOG:-llama-server.log}"
command -v llama-server >/dev/null || { echo "llama-server not found. Install: 'brew install llama.cpp' (macOS), 'winget install llama.cpp' (Windows), or see https://github.com/ggml-org/llama.cpp"; exit 1; }
PY="$(command -v python3 || command -v python)" || { echo "Python 3.9+ is required"; exit 1; }
echo "Starting llama-server with $MODEL (first run downloads the model; log: $LOG)"
llama-server -hf "$MODEL" --host 127.0.0.1 --port "$LPORT" -c "$CTX" --jinja ${LLAMA_EXTRA:-} >"$LOG" 2>&1 &
LPID=$!
trap 'kill $LPID 2>/dev/null || true' EXIT INT TERM
ready() { "$PY" - "$LPORT" <<'PYEOF'
import sys, urllib.request
try: sys.exit(0 if urllib.request.urlopen("http://127.0.0.1:%s/health" % sys.argv[1], timeout=2).status == 200 else 1)
except Exception: sys.exit(1)
PYEOF
}
waited=0
until ready; do
  kill -0 "$LPID" 2>/dev/null || { echo "llama-server exited. Last log lines:"; tail -n 20 "$LOG"; exit 1; }
  [ "$waited" -ge "$WAIT" ] && { echo "Timed out waiting for the model."; exit 1; }
  sleep 2; waited=$((waited + 2))
done
echo "Model ready. Starting Baton on http://127.0.0.1:${PORT:-8765}"
BATON_PROVIDER=openai BATON_BASE_URL="http://127.0.0.1:$LPORT/v1" "$PY" -m baton
