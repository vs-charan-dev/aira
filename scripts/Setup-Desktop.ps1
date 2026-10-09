. (Join-Path $PSScriptRoot 'Environment.ps1')
& (Join-Path $AiraRoot '.venv\Scripts\python.exe') -m pip install -r (Join-Path $AiraRoot 'desktop\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Windows controller dependency installation failed.' }
& (Join-Path $PSScriptRoot 'Setup-Windows-Use.ps1')
$env:ELECTRON_CACHE = Join-Path $env:AIRA_CACHE_DIR 'electron-download'
$env:electron_config_cache = $env:ELECTRON_CACHE
Set-Location (Join-Path $AiraRoot 'desktop')
& npm.cmd install --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw 'Desktop installation failed.' }
& node (Join-Path $AiraRoot 'desktop\node_modules\electron\install.js')
if ($LASTEXITCODE -ne 0) { throw 'Electron runtime download failed.' }
Write-Host 'Desktop ready. Launch Start-AIRA-Desktop.cmd.'
