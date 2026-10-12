# Windows: start llama.cpp (downloads the model on first run), wait until ready, start Baton.
#   winget install llama.cpp      then:   powershell -ExecutionPolicy Bypass -File scripts\run.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$model = if ($env:LLAMA_MODEL) { $env:LLAMA_MODEL } else { "ggml-org/gemma-4-E4B-it-GGUF:Q4_K_M" }
$port  = if ($env:LLAMA_PORT) { $env:LLAMA_PORT } else { "8080" }
$ctx   = if ($env:LLAMA_CTX) { $env:LLAMA_CTX } else { "8192" }
if (-not (Get-Command llama-server -ErrorAction SilentlyContinue)) { Write-Error "llama-server not found. Run: winget install llama.cpp"; exit 1 }
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
Write-Host "Starting llama-server with $model (first run downloads the model; log: llama-server.log)"
$p = Start-Process llama-server -ArgumentList @("-hf", $model, "--host", "127.0.0.1", "--port", $port, "-c", $ctx, "--jinja") `
     -RedirectStandardError "llama-server.log" -RedirectStandardOutput "llama-server.out.log" -PassThru -WindowStyle Hidden
try {
  $ready = $false
  for ($i = 0; $i -lt 900 -and -not $ready; $i++) {
    if ($p.HasExited) { Write-Error "llama-server exited. See llama-server.log"; exit 1 }
    try { $ready = (Invoke-WebRequest "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { Start-Sleep 2 }
  }
  if (-not $ready) { Write-Error "Timed out waiting for the model."; exit 1 }
  $env:BATON_PROVIDER = "openai"; $env:BATON_BASE_URL = "http://127.0.0.1:$port/v1"
  Write-Host "Model ready. Baton: http://127.0.0.1:8765"
  & $py -m baton
} finally { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
