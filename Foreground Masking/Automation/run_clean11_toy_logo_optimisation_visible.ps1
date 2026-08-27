param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [string]$RunStamp = (Get-Date -Format "yyyyMMdd_HHmmss"),
    [int]$Workers = 4,
    [switch]$ResumeFinal
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") {
    "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research"
} else {
    "D:\Dropbox\Public Documents\UCLAN\MSc Research"
}
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$Names = Join-Path $Repo "Foreground Masking\Optimisation\clean_galaxies_11_20260826.txt"
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$Control = Join-Path $DataRoot "Toy Objects paired optimisation\clean11_logo_$RunStamp"
$InjectionRoot = Join-Path $Control "paired_injections"
$InjectionManifest = Join-Path $InjectionRoot "paired_toy_injection_manifest.json"
$SepCV = Join-Path $Control "sep_logo"
$MtoCV = Join-Path $Control "mtobjects_logo"
$SepFinal = Join-Path $Control "sep_final_all11"
$MtoFinal = Join-Path $Control "mtobjects_final_all11"
$LogRoot = Join-Path $Control "logs"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) { throw "Python not found: $Python" }
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf)) { throw "S4G manifest not found: $Manifest" }
$GalaxyNames = @(Get-Content -LiteralPath $Names | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })
if ($GalaxyNames.Count -ne 11) { throw "Expected 11 clean galaxies, found $($GalaxyNames.Count) in $Names" }
if ((Test-Path -LiteralPath $Control) -and -not $ResumeFinal) { throw "Output already exists; refusing to overwrite: $Control" }
if ($ResumeFinal -and -not (Test-Path -LiteralPath $InjectionManifest -PathType Leaf)) {
    throw "Cannot resume final stages because the paired injection manifest is missing: $InjectionManifest"
}
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

function Run-Stage {
    param([string]$Name, [string]$Log, [string[]]$Arguments)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting $Name" -ForegroundColor Yellow
    $started = Get-Date
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Python @Arguments 2>&1 | Tee-Object -FilePath $Log -Append | ForEach-Object { Write-Host $_ }
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    $elapsed = (Get-Date) - $started
    if ($code -ne 0) { throw "$Name failed with exit code $code after $($elapsed.ToString('hh\:mm\:ss'))." }
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name complete in $($elapsed.ToString('hh\:mm\:ss'))." -ForegroundColor Green
}

$Host.UI.RawUI.WindowTitle = "S4G clean-11 Toy Objects leave-one-out optimisation"
Set-Location $Repo
Write-Host "S4G CLEAN-11 TOY OBJECTS RE-OPTIMISATION" -ForegroundColor Cyan
Write-Host "Run: $RunStamp"
Write-Host "Design: 11 leave-one-galaxy-out folds, 10 train / 1 held out; independent injection set for fold selection."
Write-Host "Final production fits use all 11 galaxies after cross-validation."
Write-Host "Output: $Control"

if (-not $ResumeFinal) {
Run-Stage "paired injection generation" (Join-Path $LogRoot "01_generate_injections.log") @(
    "Foreground Masking\Optimisation\generate_paired_toy_manifest.py",
    "--clean-list", $Names, "--source-manifest", $Manifest, "--output-dir", $InjectionRoot,
    "--pc", $PC, "--fold-seed", "202608260", "--cv-seed", "202608261",
    "--selection-seed", "202608262", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30"
)

Run-Stage "SEP 11-fold leave-one-out CV" (Join-Path $LogRoot "02_sep_logo.log") @(
    "Foreground Masking\Optimisation\cross_validate_toy_objects_SEP.py",
    "--clean-list", $Names, "--manifest", $Manifest, "--pc", $PC, "--output-dir", $SepCV,
    "--injection-manifest", $InjectionManifest, "--cv-injection-set", "cross_validation",
    "--evaluation-injection-set", "winner_selection", "--initial-points", "8", "--max-iter", "32",
    "--workers", "$Workers", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30", "--detect-on", "original"
)

Run-Stage "MTObjects 11-fold leave-one-out CV" (Join-Path $LogRoot "03_mtobjects_logo.log") @(
    "Foreground Masking\Optimisation\cross_validate_toy_objects_MTObjects.py",
    "--clean-list", $Names, "--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot,
    "--output-dir", $MtoCV, "--injection-manifest", $InjectionManifest,
    "--cv-injection-set", "cross_validation", "--evaluation-injection-set", "winner_selection",
    "--initial-points", "8", "--max-iter", "32", "--workers", "$Workers",
    "--toys-per-image", "6", "--truth-dilation", "1", "--toy-peak-sigma-min", "6",
    "--toy-peak-sigma-max", "30", "--detect-on", "original"
)
}

$SepFinalArguments = @(
    "Foreground Masking\Optimisation\optimise_toy_objects_SEP.py",
    "--manifest", $Manifest, "--pc", $PC, "--output-dir", $SepFinal
) + @("--names") + @($GalaxyNames) + @(
    "--max-images", "11", "--injection-manifest", $InjectionManifest, "--injection-set", "cross_validation",
    "--initial-points", "8", "--max-iter", "32", "--workers", "$Workers", "--seed", "202608263",
    "--study-name", "sep-toy-clean11-final", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30", "--detect-on", "original"
)
Run-Stage "SEP final optimisation on all 11" (Join-Path $LogRoot "04_sep_final_all11.log") $SepFinalArguments

$MtoFinalArguments = @(
    "Foreground Masking\Optimisation\optimise_toy_objects_MTObjects.py",
    "--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot,
    "--output-dir", $MtoFinal
) + @("--names") + @($GalaxyNames) + @(
    "--max-images", "11",
    "--injection-manifest", $InjectionManifest, "--injection-set", "cross_validation",
    "--initial-points", "8", "--max-iter", "32", "--workers", "$Workers", "--seed", "202608264",
    "--study-name", "mtobjects-toy-clean11-final", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30", "--mtobjects-detect-on", "original"
)
Run-Stage "MTObjects final optimisation on all 11" (Join-Path $LogRoot "05_mtobjects_final_all11.log") $MtoFinalArguments

Write-Host "All clean-11 leave-one-out and final optimisation stages completed." -ForegroundColor Green
Write-Host "Results: $Control"
Write-Host "This window will remain open for review."
