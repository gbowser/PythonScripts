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
$MtoBest = Join-Path $MtoRun "optimisation\mtobjects_toy_cross_validation_best.json"
$SepPng = Join-Path $SepRun "PNG batch"
$MtoPng = Join-Path $MtoRun "PNG batch"
$Combined = Join-Path $DataRoot "Toy Objects comparison\$RunStamp"
$Control = Join-Path $DataRoot "Toy Objects paired optimisation\$RunStamp"
$LogRoot = Join-Path $Control "logs"

$Host.UI.RawUI.WindowTitle = "Resume Paired Toy Objects PNG Batches - MTObjects then Combined"
Set-Location $Repo
Write-Host "RESUMING PAIRED TOY OBJECTS PNG BATCHES" -ForegroundColor Cyan
Write-Host "Run: $RunStamp"
Write-Host "Waiting for Dropbox paths after sign-in..."
for ($attempt=1; $attempt -le 60; $attempt++) {
    if ((Test-Path -LiteralPath $MtoBest -PathType Leaf) -and (Test-Path -LiteralPath $MtoPng -PathType Container)) { break }
    if ($attempt -eq 60) { throw "Required Dropbox paths were not available after five minutes." }
    Start-Sleep -Seconds 5
}

$sepSummary = Join-Path $SepPng "sep_optimised_apply_summary.csv"
$mtoSummary = Join-Path $MtoPng "mtobjects_optimised_apply_summary.csv"
$sepComplete = if (Test-Path -LiteralPath $sepSummary) { @((Import-Csv -LiteralPath $sepSummary) | Where-Object status -eq 'ok').Count } else { 0 }
$mtoComplete = if (Test-Path -LiteralPath $mtoSummary) { @((Import-Csv -LiteralPath $mtoSummary) | Where-Object status -eq 'ok').Count } else { 0 }
if ($sepComplete -ne 182) { throw "SEP prerequisite is incomplete: $sepComplete/182 successful." }
if ($mtoComplete -ge 182) { Write-Host "MTObjects was already complete; skipping directly to composites." -ForegroundColor Green }
else {
    Write-Host "Resuming MTObjects after $mtoComplete completed galaxies." -ForegroundColor Yellow
    & $Python "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py" `
        --manifest $Manifest --pc $PC --mtobjects-root $MTObjectsRoot `
        --resume-output-dir $MtoPng --best-json $MtoBest --source toy-object `
        --run-label "paired-$RunStamp" --toy-seed 202608299 --toys-per-image 6 `
        --truth-dilation 1 --toy-peak-sigma-min 6 --toy-peak-sigma-max 30 `
        --clean-galaxies-file $CleanList 2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "mtobjects_png_batch_resume.log") -Append | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "Resumed MTObjects batch failed with exit code $LASTEXITCODE." }
}

$mtoComplete = @((Import-Csv -LiteralPath $mtoSummary) | Where-Object status -eq 'ok').Count
if ($mtoComplete -ne 182) { throw "MTObjects resume validation failed: $mtoComplete/182 successful." }
if (Test-Path -LiteralPath $Combined) {
    $existingCombined = @(Get-ChildItem -LiteralPath $Combined -File -Filter *.png -ErrorAction SilentlyContinue).Count
    if ($existingCombined -eq 182) {
        Write-Host "Combined PNGs were already complete; retaining them." -ForegroundColor Green
    } else {
        throw "Combined output exists but is incomplete ($existingCombined/182). Remove or review it before resuming: $Combined"
    }
} else {
    & $Python "Foreground Masking\Utilities\combine_toy_method_pngs.py" `
        --mto-dir $MtoPng --sep-dir $SepPng --output-dir $Combined `
        --gutter 40 --divider-width 10 --dash-length 48 --dash-gap 28 `
        2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "combined_png_batch.log") -Append | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "Combined PNG batch failed with exit code $LASTEXITCODE." }
}

$sepCount = @(Get-ChildItem -LiteralPath $SepPng -File -Filter *.png).Count
$mtoCount = @(Get-ChildItem -LiteralPath $MtoPng -File -Filter *.png).Count
$combinedCount = @(Get-ChildItem -LiteralPath $Combined -File -Filter *.png).Count
if ($sepCount -ne 182 -or $mtoCount -ne 182 -or $combinedCount -ne 182) {
    throw "Final PNG count validation failed: SEP=$sepCount, MTObjects=$mtoCount, combined=$combinedCount."
}

Write-Host "All PNG sets complete: SEP=182, MTObjects=182, combined=182." -ForegroundColor Green
$AnalysisDir = Join-Path $Control "analysis"
Write-Host "Generating final paired statistics..." -ForegroundColor Yellow
& $Python "Foreground Masking\documentation\summarise_paired_toy_run.py" `
    --research-root $DataRoot --run-stamp $RunStamp --output-dir $AnalysisDir `
    2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "final_analysis.log") -Append | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "Final paired analysis failed with exit code $LASTEXITCODE." }

Write-Host "Creating the Methodology, Results/Conclusions and Further Improvements documents through Word COM..." -ForegroundColor Yellow
& (Join-Path $Repo "Foreground Masking\documentation\build_paired_toy_run_documents_com.ps1") `
    -ResearchRoot $DataRoot -RunStamp $RunStamp `
    2>&1 | Tee-Object -FilePath (Join-Path $LogRoot "documentation_build.log") -Append | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "Documentation build failed with exit code $LASTEXITCODE." }

Write-Host "Documents created. Codex will perform the final page-by-page visual QA when the session resumes." -ForegroundColor Green
Write-Host "The window will remain open for review."
