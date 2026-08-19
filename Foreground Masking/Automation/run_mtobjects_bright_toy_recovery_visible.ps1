param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [double]$ToyPeakSigmaMin = 20.0,
    [double]$ToyPeakSigmaMax = 80.0
)

$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$CleanList = Join-Path $DataRoot "CleanGalaxies.txt"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunRoot = Join-Path $DataRoot "mtobjects bright toy cross validation\$Stamp"
$BatchRoot = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_bright_toys_$Stamp"
$LogRoot = Join-Path $RunRoot "logs"
New-Item -ItemType Directory -Force -Path $LogRoot, $BatchRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "MTObjects bright Toy Objects - optimisation and 182 PNGs"
Set-Location $Repo

function Invoke-LoggedPython([string]$Script, [string[]]$Arguments, [string]$LogName) {
    & $Python $Script @Arguments 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath (Join-Path $LogRoot $LogName) -Append
    if ($LASTEXITCODE -ne 0) { throw "$Script failed with exit code $LASTEXITCODE" }
}

Write-Host "MTObjects bright Toy Objects four-fold optimisation" -ForegroundColor Cyan
Write-Host "Toy peak range: $ToyPeakSigmaMin to $ToyPeakSigmaMax robust sigma (standard is 5 to 25)"
Write-Host "Four folds: 30 training / 10 held out; 40 trials per fold; 10 workers"
Write-Host "MTObjects detection image: original science image"
Write-Host "Run folder: $RunRoot"

Invoke-LoggedPython `
    "Foreground Masking\Optimisation\cross_validate_toy_objects_MTObjects.py" `
    @("--clean-list", $CleanList, "--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot,
      "--output-dir", $RunRoot, "--initial-points", "8", "--max-iter", "32", "--workers", "10",
      "--toys-per-image", "6", "--toy-peak-sigma-min", "$ToyPeakSigmaMin", "--toy-peak-sigma-max", "$ToyPeakSigmaMax",
      "--detect-on", "original", "--calibrate-bg-variance", "--bg-variance-log",
      "--min-toy-detection-rate", "0.25", "--min-mean-toy-recall", "0.20",
      "--final-min-toy-detection-rate", "0.50", "--final-min-mean-toy-recall", "0.30",
      "--data-loss-penalty", "0.5", "--false-positive-penalty", "0.1") `
    "cross_validation.log"

$BestJson = Join-Path $RunRoot "mtobjects_toy_cross_validation_best.json"
if (-not (Test-Path -LiteralPath $BestJson -PathType Leaf)) { throw "Validated best JSON was not produced." }

Write-Host "Validated winner accepted. Starting the 182-galaxy bright-toy PNG batch." -ForegroundColor Green
Invoke-LoggedPython `
    "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py" `
    @("--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot, "--best-json", $BestJson,
      "--source", "toy-object", "--run-label", "MTObjects bright toys $Stamp", "--output-dir", $BatchRoot,
      "--max-images", "182", "--toys-per-image", "6", "--toy-seed", "202608299",
      "--toy-peak-sigma-min", "$ToyPeakSigmaMin", "--toy-peak-sigma-max", "$ToyPeakSigmaMax") `
    "all_182_batch.log"

Write-Host "Completed successfully." -ForegroundColor Green
Write-Host "PNG folder: $BatchRoot"
Write-Host "Optimisation folder: $RunRoot"
Read-Host "Press Enter to close"
