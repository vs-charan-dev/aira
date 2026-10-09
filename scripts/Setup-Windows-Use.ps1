. (Join-Path $PSScriptRoot 'Environment.ps1')
$AiraWorkerPython = Join-Path $AiraRoot '.runtime\windows-use\Scripts\python.exe'
if (!(Test-Path -LiteralPath $AiraWorkerPython)) {
    & (Join-Path $AiraRoot '.venv\Scripts\python.exe') -m venv (Join-Path $AiraRoot '.runtime\windows-use')
    if ($LASTEXITCODE -ne 0) { throw 'Windows-Use environment creation failed.' }
}
& $AiraWorkerPython -m pip install -r (Join-Path $AiraRoot 'desktop\windows-use-requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Windows-Use installation failed.' }
& $AiraWorkerPython (Join-Path $AiraRoot 'desktop\windows_use_worker.py') --probe
if ($LASTEXITCODE -ne 0) { throw 'Windows-Use import probe failed.' }
Write-Host 'Windows-Use installed on E. Existing AIRA Settings supplies the Gemini key.'
