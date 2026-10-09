. (Join-Path $PSScriptRoot 'Environment.ps1')
Push-Location $AiraRoot
try {
    $AiraFree = (Get-PSDrive -Name ([IO.Path]::GetPathRoot($AiraRoot).Substring(0,1))).Free
    if ($AiraFree -lt 5GB) { throw 'AIRA setup needs at least 5 GB free on its drive.' }
    if (!(Test-Path '.env')) { Copy-Item '.env.example' '.env' }
    if (!(Test-Path '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE) { throw 'Python environment creation failed' }
    }
    & '.\.venv\Scripts\python.exe' -m pip install -r backend\requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Python dependency install failed' }
    Push-Location frontend
    try {
        npm.cmd ci --no-audit --no-fund
        if ($LASTEXITCODE) { throw 'Frontend dependency install failed' }
        npm.cmd run build
        if ($LASTEXITCODE) { throw 'Frontend build failed' }
    } finally { Pop-Location }
} finally { Pop-Location }
Write-Host 'AIRA setup complete. Run Start-AIRA.ps1 and add your Gemini key in Settings.'
