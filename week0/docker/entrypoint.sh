#!/bin/sh
# Starts llama-server in the background (downloads the model on first run), then Baton in the foreground.
LLAMA_BIN="${LLAMA_BIN:-/app/llama-server}"
[ -x "$LLAMA_BIN" ] || LLAMA_BIN="$(command -v llama-server || true)"
if [ -z "$LLAMA_BIN" ]; then echo "llama-server not found in this image"; exit 1; fi
"$LLAMA_BIN" -hf "$LLAMA_MODEL" --host 127.0.0.1 --port 8080 -c "$LLAMA_CTX" --jinja $LLAMA_EXTRA &
LLAMA_PID=$!
trap 'kill $LLAMA_PID 2>/dev/null' TERM INT
echo "llama-server started (pid $LLAMA_PID); Baton shows 'model server not running' until the model has downloaded and loaded."
python3 -m baton &
BATON_PID=$!
wait $BATON_PID
kill $LLAMA_PID 2>/dev/null
