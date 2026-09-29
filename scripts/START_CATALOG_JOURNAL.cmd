@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_catalog_journal.ps1" %*
pause
