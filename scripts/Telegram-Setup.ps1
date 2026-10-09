. (Join-Path $PSScriptRoot 'Environment.ps1')
$env:PYTHONPATH = Join-Path $AiraRoot 'backend'
$env:PYTHONUTF8 = '1'
& (Join-Path $AiraRoot '.venv\Scripts\python.exe') (Join-Path $AiraRoot 'backend\telegram_setup.py')
exit $LASTEXITCODE
