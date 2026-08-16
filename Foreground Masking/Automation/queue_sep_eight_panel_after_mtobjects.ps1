param([int]$MTObjectsSupervisorProcessId = 26348)

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Launcher = Join-Path $PSScriptRoot "run_sep_toy_eight_panel_batch_visible.ps1"
$Process = Get-Process -Id $MTObjectsSupervisorProcessId -ErrorAction SilentlyContinue
if ($Process) { $Process.WaitForExit() }
$Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$Launcher`" -PC Desktop"
Start-Process -FilePath "powershell.exe" -ArgumentList $Arguments -WorkingDirectory $Repo -WindowStyle Normal
