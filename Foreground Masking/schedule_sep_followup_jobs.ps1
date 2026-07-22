param(
    [int]$WaitPid = 0,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$WorkbookHelper = Join-Path $ForegroundDir "append_optimisation_run_to_workbook.py"
$BatchScript = Join-Path $ForegroundDir "batch_sep_all_galaxies.py"

$Root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$Workbook = Join-Path $Root "documentation\Foreground Masking Optimisation Results.xlsx"

$ToyRun = Join-Path $Root "sep toy optimisation\20260722_141659"
$ToyBest = Join-Path $ToyRun "sep_toy_object_optimisation_best.json"
$ToyBatchOut = Join-Path $Root "SEP all galaxy batch\sep_toy_object_20260722_141659"
$ToyBatchLog = Join-Path $ToyBatchOut "terminal_log.txt"

$SpikeRun = Join-Path $Root "sep spike optimisation\20260719_183144"
$SpikeBest = Join-Path $SpikeRun "sep_spike_optimisation_best.json"
$SpikeBatchOut = Join-Path $Root "SEP all galaxy batch\sep_spike_gate_20260719_183144"
$SpikeBatchLog = Join-Path $SpikeBatchOut "terminal_log.txt"

$SchedulerLog = Join-Path $Root "SEP all galaxy batch\scheduled_sep_followup.log"

function Write-ScheduleLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $SchedulerLog -Value $line
}

function Invoke-LoggedCommand {
    param(
        [string]$LogPath,
        [string[]]$Command
    )
    $parent = Split-Path -Parent $LogPath
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Write-ScheduleLog ("Running: " + ($Command -join " "))
    & $Command[0] @($Command[1..($Command.Count - 1)]) 2>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $SchedulerLog) | Out-Null

Write-ScheduleLog "SEP follow-up scheduler started."
Write-ScheduleLog "Wait PID: $WaitPid"
Write-ScheduleLog "Spike batch output: $SpikeBatchOut"
Write-ScheduleLog "Toy batch output: $ToyBatchOut"

if ($DryRun) {
    Write-ScheduleLog "Dry run requested; no jobs launched."
    exit 0
}

if ($WaitPid -gt 0) {
    $process = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
    if ($process) {
        Write-ScheduleLog "Waiting for SEP optimiser PID $WaitPid to finish."
        Wait-Process -Id $WaitPid
    }
    else {
        Write-ScheduleLog "PID $WaitPid is not running; continuing immediately."
    }
}

Invoke-LoggedCommand -LogPath $SchedulerLog -Command @(
    $Python,
    $WorkbookHelper,
    "--algorithm", "SEP",
    "--method", "Toy Object",
    "--run-dir", $ToyRun,
    "--prefix", "sep_toy_object_optimisation",
    "--workbook", $Workbook
)

Invoke-LoggedCommand -LogPath $SpikeBatchLog -Command @(
    $Python,
    $BatchScript,
    "--best-json", $SpikeBest,
    "--source", "spike-gate",
    "--run-label", "SEP Spike Gate best 20260719_183144",
    "--output-dir", $SpikeBatchOut
)

Invoke-LoggedCommand -LogPath $ToyBatchLog -Command @(
    $Python,
    $BatchScript,
    "--best-json", $ToyBest,
    "--source", "toy-object",
    "--run-label", "SEP Toy Object best 20260722_141659",
    "--output-dir", $ToyBatchOut
)

Write-ScheduleLog "SEP follow-up scheduler finished."
