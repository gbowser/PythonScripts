@echo off
set "RESUME_SCRIPT=C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\Automation\resume_paired_toy_png_batches_visible.ps1"
del "%~f0"
start "" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%RESUME_SCRIPT%" -PC Desktop -RunStamp 20260824_115154
