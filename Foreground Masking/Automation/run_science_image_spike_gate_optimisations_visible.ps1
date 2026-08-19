param(
    [int]$OptimisationGalaxies = 40,
    [int]$Workers = 1
)

$ErrorActionPreference = "Continue"
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Foreground = Join-Path $Repo "Foreground Masking"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = Join-Path $DataRoot "spike gate science image comparison\$Stamp"
$LogRoot = Join-Path $RunRoot "logs"
$SepOptimisationRoot = Join-Path $RunRoot "SEP optimisation"
$MtoOptimisationRoot = Join-Path $RunRoot "MTObjects optimisation"
$SepBatch = Join-Path $DataRoot "SEP all galaxy batch\sep_spike_gate_$Stamp"
$MtoBatch = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_spike_gate_$Stamp"

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
$Host.UI.RawUI.WindowTitle = "Science-image SEP + MTObjects - residual Spike Gate"

function Run-Stage([string]$Name, [string]$Script, [string[]]$Arguments, [string]$LogName) {
    Write-Host ""
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name" -ForegroundColor Cyan
    & $Python $Script @Arguments 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath (Join-Path $LogRoot $LogName)
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Matched Spike Gate optimisation and 182-galaxy batches" -ForegroundColor Green
Write-Host "Spike Gate target image: residual"
Write-Host "SEP and MTObjects mask image: original science image"
Write-Host "Optimisation galaxies: $OptimisationGalaxies; workers: $Workers"
Write-Host "Run root: $RunRoot"

Run-Stage "SEP Spike Gate optimisation" `
    (Join-Path $Foreground "Optimisation\optimise_spike_gate_SEP.py") `
    @("--output-dir", $SepOptimisationRoot, "--max-images", "$OptimisationGalaxies", "--initial-points", "16", "--max-iter", "64", "--workers", "$Workers", "--detect-on", "original", "--spike-gate-detect-on", "residual", "--progress-galaxies", "--results-workbook", (Join-Path $DataRoot "documentation\Foreground Masking Optimisation Results.xlsx")) `
    "sep_optimisation.log"

$SepBest = Get-ChildItem -LiteralPath $SepOptimisationRoot -Filter "sep_spike_optimisation_best.json" -Recurse -File | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $SepBest) { throw "SEP optimisation finished without a best-parameter JSON." }

Run-Stage "SEP 182-galaxy batch" `
    (Join-Path $Foreground "Batch tools\batch_spike_gate_SEP.py") `
    @("--best-json", $SepBest.FullName, "--output-dir", $SepBatch, "--max-images", "182", "--run-label", "SEP science image + residual Spike Gate $Stamp", "--spike-gate-detect-on", "residual", "--replace-summary") `
    "sep_182_batch.log"

Run-Stage "MTObjects Spike Gate optimisation" `
    (Join-Path $Foreground "Optimisation\optimise_spike_gate_MTObjects.py") `
    @("--output-dir", $MtoOptimisationRoot, "--max-images", "$OptimisationGalaxies", "--initial-points", "12", "--max-iter", "48", "--workers", "$Workers", "--detect-on", "original", "--spike-gate-detect-on", "residual", "--progress-galaxies", "--results-workbook", (Join-Path $DataRoot "documentation\Foreground Masking Optimisation Results.xlsx")) `
    "mtobjects_optimisation.log"

$MtoBest = Get-ChildItem -LiteralPath $MtoOptimisationRoot -Filter "mtobjects_spike_optimisation_best.json" -Recurse -File | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $MtoBest) { throw "MTObjects optimisation finished without a best-parameter JSON." }

Run-Stage "MTObjects 182-galaxy batch" `
    (Join-Path $Foreground "Batch tools\batch_spike_gate_MTObjects.py") `
    @("--best-json", $MtoBest.FullName, "--output-dir", $MtoBatch, "--max-images", "182", "--run-label", "MTObjects science image + residual Spike Gate $Stamp") `
    "mtobjects_182_batch.log"

Write-Host ""
Write-Host "All stages completed successfully." -ForegroundColor Green
Write-Host "SEP PNG folder: $SepBatch"
Write-Host "MTObjects PNG folder: $MtoBatch"
Write-Host "Logs: $LogRoot"
Read-Host "Press Enter to close"
