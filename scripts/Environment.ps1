$ErrorActionPreference = 'Stop'
$AiraRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$env:AIRA_DATA_DIR = Join-Path $AiraRoot 'data'
$env:AIRA_CACHE_DIR = Join-Path $AiraRoot '.cache'
$env:TEMP = Join-Path $env:AIRA_CACHE_DIR 'tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $env:AIRA_CACHE_DIR 'pip'
$env:npm_config_cache = Join-Path $env:AIRA_CACHE_DIR 'npm'
$env:HF_HOME = Join-Path $env:AIRA_CACHE_DIR 'models'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $env:AIRA_CACHE_DIR 'browsers'
$env:ELECTRON_CACHE = Join-Path $env:AIRA_CACHE_DIR 'electron-download'
$env:electron_config_cache = $env:ELECTRON_CACHE
$env:PYTHONPYCACHEPREFIX = Join-Path $env:AIRA_CACHE_DIR 'pycache'
foreach ($AiraDir in @($env:TEMP, $env:PIP_CACHE_DIR, $env:npm_config_cache, $env:HF_HOME, $env:PLAYWRIGHT_BROWSERS_PATH, $env:PYTHONPYCACHEPREFIX)) {
    New-Item -ItemType Directory -Path $AiraDir -Force | Out-Null
}
