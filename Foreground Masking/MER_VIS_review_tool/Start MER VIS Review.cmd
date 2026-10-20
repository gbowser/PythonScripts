@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start_MER_VIS_Review.ps1"
if errorlevel 1 pause
