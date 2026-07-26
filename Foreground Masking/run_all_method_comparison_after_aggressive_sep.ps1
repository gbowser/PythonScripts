param(
    [int]$WaitPid = 29164,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$Compositor = Join-Path $ForegroundDir "make_all_method_galaxy_comparison_pngs.py"

$Root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$MTObjectsSpikeSummary = Join-Path $Root "mtobjects all galaxy batch\mtobjects_spike_gate_20260722_103506\mtobjects_optimised_apply_summary.csv"
$MTObjectsToySummary = Join-Path $Root "mtobjects all galaxy batch\mtobjects_toy_object_20260723_195742\mtobjects_optimised_apply_summary.csv"
$SEPSpikeSummary = Join-Path $Root "SEP all galaxy batch\sep_spike_gate_aggressive_20260724_150938\sep_optimised_apply_summary.csv"
$ComparisonRoot = Join-Path $Root "all method galaxy comparison panels"
$OutputDir = Join-Path $ComparisonRoot "all_method_comparison_aggressive_sep_20260724"
$MasterLog = Join-Path $ForegroundDir ("run_logs\all_method_comparison_after_aggressive_sep_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-MasterLog {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MasterLog) | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line
}

function Latest-AggressiveToySummary {
    $parent = Join-Path $Root "SEP all galaxy batch"
    Get-ChildItem -Path $parent -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "sep_toy_object_aggressive_*" -and (Test-Path (Join-Path $_.FullName "sep_optimised_apply_summary.csv")) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 |
        ForEach-Object { Join-Path $_.FullName "sep_optimised_apply_summary.csv" }
}

Write-MasterLog "Aggressive all-method comparison scheduler started."
Write-MasterLog "Waiting for aggressive SEP continuation PID $WaitPid."
Write-MasterLog "Output: $OutputDir"

if ($DryRun) {
    Write-MasterLog "Dry run requested; no wait or render."
    exit 0
}

$process = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
if ($process) {
    Wait-Process -Id $WaitPid
}
else {
    Write-MasterLog "PID $WaitPid is not running; checking outputs immediately."
}

$deadline = (Get-Date).AddMinutes(30)
$SEPToySummary = $null
while (-not $SEPToySummary -and (Get-Date) -lt $deadline) {
    $SEPToySummary = Latest-AggressiveToySummary
    if (-not $SEPToySummary) {
        Write-MasterLog "Waiting for aggressive SEP Toy Object batch summary."
        Start-Sleep -Seconds 60
    }
}

$required = @($MTObjectsSpikeSummary, $MTObjectsToySummary, $SEPSpikeSummary, $SEPToySummary)
foreach ($path in $required) {
    if (-not $path -or -not (Test-Path $path)) {
        Write-MasterLog "Missing required summary: $path"
        exit 1
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
& $Python $Compositor `
    --mtobjects-spike-summary $MTObjectsSpikeSummary `
    --mtobjects-toy-summary $MTObjectsToySummary `
    --sep-spike-summary $SEPSpikeSummary `
    --sep-toy-summary $SEPToySummary `
    --output-dir $OutputDir `
    --require-all 2>&1 | Tee-Object -FilePath (Join-Path $OutputDir "terminal_log.txt") -Append

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-MasterLog "Aggressive all-method comparison rendering finished successfully."
}
else {
    Write-MasterLog "Aggressive all-method comparison rendering failed exit_code=$exitCode."
}
exit $exitCode
