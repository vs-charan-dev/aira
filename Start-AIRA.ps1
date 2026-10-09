param([switch]$NoBrowser, [int]$Port = 8000)
. (Join-Path $PSScriptRoot 'scripts\Environment.ps1')
if (!(Test-Path (Join-Path $AiraRoot 'frontend\dist\index.html'))) { throw 'Run scripts\Setup.ps1 first.' }
$env:PORT = "$Port"
Set-Location (Join-Path $AiraRoot 'backend')
Write-Host "AIRA Memory Palace: http://127.0.0.1:$Port/palace"
Write-Host 'Press Ctrl+C to stop. Add your Gemini key in Settings.'
if (!$NoBrowser) { Start-Process "http://127.0.0.1:$Port/palace" }
& (Join-Path $AiraRoot '.venv\Scripts\python.exe') -m uvicorn main:app --host 127.0.0.1 --port $Port
