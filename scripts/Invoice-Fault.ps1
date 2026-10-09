param([Parameter(Mandatory=$true)][ValidateSet('create','fix')][string]$Mode)
. (Join-Path $PSScriptRoot 'Environment.ps1')
$AiraFaultPython = Join-Path $AiraRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $AiraFaultPython)) { throw 'Run the AIRA setup first.' }
$env:PYTHONPATH = Join-Path $AiraRoot 'backend'
$env:PYTHONUTF8 = '1'
& $AiraFaultPython (Join-Path $AiraRoot 'backend\invoice_fault_cli.py') $Mode
exit $LASTEXITCODE
