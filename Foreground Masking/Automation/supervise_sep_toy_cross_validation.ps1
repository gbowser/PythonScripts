param(
    [Parameter(Mandatory = $true)]
    [string]$RunRoot,
    [int]$AdoptProcessId = 0,
    [int]$MaxRestarts = 8
)

$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Launcher = Join-Path $PSScriptRoot "run_sep_toy_cross_validation_visible.ps1"
$RunStamp = Split-Path -Leaf $RunRoot
$ResearchRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research"
$BatchRoot = Join-Path $ResearchRoot "Remove foreground objects\SEP all galaxy batch\sep_toy_cv_$RunStamp"
$Summary = Join-Path $BatchRoot "sep_optimised_apply_summary.csv"
$Winner = Join-Path $RunRoot "sep_toy_cross_validation_best.json"
$MonitorLog = Join-Path $RunRoot "logs\supervisor.log"
$CurrentPid = $AdoptProcessId
$Restarts = 0

function Write-Monitor([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -LiteralPath $MonitorLog -Value $line -Encoding utf8
}

function Completed-Galaxies {
    if (-not (Test-Path -LiteralPath $Summary)) { return 0 }
    return [Math]::Max(0, @(Get-Content -LiteralPath $Summary).Count - 1)
}

function Start-Workflow {
    $arguments = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"$Launcher`" -PC Desktop -ResumeRunRoot `"$RunRoot`""
    $process = Start-Process -FilePath "powershell.exe" -ArgumentList $arguments `
        -WorkingDirectory $Repo -WindowStyle Normal -PassThru
    Write-Monitor "Restarted visible workflow pid=$($process.Id), restart=$($Restarts)/$MaxRestarts"
    return $process.Id
}

Write-Monitor "Supervisor started; adopted_pid=$CurrentPid"
while ($true) {
    $completed = Completed-Galaxies
    if ((Test-Path -LiteralPath $Winner) -and $completed -ge 182) {
        Write-Monitor "Workflow complete: winner exists and batch rows=$completed"
        exit 0
    }

    $running = $false
    if ($CurrentPid -gt 0) {
        $running = [bool](Get-Process -Id $CurrentPid -ErrorAction SilentlyContinue)
    }
    if (-not $running) {
        if ($Restarts -ge $MaxRestarts) {
            Write-Monitor "Maximum restarts reached before completion; winner=$(Test-Path -LiteralPath $Winner), batch_rows=$completed"
            exit 1
        }
        $Restarts += 1
        Start-Sleep -Seconds 3
        $CurrentPid = Start-Workflow
    }
    Start-Sleep -Seconds 10
}
