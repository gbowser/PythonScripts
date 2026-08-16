param([ValidateSet("Desktop", "Laptop")][string]$PC = "Desktop")

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$MTObjectsRoot = Join-Path $Repo "mtobjects"
$MTBest = Join-Path $DataRoot "mtobjects toy recovery followup\20260816_063455\mtobjects_toy_cross_validation_best.json"
$SEPBest = Join-Path $Repo "Foreground Masking\Optimisation\sep_toy_cv_20260815_175144_reconstructed_best.json"
$MTOutput = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_toy_recovery_20260816_063455_eight_panel_aligned"
$SEPOutput = Join-Path $DataRoot "SEP all galaxy batch\sep_toy_cv_20260815_175144_eight_panel_aligned"
New-Item -ItemType Directory -Force -Path $MTOutput, $SEPOutput | Out-Null
$Host.UI.RawUI.WindowTitle = "SEP and MTObjects Toy Objects - aligned eight-panel PNG batches"
Set-Location $Repo

Write-Host "Corrected Toy Objects eight-panel batches" -ForegroundColor Cyan
Write-Host "Title is reserved above row 1; profile x-axis limits and widths match the panels above."
Write-Host "Starting MTObjects (182 galaxies). Output: $MTOutput"
$MTSummary = Join-Path $MTOutput "mtobjects_optimised_apply_summary.csv"
$MTMode = if(Test-Path $MTSummary){"--resume-output-dir"}else{"--output-dir"}
& $Python "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py" `
    --manifest $Manifest --pc $PC --mtobjects-root $MTObjectsRoot --best-json $MTBest `
    --source toy-object --run-label "MTObjects recovery aligned eight-panel" $MTMode $MTOutput `
    --max-images 182 --toys-per-image 6 --toy-seed 202608299 --truth-dilation 1 `
    2>&1 | Tee-Object -FilePath (Join-Path $MTOutput "batch.log") -Append
if($LASTEXITCODE -ne 0){Write-Host "MTObjects batch stopped with exit code $LASTEXITCODE" -ForegroundColor Red; Read-Host "Press Enter to close"; exit $LASTEXITCODE}

Write-Host "MTObjects complete. Starting SEP (182 galaxies). Output: $SEPOutput" -ForegroundColor Green
$SEPSummary = Join-Path $SEPOutput "sep_optimised_apply_summary.csv"
$SEPMode = if(Test-Path $SEPSummary){"--resume-output-dir"}else{"--output-dir"}
& $Python "Foreground Masking\Batch tools\batch_toy_objects_SEP.py" `
    --manifest $Manifest --pc $PC --best-json $SEPBest --source toy-object `
    --run-label "SEP Toy Objects aligned eight-panel" $SEPMode $SEPOutput `
    --max-images 182 --toys-per-image 6 --toy-seed 202608299 --truth-dilation 1 `
    2>&1 | Tee-Object -FilePath (Join-Path $SEPOutput "batch.log") -Append
if($LASTEXITCODE -eq 0){Write-Host "Both corrected PNG batches completed successfully." -ForegroundColor Green}else{Write-Host "SEP batch stopped with exit code $LASTEXITCODE" -ForegroundColor Red}
Read-Host "Press Enter to close"
exit $LASTEXITCODE
