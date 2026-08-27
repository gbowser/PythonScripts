param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [string]$RunStamp = "clean11_logo_20260826_122730"
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
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$CleanList = Join-Path $Repo "Foreground Masking\Optimisation\clean_galaxies_11_20260826.txt"
$Control = Join-Path $DataRoot "Toy Objects paired optimisation\$RunStamp"
$SepBest = Join-Path $Control "sep_final_all11\20260826_193633\sep_toy_object_optimisation_best.json"
$MtoBest = Join-Path $Control "mtobjects_logo\mtobjects_toy_cross_validation_best.json"
$SepPng = Join-Path $DataRoot "SEP\Toy Objects\$RunStamp\PNG batch"
$MtoPng = Join-Path $DataRoot "MTObjects\Toy Objects\$RunStamp\PNG batch"
$Combined = Join-Path $DataRoot "Toy Objects comparison\$RunStamp"
$LogRoot = Join-Path $Control "logs"

foreach ($path in @($Python, $Manifest, $CleanList, $SepBest, $MtoBest)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required file not found: $path" }
}
foreach ($path in @($MtoPng, $Combined)) {
    if (Test-Path -LiteralPath $path) { throw "Output already exists; refusing to overwrite: $path" }
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
    finally { $ErrorActionPreference = $previousErrorActionPreference }
    $elapsed = (Get-Date) - $started
    if ($code -ne 0) { throw "$Name failed with exit code $code after $($elapsed.ToString('hh\:mm\:ss'))." }
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name complete in $($elapsed.ToString('hh\:mm\:ss'))." -ForegroundColor Green
}

$Host.UI.RawUI.WindowTitle = "S4G clean-11 LOGO-CV production PNG batches"
Set-Location $Repo
Write-Host "CLEAN-11 LOGO-CV PRODUCTION PNG BATCHES" -ForegroundColor Cyan
Write-Host "Run: $RunStamp"
Write-Host "SEP best: $SepBest"
Write-Host "MTObjects best: $MtoBest"

$SepOutputArguments = if (Test-Path -LiteralPath $SepPng -PathType Container) {
    @("--resume-output-dir", $SepPng)
} else {
    @("--output-dir", $SepPng)
}
$SepArguments = @(
    "Foreground Masking\Batch tools\batch_toy_objects_SEP.py",
    "--manifest", $Manifest, "--pc", $PC
) + $SepOutputArguments + @(
    "--best-json", $SepBest, "--source", "toy-object", "--run-label", $RunStamp,
    "--toy-seed", "202608299", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
    "--clean-galaxies-file", $CleanList, "--expected-clean-galaxies", "11",
    "--detect-on", "original", "--max-images", "182"
)
Run-Stage "SEP 182-galaxy PNG batch" (Join-Path $LogRoot "06_sep_png_batch.log") $SepArguments

Run-Stage "MTObjects 182-galaxy PNG batch" (Join-Path $LogRoot "07_mtobjects_png_batch.log") @(
    "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py",
    "--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot,
    "--output-dir", $MtoPng, "--best-json", $MtoBest, "--source", "toy-object",
    "--run-label", $RunStamp, "--toy-seed", "202608299", "--toys-per-image", "6",
    "--truth-dilation", "1", "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
    "--clean-galaxies-file", $CleanList, "--expected-clean-galaxies", "11", "--max-images", "182"
)

Run-Stage "182-galaxy side-by-side composite batch" (Join-Path $LogRoot "08_combined_png_batch.log") @(
    "Foreground Masking\Utilities\combine_toy_method_pngs.py",
    "--mto-dir", $MtoPng, "--sep-dir", $SepPng, "--output-dir", $Combined,
    "--gutter", "40", "--divider-width", "10", "--dash-length", "48", "--dash-gap", "28"
)

$sepCount = @(Get-ChildItem -LiteralPath $SepPng -File -Filter *.png).Count
$mtoCount = @(Get-ChildItem -LiteralPath $MtoPng -File -Filter *.png).Count
$combinedCount = @(Get-ChildItem -LiteralPath $Combined -File -Filter *.png).Count
if ($sepCount -ne 182 -or $mtoCount -ne 182 -or $combinedCount -ne 182) {
    throw "PNG count validation failed: SEP=$sepCount, MTObjects=$mtoCount, combined=$combinedCount; expected 182 each."
}

Write-Host "All PNG batches complete and validated: SEP=182, MTObjects=182, combined=182." -ForegroundColor Green
Write-Host "SEP: $SepPng"
Write-Host "MTObjects: $MtoPng"
Write-Host "Combined: $Combined"
Write-Host "The window will remain open for review."
