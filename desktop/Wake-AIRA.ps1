param([switch]$Probe, [switch]$InterruptMode, [string]$WaveFile, [ValidateRange(0.4, 0.9)][double]$ConfidenceThreshold = 0.70, [ValidateRange(0, 30)][int]$TestSeconds = 0)
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Speech
    $info = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers() | Where-Object { $_.Culture.TwoLetterISOLanguageName -eq 'en' } | Select-Object -First 1
    if (!$info) { throw 'No English Windows speech recognizer installed. Install English Speech in Windows language settings, then retry.' }
    if ($Probe) { Write-Output "AVAILABLE:$($info.Culture.Name)"; exit 0 }
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine($info)
    $recognizer.BabbleTimeout = [TimeSpan]::FromSeconds(2)
    $choices = New-Object System.Speech.Recognition.Choices
    if ($InterruptMode) {
        $choices.Add([string[]]@('stop aira', 'stop eye rah', 'stop air ah', 'aira stop', 'cancel aira', 'cancel eye rah', 'cancel air ah', 'aira cancel'))
        # Whole, named requests only; never load dictation or one-word stop guesses.
        foreach ($airaName in @('aira', 'eye rah', 'air ah', 'eye ra', 'ira', 'ayra')) {
            foreach ($airaRequest in @('stop', 'cancel', 'stop doing the work that you are doing', 'stop the work that you are doing', 'stop what you are doing', 'stop doing what you are doing', 'stop the current task', 'stop working', 'cancel the current task')) {
                $choices.Add("hey $airaName $airaRequest")
                $choices.Add("$airaName $airaRequest")
            }
        }
    } else {
        $choices.Add([string[]]@('hey aira', 'hey eye ra', 'hey ira', 'hey ayra', 'hey air ah', 'hey eye rah', 'hey aura', 'hey era'))
    }
    $builder = New-Object System.Speech.Recognition.GrammarBuilder
    $builder.Culture = $info.Culture
    $builder.Append($choices)
    $recognizer.LoadGrammar((New-Object System.Speech.Recognition.Grammar($builder)))
    # Queue CLR events, without PowerShell callbacks on the recognizer thread.
    # Only levels, counters and grammar matches leave this process; no audio is saved.
    Register-ObjectEvent $recognizer AudioLevelUpdated -SourceIdentifier 'aira-level' | Out-Null
    Register-ObjectEvent $recognizer SpeechDetected -SourceIdentifier 'aira-speech' | Out-Null
    Register-ObjectEvent $recognizer SpeechRecognitionRejected -SourceIdentifier 'aira-rejected' | Out-Null
    Register-ObjectEvent $recognizer AudioSignalProblemOccurred -SourceIdentifier 'aira-signal' | Out-Null
    Register-ObjectEvent $recognizer SpeechRecognized -SourceIdentifier 'aira-recognized' | Out-Null
    Register-ObjectEvent $recognizer RecognizeCompleted -SourceIdentifier 'aira-completed' | Out-Null
    if ($WaveFile) { $recognizer.SetInputToWaveFile($WaveFile) } else { $recognizer.SetInputToDefaultAudioDevice() }
    $deadline = (Get-Date).AddSeconds($TestSeconds)
    $speechCount = 0; $rejectedCount = 0; $matched = $false; $confidence = 0; $phrase = ''; $signal = ''
    $recognizer.RecognizeAsync([System.Speech.Recognition.RecognizeMode]::Multiple)
    Write-Output 'READY'
    while ($true) {
        Start-Sleep -Milliseconds 100
        $level = $recognizer.AudioLevel; $completed = $false
        foreach ($event in @(Get-Event -ErrorAction SilentlyContinue)) {
            switch ($event.SourceIdentifier) {
                'aira-level' { $level = [Math]::Max($level, $event.SourceEventArgs.AudioLevel) }
                'aira-speech' { $speechCount++ }
                'aira-rejected' { $rejectedCount++ }
                'aira-signal' { $signal = [string]$event.SourceEventArgs.AudioSignalProblem }
                'aira-recognized' {
                    $result = $event.SourceEventArgs.Result
                    $phrase = $result.Text; $confidence = [Math]::Round($result.Confidence, 3); $matched = $result.Confidence -ge $ConfidenceThreshold
                    if ($InterruptMode) {
                        # A bounded grammar can otherwise force noise into a stop phrase.
                        $weakWords = @($result.Words | Where-Object { $_.Confidence -lt 0.50 })
                        $matched = $matched -and $weakWords.Count -eq 0 -and $result.Audio.Duration.TotalMilliseconds -ge 300
                    }
                }
                'aira-completed' {
                    if ($event.SourceEventArgs.Error) { throw $event.SourceEventArgs.Error }
                    $completed = $true
                }
            }
            Remove-Event -EventIdentifier $event.EventIdentifier -ErrorAction SilentlyContinue
        }
        if ($level -gt 0 -and $signal -eq 'NoSignal') { $signal = '' }
        $diagnostic = @{ level = $level; speechCount = $speechCount; rejectedCount = $rejectedCount; phrase = $phrase; confidence = $confidence; matched = $matched; signal = $signal; culture = $info.Culture.Name; testing = ($TestSeconds -gt 0) }
        Write-Output ('DIAG:' + ($diagnostic | ConvertTo-Json -Compress))
        if ($matched -and !$TestSeconds) { if ($InterruptMode) { Write-Output 'INTERRUPT' } else { Write-Output 'WAKE' }; break }
        if ($TestSeconds -and (Get-Date) -ge $deadline) { Write-Output 'DONE'; break }
        if ($completed) {
            if ($WaveFile) { if ($TestSeconds) { Write-Output 'DONE' }; break }
            throw 'Wake microphone recognition ended. Disable and re-enable Hey AIRA to retry.'
        }
    }
} catch {
    Write-Output "ERROR:$($_.Exception.GetBaseException().Message)"
    exit 1
} finally {
    foreach ($identifier in @('aira-level', 'aira-speech', 'aira-rejected', 'aira-signal', 'aira-recognized', 'aira-completed')) {
        Unregister-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue
        Get-Event -SourceIdentifier $identifier -ErrorAction SilentlyContinue | Remove-Event -ErrorAction SilentlyContinue
    }
    if ($recognizer) { $recognizer.Dispose() }
}
