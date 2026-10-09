. (Join-Path $PSScriptRoot 'Environment.ps1')
$AiraDemoPath = Join-Path $AiraRoot 'data\projects\aira-demo'
if (Test-Path -LiteralPath $AiraDemoPath) { Write-Host 'Existing demo preserved.'; return }
New-Item -ItemType Directory -Force -Path $AiraDemoPath | Out-Null
Copy-Item -LiteralPath (Join-Path $AiraRoot 'demo\coding-fixture\invoice.js'), (Join-Path $AiraRoot 'demo\coding-fixture\invoice.test.js'), (Join-Path $AiraRoot 'demo\coding-fixture\package.json'), (Join-Path $AiraRoot 'demo\coding-fixture\README.md') -Destination $AiraDemoPath
Write-Host 'AIRA coding demo created on E. It intentionally has failing tests.'
