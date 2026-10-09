@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Telegram-Setup.ps1"
set AIRA_TELEGRAM_EXIT=%errorlevel%
echo.
pause
exit /b %AIRA_TELEGRAM_EXIT%
