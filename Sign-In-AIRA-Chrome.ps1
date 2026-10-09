# Open the SAME E-drive profile in ordinary Chrome for manual website sign-in.
# This helper never reads cookies/passwords or controls the sign-in page.
. (Join-Path $PSScriptRoot 'scripts\Environment.ps1')
$profile = [IO.Path]::GetFullPath((Join-Path $AiraRoot 'data\browser\chrome'))
$cache = Join-Path $AiraRoot '.cache\chrome'

foreach ($chromeProcess in @(Get-CimInstance Win32_Process -Filter "Name='chrome.exe'")) {
    if ([string]$chromeProcess.CommandLine -match '--user-data-dir(?:=|\s+)(?:"([^"]+)"|([^\s"]+))') {
        $usedProfile = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        if ([IO.Path]::GetFullPath($usedProfile).TrimEnd('\') -ieq $profile.TrimEnd('\')) {
            throw 'Close the existing AIRA Chrome window first, then run this helper again. Personal Chrome windows can stay open.'
        }
    }
}

$candidates = @()
foreach ($key in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe')) {
    if (Test-Path -LiteralPath $key) { $candidates += (Get-Item -LiteralPath $key).GetValue('') }
}
$candidates += @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1
if (!$chrome) { throw 'Google Chrome is not installed in a recognized location.' }
foreach ($directory in @($profile, $cache)) { New-Item -ItemType Directory -Path $directory -Force | Out-Null }

Write-Host 'This is normal Chrome, using the persistent AIRA profile on E:.'
Write-Host 'Click Sign in on YouTube and complete Google sign-in yourself.'
Write-Host 'Website sign-in is enough; Chrome Sync is not needed.'
Write-Host 'After sign-in, close this Chrome window, then ask AIRA to open Chrome.'
Start-Process -FilePath $chrome -ArgumentList @(
    ('--user-data-dir="' + $profile + '"'), '--profile-directory=Default',
    ('--disk-cache-dir="' + $cache + '"'), '--disable-sync', '--no-first-run',
    'https://www.youtube.com'
) -WindowStyle Normal | Out-Null
