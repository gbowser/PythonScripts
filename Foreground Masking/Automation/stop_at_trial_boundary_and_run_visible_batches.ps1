$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$LogRoot = Join-Path $ForegroundDir "run_logs\stability_20260727"
$ControlLog = Join-Path $LogRoot "stop_and_visible_batches.log"
$Python = (Get-Command python).Source

function Write-ControlLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $ControlLog -Value $line -Encoding utf8
}

function Get-FinishedTrialCount([string]$ErrorLog) {
    if (-not (Test-Path -LiteralPath $ErrorLog)) { return 0 }
    $content = Get-Content -Raw -LiteralPath $ErrorLog
    if ([string]::IsNullOrEmpty($content)) { return 0 }
    return [regex]::Matches($content, 'Trial\s+\d+ finished').Count
}

# Stop the controller first so it cannot launch seed waves 2 or 3 while the
# current optimisers are being allowed to reach their next trial boundary.
$controllers = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like '*run_optimiser_stability_study.ps1*'
}
foreach ($controller in $controllers) {
    Write-ControlLog "Stopping optimisation queue controller PID $($controller.ProcessId)."
    Stop-Process -Id $controller.ProcessId -Force -ErrorAction SilentlyContinue
}

$targets = @(
    @{
        Name = "MTObjects Spike Gate"
        Pattern = '*optimise_spike_gate_MTObjects.py*--seed 202607281*'
        ErrorLog = Join-Path $LogRoot 'spike_gate_MTObjects_seed_202607281.err.log'
    },
    @{
        Name = "MTObjects Toy Objects"
        Pattern = '*optimise_toy_objects_MTObjects.py*--seed 202607281*'
        ErrorLog = Join-Path $LogRoot 'toy_objects_MTObjects_seed_202607281.err.log'
    }
)

$activeTargets = @()
foreach ($target in $targets) {
    $process = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -like $target.Pattern
    } | Select-Object -First 1
    if ($null -eq $process) {
        Write-ControlLog "$($target.Name) is no longer running."
        continue
    }

    $baseline = Get-FinishedTrialCount $target.ErrorLog
    Write-ControlLog "$($target.Name) PID $($process.ProcessId): waiting for trial $($baseline + 1) to finish."
    $activeTargets += [pscustomobject]@{
        Name = $target.Name
        ProcessId = $process.ProcessId
        ErrorLog = $target.ErrorLog
        Baseline = $baseline
        Stopped = $false
    }
}

while (@($activeTargets | Where-Object { -not $_.Stopped }).Count -gt 0) {
    Start-Sleep -Seconds 10
    foreach ($target in $activeTargets | Where-Object { -not $_.Stopped }) {
        if (-not (Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue)) {
            Write-ControlLog "$($target.Name) exited before an explicit boundary stop was needed."
            $target.Stopped = $true
            continue
        }
        $finished = Get-FinishedTrialCount $target.ErrorLog
        if ($finished -gt $target.Baseline) {
            Write-ControlLog "$($target.Name): trial $finished finished; stopping PID $($target.ProcessId) at the boundary."
            Stop-Process -Id $target.ProcessId -Force -ErrorAction SilentlyContinue
            $target.Stopped = $true
        }
    }
}

Write-ControlLog "Optimisation sequence stopped. Starting visible all-galaxy batches sequentially."
$batches = @(
    'batch_spike_gate_SEP.py',
    'batch_toy_objects_SEP.py',
    'batch_spike_gate_MTObjects.py',
    'batch_toy_objects_MTObjects.py'
)

foreach ($batch in $batches) {
    $script = Join-Path $ForegroundDir $batch
    Write-ControlLog "Starting $batch"
    & $Python $script
    Write-ControlLog "$batch finished with exit code $LASTEXITCODE"
}

Write-ControlLog "All visible batch jobs finished."
Write-Host "Press Enter to close this window."
Read-Host
