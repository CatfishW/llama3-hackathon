# Run the OpenAI-compatible proxy on Windows
# Usage: .\deployment\run_openai_proxy.ps1 -Host 0.0.0.0 -Port 8000

param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000
)

$env:PYTHONUNBUFFERED = "1"
uvicorn deployment.openai_compat_server:app --host $Host --port $Port
