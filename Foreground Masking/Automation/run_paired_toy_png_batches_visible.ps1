param(
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop",
    [Parameter(Mandatory = $true)]
    [string]$RunStamp
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
$CleanList = Join-Path $DataRoot "CleanGalaxies.txt"
$SepRun = Join-Path $DataRoot "SEP\Toy Objects\$RunStamp"
$MtoRun = Join-Path $DataRoot "MTObjects\Toy Objects\$RunStamp"
$SepBest = Join-Path $SepRun "optimisation\sep_toy_cross_validation_best.json"
$MtoBest = Join-Path $MtoRun "optimisation\mtobjects_toy_cross_validation_best.json"
$SepPng = Join-Path $SepRun "PNG batch"
$MtoPng = Join-Path $MtoRun "PNG batch"
$Combined = Join-Path $DataRoot "Toy Objects comparison\$RunStamp"
$Control = Join-Path $DataRoot "Toy Objects paired optimisation\$RunStamp"
$LogRoot = Join-Path $Control "logs"

foreach ($path in @($SepBest, $MtoBest)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Optimisation winner not found: $path"
    }
}
foreach ($path in @($SepPng, $MtoPng, $Combined)) {
    if (Test-Path -LiteralPath $path) {
        throw "Output already exists; refusing to overwrite: $path"
    }
}
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

function Run-Stage {
    param([string]$Name, [string]$Log, [string[]]$Arguments)
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting $Name" -ForegroundColor Yellow
    $started = Get-Date
    & $Python @Arguments 2>&1 | Tee-Object -FilePath $Log -Append | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
    $elapsed = (Get-Date) - $started
    if ($code -ne 0) {
        throw "$Name failed with exit code $code after $($elapsed.ToString('hh\:mm\:ss'))."
    }
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Name complete in $($elapsed.ToString('hh\:mm\:ss'))." -ForegroundColor Green
}

$Host.UI.RawUI.WindowTitle = "Paired Toy Objects PNG Batches - SEP, MTObjects, Combined"
Set-Location $Repo
Write-Host "PAIRED TOY OBJECTS PNG BATCHES" -ForegroundColor Cyan
Write-Host "Run: $RunStamp"
Write-Host "Both methods use the original science image, seed 202608299, six toys, and 6-30 sigma peaks."

Run-Stage "SEP 182-galaxy PNG batch" (Join-Path $LogRoot "sep_png_batch.log") @(
    "Foreground Masking\Batch tools\batch_toy_objects_SEP.py",
    "--manifest", $Manifest, "--pc", $PC, "--output-dir", $SepPng,
    "--best-json", $SepBest, "--source", "toy-object", "--run-label", "paired-$RunStamp",
    "--toy-seed", "202608299", "--toys-per-image", "6", "--truth-dilation", "1",
    "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
    "--clean-galaxies-file", $CleanList, "--detect-on", "original"
)

Run-Stage "MTObjects 182-galaxy PNG batch" (Join-Path $LogRoot "mtobjects_png_batch.log") @(
    "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py",
    "--manifest", $Manifest, "--pc", $PC, "--mtobjects-root", $MTObjectsRoot,
    "--output-dir", $MtoPng, "--best-json", $MtoBest, "--source", "toy-object",
    "--run-label", "paired-$RunStamp", "--toy-seed", "202608299", "--toys-per-image", "6",
    "--truth-dilation", "1", "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
    "--clean-galaxies-file", $CleanList
)

Run-Stage "182-galaxy side-by-side composite batch" (Join-Path $LogRoot "combined_png_batch.log") @(
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
Write-Host "SEP:      $SepPng"
Write-Host "MTObjects: $MtoPng"
Write-Host "Combined: $Combined"
Write-Host "The window will remain open for review."
