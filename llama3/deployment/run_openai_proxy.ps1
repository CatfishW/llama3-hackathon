# Run the OpenAI-compatible proxy on Windows
# Usage: .\deployment\run_openai_proxy.ps1 -BindHost 0.0.0.0 -Port 8000

param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000
)

$env:PYTHONUNBUFFERED = "1"
uvicorn deployment.openai_compat_server:app --host $BindHost --port $Port
