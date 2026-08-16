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
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$CleanList = Join-Path $DataRoot "CleanGalaxies.txt"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = if ($ResumeRunRoot) { $ResumeRunRoot } else { Join-Path $DataRoot "mtobjects toy cross validation\$Stamp" }
$RunStamp = Split-Path -Leaf $RunRoot
$BatchRoot = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_toy_cv_$RunStamp"
$LogRoot = Join-Path $RunRoot "logs"
$CvLog = Join-Path $LogRoot "cross_validation.log"
$BatchLog = Join-Path $LogRoot "all_182_batch.log"

New-Item -ItemType Directory -Force -Path $LogRoot, $BatchRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "MTObjects Toy Objects - 4-fold cross-validation and 182-galaxy batch"
Set-Location $Repo

Write-Host "MTObjects Toy Objects four-fold cross-validation" -ForegroundColor Cyan
Write-Host "Design: four rotations of 30 training + 10 held-out galaxies"
Write-Host "Trials per fold: 40 (8 startup + 32 TPE); workers: 10"
Write-Host "Run folder: $RunRoot"
Write-Host ""

& $Python "Foreground Masking\Optimisation\cross_validate_toy_objects_MTObjects.py" `
    --clean-list $CleanList `
    --manifest $Manifest `
    --pc $PC `
    --mtobjects-root $MTObjectsRoot `
    --output-dir $RunRoot `
    --initial-points 8 `
    --max-iter 32 `
    --workers 10 `
    --toys-per-image 6 `
    --detect-on original `
    --bg-variance-min 0.0001 `
    --bg-variance-max 10000.0 `
    --bg-variance-step 0.0001 2>&1 | Tee-Object -FilePath $CvLog -Append

$cvExit = $LASTEXITCODE
if ($cvExit -ne 0) {
    Write-Host "MTObjects cross-validation stopped with exit code $cvExit; the supervisor will resume it." -ForegroundColor Red
    exit $cvExit
}

$BestJson = Join-Path $RunRoot "mtobjects_toy_cross_validation_best.json"
if (-not (Test-Path -LiteralPath $BestJson)) {
    Write-Host "Winner JSON was not created: $BestJson" -ForegroundColor Red
    exit 1
}

Write-Host "MTObjects cross-validation complete. Starting all 182 galaxies." -ForegroundColor Green
$BatchSummary = Join-Path $BatchRoot "mtobjects_optimised_apply_summary.csv"
$BatchMode = if (Test-Path -LiteralPath $BatchSummary) { "--resume-output-dir" } else { "--output-dir" }
$BatchArguments = @(
    "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py",
    "--manifest", $Manifest,
    "--pc", $PC,
    "--mtobjects-root", $MTObjectsRoot,
    "--best-json", $BestJson,
    "--source", "toy-object",
    "--run-label", "MTObjects Toy Objects four-fold CV $RunStamp",
    $BatchMode, $BatchRoot,
    "--max-images", "182"
)
& $Python @BatchArguments 2>&1 | Tee-Object -FilePath $BatchLog -Append

$batchExit = $LASTEXITCODE
if ($batchExit -eq 0) {
    Write-Host "MTObjects cross-validation and 182-galaxy batch completed successfully." -ForegroundColor Green
} else {
    Write-Host "MTObjects batch stopped with exit code $batchExit; the supervisor will resume it." -ForegroundColor Red
}
exit $batchExit

