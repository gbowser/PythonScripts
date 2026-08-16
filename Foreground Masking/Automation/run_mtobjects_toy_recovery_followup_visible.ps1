param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [string]$ResumeRunRoot = ""
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$CleanList = Join-Path $DataRoot "CleanGalaxies.txt"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = if ($ResumeRunRoot) { $ResumeRunRoot } else { Join-Path $DataRoot "mtobjects toy recovery followup\$Stamp" }
$RunStamp = Split-Path -Leaf $RunRoot
$BatchRoot = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_toy_recovery_$RunStamp"
$LogRoot = Join-Path $RunRoot "logs"
New-Item -ItemType Directory -Force -Path $LogRoot, $BatchRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "MTObjects recovery optimisation - monitored"
Set-Location $Repo

Write-Host "MTObjects Toy Objects recovery optimisation" -ForegroundColor Cyan
Write-Host "Calibration + four folds (30 training / 10 validation), 40 trials per fold, 10 workers"
Write-Host "Hard search gates: detection >= 25%, mean toy recall >= 20%"
Write-Host "Final release gates: detection >= 50%, mean toy recall >= 30%, max masked <= 15%, recovery in every fold"
Write-Host "Run folder: $RunRoot"

& $Python "Foreground Masking\Optimisation\cross_validate_toy_objects_MTObjects.py" `
    --clean-list $CleanList --manifest $Manifest --pc $PC --mtobjects-root $MTObjectsRoot `
    --output-dir $RunRoot --initial-points 8 --max-iter 32 --workers 10 --toys-per-image 6 `
    --detect-on original --calibrate-bg-variance --bg-variance-log `
    --min-toy-detection-rate 0.25 --min-mean-toy-recall 0.20 `
    --final-min-toy-detection-rate 0.50 --final-min-mean-toy-recall 0.30 `
    --data-loss-penalty 0.5 --false-positive-penalty 0.1 2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "cross_validation.log") -Append

if ($LASTEXITCODE -ne 0) {
    Write-Host "Cross-validation stopped or rejected its candidates. See the log and rejection JSON." -ForegroundColor Red
    exit $LASTEXITCODE
}
$BestJson = Join-Path $RunRoot "mtobjects_toy_cross_validation_best.json"
$BatchSummary = Join-Path $BatchRoot "mtobjects_optimised_apply_summary.csv"
$BatchMode = if (Test-Path -LiteralPath $BatchSummary) { "--resume-output-dir" } else { "--output-dir" }
Write-Host "Validated winner accepted. Starting the 182-galaxy PNG batch." -ForegroundColor Green
& $Python "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py" `
    --manifest $Manifest --pc $PC --mtobjects-root $MTObjectsRoot --best-json $BestJson `
    --source toy-object --run-label "MTObjects recovery CV $RunStamp" $BatchMode $BatchRoot --max-images 182 `
    2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "all_182_batch.log") -Append
exit $LASTEXITCODE
