param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [string]$RunStamp = ""
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
if (-not $RunStamp) { $RunStamp = Get-Date -Format "yyyyMMdd_HHmmss" }

$CommonFoldSeed = 202608150
$CommonInjectionSeed = 202608299
$IndependentSelectionSeed = 202608399
$ToyPeakSigmaMin = 6.0
$ToyPeakSigmaMax = 30.0
$SepRoot = Join-Path $DataRoot "SEP\Toy Objects\$RunStamp\optimisation"
$MtoRoot = Join-Path $DataRoot "MTObjects\Toy Objects\$RunStamp\optimisation"
$ControlRoot = Join-Path $DataRoot "Toy Objects paired optimisation\$RunStamp"
$LogRoot = Join-Path $ControlRoot "logs"
$InjectionRoot = Join-Path $ControlRoot "immutable_injections"
$InjectionManifest = Join-Path $InjectionRoot "paired_toy_injection_manifest.json"
New-Item -ItemType Directory -Force -Path $SepRoot,$MtoRoot,$LogRoot,$InjectionRoot | Out-Null

$config = [ordered]@{
    run_stamp = $RunStamp
    design = "four-fold cross-validation; 30 training and 10 held out"
    common_fold_seed = $CommonFoldSeed
    cross_validation_global_seed = $CommonInjectionSeed
    independent_selection_global_seed = $IndependentSelectionSeed
    per_galaxy_seeds = "stored in immutable manifest and derived from global seed plus CRC32 galaxy identifier"
    toy_peak_sigma_original = "5.0 to 25.0"
    toy_peak_sigma_new = "$ToyPeakSigmaMin to $ToyPeakSigmaMax"
    brightness_scale = 1.20
    toys_per_image = 6
    science_image_detection = $true
    sep_output = $SepRoot
    mtobjects_output = $MtoRoot
    immutable_injection_manifest = $InjectionManifest
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ControlRoot "paired_run_config.json") -Encoding UTF8

$Host.UI.RawUI.WindowTitle = "Paired 20% Brighter Toy Optimisations - SEP then MTObjects"
Set-Location $Repo
Write-Host "PAIRED TOY OBJECTS OPTIMISATION" -ForegroundColor Cyan
Write-Host "SEP and MTObjects use identical folds and injection seeds."
Write-Host "Toy peak range: 6-30 sigma (20% above the previous 5-25 sigma)."
Write-Host "Detection input: original science image for both methods."
Write-Host "Each method: 4 folds x 40 trials (8 startup + 32 TPE), 10 workers."
Write-Host "Runs are sequential to avoid resource contention and preserve comparable timings."
Write-Host "Control folder: $ControlRoot"
Write-Host ""

function Run-Stage {
    param([string]$Name,[string]$Log,[string[]]$Arguments)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting $Name" -ForegroundColor Yellow
    $started = Get-Date
    & $Python @Arguments 2>&1 | Tee-Object -FilePath $Log -Append | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
    $elapsed = (Get-Date) - $started
    if ($code -ne 0) {
        Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name FAILED (exit $code; elapsed $($elapsed.ToString('hh\:mm\:ss')))." -ForegroundColor Red
        return $code
    }
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name complete (elapsed $($elapsed.ToString('hh\:mm\:ss')))." -ForegroundColor Green
    return 0
}

$manifestArgs = @(
    "Foreground Masking\Optimisation\generate_paired_toy_manifest.py",
    "--clean-list", $CleanList, "--source-manifest", $Manifest, "--output-dir", $InjectionRoot,
    "--pc", $PC, "--fold-seed", "$CommonFoldSeed", "--cv-seed", "$CommonInjectionSeed",
    "--selection-seed", "$IndependentSelectionSeed", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "$ToyPeakSigmaMin", "--toy-peak-sigma-max", "$ToyPeakSigmaMax"
)
$code = Run-Stage "immutable paired injection generation" (Join-Path $LogRoot "injection_manifest.log") $manifestArgs
if ($code -ne 0) { exit $code }

$sepArgs = @(
    "Foreground Masking\Optimisation\cross_validate_toy_objects_SEP.py",
    "--clean-list", $CleanList, "--manifest", $Manifest, "--pc", $PC,
    "--output-dir", $SepRoot, "--fold-seed", "$CommonFoldSeed",
    "--seed", "$CommonInjectionSeed", "--evaluation-seed", "$IndependentSelectionSeed",
    "--injection-manifest", $InjectionManifest, "--cv-injection-set", "cross_validation",
    "--evaluation-injection-set", "winner_selection",
    "--initial-points", "8", "--max-iter", "32", "--workers", "10",
    "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "$ToyPeakSigmaMin", "--toy-peak-sigma-max", "$ToyPeakSigmaMax",
    "--detect-on", "original"
)
$code = Run-Stage "SEP four-fold optimisation" (Join-Path $LogRoot "sep_cross_validation.log") $sepArgs
if ($code -ne 0) { Write-Host "MTObjects was not started because SEP failed." -ForegroundColor Red; exit $code }

$mtoArgs = @(
    "Foreground Masking\Optimisation\cross_validate_toy_objects_MTObjects.py",
    "--clean-list", $CleanList, "--manifest", $Manifest, "--pc", $PC,
    "--mtobjects-root", $MTObjectsRoot, "--output-dir", $MtoRoot,
    "--fold-seed", "$CommonFoldSeed", "--seed", "$CommonInjectionSeed",
    "--evaluation-seed", "$IndependentSelectionSeed",
    "--injection-manifest", $InjectionManifest, "--cv-injection-set", "cross_validation",
    "--evaluation-injection-set", "winner_selection",
    "--initial-points", "8", "--max-iter", "32", "--workers", "10",
    "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "$ToyPeakSigmaMin", "--toy-peak-sigma-max", "$ToyPeakSigmaMax",
    "--detect-on", "original", "--bg-variance-min", "0.0001",
    "--bg-variance-max", "10000.0", "--bg-variance-step", "0.0001"
)
$code = Run-Stage "MTObjects four-fold optimisation" (Join-Path $LogRoot "mtobjects_cross_validation.log") $mtoArgs
if ($code -ne 0) { exit $code }

Write-Host ""
Write-Host "Both paired 20%-brighter Toy Objects optimisations completed successfully." -ForegroundColor Green
Write-Host "SEP:       $SepRoot"
Write-Host "MTObjects: $MtoRoot"
Write-Host "Logs:      $LogRoot"
Write-Host "The window will remain open for review."
