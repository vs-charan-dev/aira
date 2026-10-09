param([int]$Port = 8000, [switch]$SmokeTest, [switch]$RestartBackend)
. (Join-Path $PSScriptRoot 'scripts\Environment.ps1')
. (Join-Path $PSScriptRoot 'scripts\Aira-Backend.ps1')
$env:AIRA_ROOT = $AiraRoot
$env:AIRA_URL = "http://127.0.0.1:$Port"
$env:ELECTRON_CACHE = Join-Path $env:AIRA_CACHE_DIR 'electron-download'
$electron = Join-Path $AiraRoot 'desktop\node_modules\electron\dist\electron.exe'
if (!(Test-Path $electron)) { throw 'Run scripts\Setup-Desktop.ps1 first.' }
$server = $null
try {
    $expectedRevision = Get-AiraBackendRevision
    if ($RestartBackend) {
        $runningDesktop = @(Get-CimInstance Win32_Process -Filter "Name='electron.exe'" | Where-Object { $_.ExecutablePath -ieq $electron })
        if ($runningDesktop.Count) { throw 'Quit AIRA from its tray first, then run Restart-AIRA-Desktop.cmd again. No backend was stopped.' }
        Stop-AiraWorkspaceBackend $Port
    }
    try { $health = Invoke-RestMethod "$env:AIRA_URL/health" -TimeoutSec 2 } catch { $health = $null }
    if ($health -and ($health.status -ne 'healthy' -or $health.backendRevision -ne $expectedRevision)) {
        throw 'The backend is running older AIRA code. Quit AIRA from its tray, then run Restart-AIRA-Desktop.cmd. The old backend was not reused.'
    }
    if (!$health) {
        $server = Start-Process -FilePath (Join-Path $AiraRoot '.venv\Scripts\python.exe') -ArgumentList @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', "$Port") -WorkingDirectory (Join-Path $AiraRoot 'backend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $env:AIRA_CACHE_DIR 'desktop-backend.log') -RedirectStandardError (Join-Path $env:AIRA_CACHE_DIR 'desktop-backend-errors.log')
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            Start-Sleep -Milliseconds 500
            try { $health = Invoke-RestMethod "$env:AIRA_URL/health" -TimeoutSec 1; break } catch {}
        }
        if (!$health) { throw 'AIRA backend did not start. See .cache\desktop-backend-errors.log.' }
        if ($health.backendRevision -ne $expectedRevision) { throw 'The backend source changed during startup. Restart AIRA again.' }
    }
    $desktopArgs = @('"' + (Join-Path $AiraRoot 'desktop') + '"')
    if ($SmokeTest) { $desktopArgs += '--smoke-test' }
    $desktopProcess = Start-Process -FilePath $electron -ArgumentList $desktopArgs -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $env:AIRA_CACHE_DIR 'desktop.log') -RedirectStandardError (Join-Path $env:AIRA_CACHE_DIR 'desktop-errors.log')
    if ($desktopProcess.ExitCode -ne 0) { throw "Desktop exited with code $($desktopProcess.ExitCode). See .cache\desktop-errors.log." }
} finally {
    # Only terminate the server this launcher created; leave an existing server running.
    if ($server -and !$server.HasExited) { Stop-Process -Id $server.Id }
}
