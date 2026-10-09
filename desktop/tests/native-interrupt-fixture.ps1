$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\..\scripts\Environment.ps1')
Add-Type -AssemblyName System.Speech
$airaFixture = Join-Path $env:AIRA_CACHE_DIR 'interrupt-fixture.wav'
$airaSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $airaSynth.SetOutputToWaveFile($airaFixture)
    $airaSynth.Speak('stop eye rah')
} finally { $airaSynth.Dispose() }
$airaRecognition = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot '..\Wake-AIRA.ps1') -InterruptMode -WaveFile $airaFixture -ConfidenceThreshold 0.70
$airaRecognition | Write-Output
if ($LASTEXITCODE -ne 0 -or $airaRecognition -notcontains 'INTERRUPT') { throw 'Synthetic stop phrase recognition failed.' }
