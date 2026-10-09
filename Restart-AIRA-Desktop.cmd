@echo off
echo Quit AIRA from its tray before using this launcher.
echo This reloads the AIRA backend; active conversations disconnect.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-AIRA-Desktop.ps1" -RestartBackend
if errorlevel 1 pause
