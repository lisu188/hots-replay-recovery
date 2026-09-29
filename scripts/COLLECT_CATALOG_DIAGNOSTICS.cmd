@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0collect_catalog_diagnostics.ps1"
set "HRC_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %HRC_EXIT%
