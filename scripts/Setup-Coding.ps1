. (Join-Path $PSScriptRoot 'Environment.ps1')
$AiraCodingRuntime = Join-Path $AiraRoot '.runtime\opencode'
New-Item -ItemType Directory -Force -Path $AiraCodingRuntime | Out-Null
npm.cmd install --prefix $AiraCodingRuntime opencode-ai@1.18.35 --no-audit --no-fund
if ($LASTEXITCODE) { throw 'OpenCode install failed.' }
$AiraCodingBinary = Join-Path $AiraCodingRuntime 'node_modules\opencode-windows-x64\bin\opencode.exe'
if (!(Test-Path -LiteralPath $AiraCodingBinary)) { throw 'OpenCode Windows x64 binary missing.' }
& $AiraCodingBinary --version
if ($LASTEXITCODE) { throw 'OpenCode probe failed.' }
Write-Host 'OpenCode installed locally on E. AIRA supplies your saved Gemini key when you start a coding job.'
