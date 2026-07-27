param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

param(
    [int]$WaitPid = 37036,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$Compositor = Join-Path $ForegroundDir "Utilities\make_all_method_galaxy_comparison_pngs.py"
$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$OutputDir = Join-Path $Root "all method galaxy comparison panels\all_method_comparison_20260724"
$MasterLog = Join-Path $ForegroundDir ("run_logs\all_method_comparison_after_mtobjects_toy_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-MasterLog {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MasterLog) | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line
}

Write-MasterLog "All-method comparison scheduler started."
Write-MasterLog "Waiting for MTObjects toy batch PID $WaitPid."
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
    Write-MasterLog "PID $WaitPid is not running; rendering immediately."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
& $Python $Compositor --output-dir $OutputDir 2>&1 | Tee-Object -FilePath (Join-Path $OutputDir "terminal_log.txt") -Append
$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-MasterLog "All-method comparison rendering finished successfully."
}
else {
    Write-MasterLog "All-method comparison rendering failed exit_code=$exitCode."
}
exit $exitCode
