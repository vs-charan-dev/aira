# Lifecycle helpers for this workspace's loopback backend only.
function Get-AiraBackendRevision {
    $revision = & (Join-Path $AiraRoot '.venv\Scripts\python.exe') (Join-Path $AiraRoot 'backend\app\core\runtime_version.py')
    if ($LASTEXITCODE -ne 0 -or $revision -notmatch '^[a-f0-9]{64}$') { throw 'Could not determine the AIRA backend version.' }
    return "$revision"
}

function Test-AiraBackendCommand([string]$Command, [string]$PythonPath, [int]$BackendPort) {
    # Accept only the fixed command emitted by AIRA's launchers, with no extra
    # module, app directory, executable arguments or listening interfaces.
    $pattern = '(?i)^"?' + [regex]::Escape($PythonPath) + '"?\s+-m\s+uvicorn\s+main:app\s+--host\s+127\.0\.0\.1\s+--port\s+' + $BackendPort + '\s*$'
    return $Command -match $pattern
}

function Get-AiraWorkspaceBackendTargets([int]$BackendPort) {
    $listeners = @(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    $expectedPython = [IO.Path]::GetFullPath((Join-Path $AiraRoot '.venv\Scripts\python.exe'))
    $basePython = $null
    foreach ($line in Get-Content -LiteralPath (Join-Path $AiraRoot '.venv\pyvenv.cfg')) {
        if ($line -match '^executable\s*=\s*(.+?)\s*$') { $basePython = [IO.Path]::GetFullPath($Matches[1]) }
    }
    $targets = @()
    foreach ($ownerId in $owners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerId"
        $workspacePython = $process -and $process.ExecutablePath -ieq $expectedPython -and
            (Test-AiraBackendCommand ([string]$process.CommandLine) $expectedPython $BackendPort)
        # On Windows the venv redirector starts the base interpreter as a child.
        # A base Python process alone is insufficient: require the verified live
        # E-drive parent, identical AIRA arguments, and consistent creation times.
        $redirectedPython = $false
        if ($process -and $basePython -and $process.ExecutablePath -ieq $basePython -and
            (Test-AiraBackendCommand ([string]$process.CommandLine) $basePython $BackendPort)) {
            $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($process.ParentProcessId)"
            $redirectedPython = $parent -and $parent.Name -ieq 'python.exe' -and
                $parent.ExecutablePath -ieq $expectedPython -and
                (Test-AiraBackendCommand ([string]$parent.CommandLine) $expectedPython $BackendPort) -and
                $parent.CreationDate -le $process.CreationDate
        }
        if ($process.Name -ine 'python.exe' -or !($workspacePython -or $redirectedPython) -or @($listeners | Where-Object { $_.OwningProcess -eq $ownerId -and $_.LocalAddress -ne '127.0.0.1' }).Count) {
            throw "Port $BackendPort belongs to a process that cannot be verified as this workspace's AIRA backend. Stop your AIRA server manually; no process was stopped."
        }
        $targets += $process
    }
    return $targets
}

function Stop-AiraWorkspaceBackend([int]$BackendPort) {
    $targets = @(Get-AiraWorkspaceBackendTargets $BackendPort)
    foreach ($target in $targets) {
        # Recheck immediately before stopping to avoid acting on a reused PID.
        $verified = @(Get-AiraWorkspaceBackendTargets $BackendPort | Where-Object { $_.ProcessId -eq $target.ProcessId -and $_.CreationDate -eq $target.CreationDate })
        if (!$verified.Count) { continue }
        Write-Host 'Restarting this workspace AIRA backend; active conversations will disconnect.'
        Stop-Process -Id $target.ProcessId -ErrorAction Stop
    }
    for ($attempt=0; $attempt -lt 20; $attempt++) {
        if (!(Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue)) { return }
        Start-Sleep -Milliseconds 250
    }
    throw "Port $BackendPort is still occupied. Stop the AIRA server manually before retrying."
}
