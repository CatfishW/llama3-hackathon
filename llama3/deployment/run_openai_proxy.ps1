# Run the OpenAI-compatible proxy on Windows
# Usage: .\deployment\run_openai_proxy.ps1 -BindHost 0.0.0.0 -Port 25565

param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 25565
)

$env:PYTHONUNBUFFERED = "1"
C:\Users\Tang_\AppData\Roaming\Python\Python310\Scripts\uvicorn.exe deployment.openai_compat_server:app --host $BindHost --port $Port
