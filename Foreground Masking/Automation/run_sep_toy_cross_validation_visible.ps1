param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [string]$ResumeRunRoot = ""
)

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") {
    "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research"
} else {
    "D:\Dropbox\Public Documents\UCLAN\MSc Research"
}
$ForegroundData = Join-Path $ResearchRoot "Remove foreground objects"
$CleanList = Join-Path $ForegroundData "CleanGalaxies.txt"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = if ($ResumeRunRoot) { $ResumeRunRoot } else { Join-Path $ForegroundData "sep toy cross validation\$Stamp" }
$RunStamp = Split-Path -Leaf $RunRoot
$BatchRoot = Join-Path $ForegroundData "SEP all galaxy batch\sep_toy_cv_$RunStamp"
$LogRoot = Join-Path $RunRoot "logs"
$CvLog = Join-Path $LogRoot "cross_validation.log"
$BatchLog = Join-Path $LogRoot "all_182_batch.log"

New-Item -ItemType Directory -Force -Path $LogRoot, $BatchRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "SEP Toy Objects - 4-fold cross-validation and 182-galaxy batch"
Set-Location $Repo

Write-Host "SEP Toy Objects four-fold cross-validation" -ForegroundColor Cyan
Write-Host "Design: four rotations of 30 training + 10 held-out galaxies"
Write-Host "SEP detection image: original science image (enforced)"
Write-Host "Trials per fold: 40 (8 startup + 32 TPE); workers: 10"
Write-Host "The optimiser prints progress, rough ETA, and expected completion after every trial."
Write-Host "Run folder: $RunRoot"
Write-Host ""

& $Python "Foreground Masking\Optimisation\cross_validate_toy_objects_SEP.py" `
    --clean-list $CleanList `
    --manifest $Manifest `
    --pc $PC `
    --output-dir $RunRoot `
    --initial-points 8 `
    --max-iter 32 `
    --workers 10 `
    --toys-per-image 6 `
    --detect-on original 2>&1 | Tee-Object -FilePath $CvLog

$cvExit = $LASTEXITCODE
if ($cvExit -ne 0) {
    Write-Host "Cross-validation failed with exit code $cvExit. Batch not started." -ForegroundColor Red
    exit $cvExit
}

$BestJson = Join-Path $RunRoot "sep_toy_cross_validation_best.json"
if (-not (Test-Path -LiteralPath $BestJson)) {
    Write-Host "Winner JSON was not created: $BestJson" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Cross-validation complete. Starting SEP on all 182 galaxies." -ForegroundColor Green
Write-Host "Best parameters: $BestJson"
Write-Host "Batch output: $BatchRoot"

$BatchSummary = Join-Path $BatchRoot "sep_optimised_apply_summary.csv"
$BatchMode = if (Test-Path -LiteralPath $BatchSummary) { "--resume-output-dir" } else { "--output-dir" }
$BatchArguments = @(
    "Foreground Masking\Batch tools\batch_toy_objects_SEP.py",
    "--manifest", $Manifest,
    "--pc", $PC,
    "--best-json", $BestJson,
    "--source", "toy-object",
    "--run-label", "SEP Toy Objects four-fold CV $RunStamp",
    $BatchMode, $BatchRoot,
    "--max-images", "182",
    "--require-best-json"
)
& $Python @BatchArguments 2>&1 | Tee-Object -FilePath $BatchLog -Append

$batchExit = $LASTEXITCODE
if ($batchExit -eq 0) {
    Write-Host "SEP cross-validation and 182-galaxy batch completed successfully." -ForegroundColor Green
} else {
    Write-Host "SEP batch failed with exit code $batchExit." -ForegroundColor Red
}
Write-Host "Logs: $LogRoot"
exit $batchExit
