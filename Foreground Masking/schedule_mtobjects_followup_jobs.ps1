param(
    [int]$WaitPid = 3760,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$WorkbookHelper = Join-Path $ForegroundDir "append_optimisation_run_to_workbook.py"
$ApplyScript = Join-Path $ForegroundDir "apply_optimised_mtobjects_all_galaxies.py"

$Root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$Workbook = Join-Path $Root "documentation\Foreground Masking Optimisation Results.xlsx"

$ToyRun = Join-Path $Root "mtobjects toy optimisation\20260722_141659"
$ToyBest = Join-Path $ToyRun "mtobjects_parameter_optimisation_best.json"
$ToyBatchOut = Join-Path $Root "mtobjects all galaxy batch\mtobjects_toy_object_20260722_141659"
$ToyBatchLog = Join-Path $ToyBatchOut "terminal_log.txt"

$SpikeBest = Join-Path $Root "mtobjects spike optimisation\20260719_175031\mtobjects_spike_optimisation_best.json"
$SpikeResumeOut = Join-Path $Root "mtobjects all galaxy batch\mtobjects_spike_gate_20260722_103506"
$SpikeResumeLog = Join-Path $SpikeResumeOut "terminal_log.txt"

$SchedulerLog = Join-Path $Root "mtobjects all galaxy batch\scheduled_mtobjects_followup_20260722_141659.log"

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

Write-ScheduleLog "MTObjects follow-up scheduler started."
Write-ScheduleLog "Wait PID: $WaitPid"
Write-ScheduleLog "Toy optimisation run: $ToyRun"
Write-ScheduleLog "Spike resume output: $SpikeResumeOut"
Write-ScheduleLog "Toy batch output: $ToyBatchOut"

if ($DryRun) {
    Write-ScheduleLog "Dry run requested; no jobs launched."
    exit 0
}

$process = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
if ($process) {
    Write-ScheduleLog "Waiting for MTObjects toy optimiser PID $WaitPid to finish."
    Wait-Process -Id $WaitPid
}
else {
    Write-ScheduleLog "PID $WaitPid is not running; continuing immediately."
}

$deadline = (Get-Date).AddHours(12)
while (-not (Test-Path $ToyBest)) {
    if ((Get-Date) -gt $deadline) {
        throw "Timed out waiting for toy best JSON: $ToyBest"
    }
    Write-ScheduleLog "Waiting for toy best JSON: $ToyBest"
    Start-Sleep -Seconds 60
}

Write-ScheduleLog "Toy best JSON found."

Invoke-LoggedCommand -LogPath $SchedulerLog -Command @(
    $Python,
    $WorkbookHelper,
    "--algorithm", "MTObjects",
    "--method", "Toy Object",
    "--run-dir", $ToyRun,
    "--prefix", "mtobjects_parameter_optimisation",
    "--workbook", $Workbook
)

Invoke-LoggedCommand -LogPath $SpikeResumeLog -Command @(
    $Python,
    $ApplyScript,
    "--best-json", $SpikeBest,
    "--source", "spike-gate",
    "--run-label", "MTObjects Spike Gate best 20260719_175031",
    "--resume-output-dir", $SpikeResumeOut
)

New-Item -ItemType Directory -Force -Path $ToyBatchOut | Out-Null
Invoke-LoggedCommand -LogPath $ToyBatchLog -Command @(
    $Python,
    $ApplyScript,
    "--best-json", $ToyBest,
    "--source", "toy-object",
    "--run-label", "MTObjects Toy Object best 20260722_141659",
    "--output-dir", $ToyBatchOut
)

Write-ScheduleLog "MTObjects follow-up scheduler finished."
