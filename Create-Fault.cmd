@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Invoice-Fault.ps1" -Mode create
set AIRA_FAULT_EXIT=%errorlevel%
echo.
pause
exit /b %AIRA_FAULT_EXIT%
