param(
    [Parameter(Mandatory = $true)][string]$RunRoot,
    [int]$AdoptProcessId = 0,
    [int]$MaxRestarts = 8
)

$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Launcher = Join-Path $PSScriptRoot "run_mtobjects_toy_recovery_followup_visible.ps1"
$RunStamp = Split-Path -Leaf $RunRoot
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$BatchRoot = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_toy_recovery_$RunStamp"
$Summary = Join-Path $BatchRoot "mtobjects_optimised_apply_summary.csv"
$Winner = Join-Path $RunRoot "mtobjects_toy_cross_validation_best.json"
$Rejected = Join-Path $RunRoot "mtobjects_toy_cross_validation_rejected.json"
$MonitorLog = Join-Path $RunRoot "logs\supervisor.log"
$CurrentPid = $AdoptProcessId
$Restarts = 0

function Write-Monitor([string]$Message) {
    Add-Content -LiteralPath $MonitorLog -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" -Encoding utf8
}
function Completed-Galaxies {
    if (-not (Test-Path -LiteralPath $Summary)) { return 0 }
    return [Math]::Max(0, @(Get-Content -LiteralPath $Summary).Count - 1)
}
function Start-Workflow {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$Launcher`" -PC Desktop -ResumeRunRoot `"$RunRoot`""
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $Repo -WindowStyle Normal -PassThru
    Write-Monitor "Restarted visible workflow pid=$($process.Id), restart=$Restarts/$MaxRestarts"
    return $process.Id
}

Write-Monitor "Recovery supervisor started; adopted_pid=$CurrentPid"
while ($true) {
    $completed = Completed-Galaxies
    if ((Test-Path -LiteralPath $Winner) -and $completed -ge 182) { Write-Monitor "Complete: batch rows=$completed"; exit 0 }
    if (Test-Path -LiteralPath $Rejected) { Write-Monitor "Stopped correctly: all candidates were scientifically rejected"; exit 2 }
    $running = $CurrentPid -gt 0 -and [bool](Get-Process -Id $CurrentPid -ErrorAction SilentlyContinue)
    if (-not $running) {
        if ($Restarts -ge $MaxRestarts) { Write-Monitor "Maximum restarts reached"; exit 1 }
        $Restarts += 1
        Start-Sleep -Seconds 3
        $CurrentPid = Start-Workflow
    }
    Start-Sleep -Seconds 10
}
