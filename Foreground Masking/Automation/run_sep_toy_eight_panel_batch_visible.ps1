param([ValidateSet("Desktop", "Laptop")][string]$PC = "Desktop")

$ErrorActionPreference = "Continue"
$PSNativeCommandUseErrorActionPreference = $false
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$DataRoot = Join-Path $ResearchRoot "Remove foreground objects"
$Manifest = Join-Path $Repo "Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv"
$BestJson = Join-Path $Repo "Foreground Masking\Optimisation\sep_toy_cv_20260815_175144_reconstructed_best.json"
$OutputRoot = Join-Path $DataRoot "SEP all galaxy batch\sep_toy_cv_20260815_175144_eight_panel_toys"
$Summary = Join-Path $OutputRoot "sep_optimised_apply_summary.csv"
$OutputMode = if (Test-Path -LiteralPath $Summary) { "--resume-output-dir" } else { "--output-dir" }
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null

$Host.UI.RawUI.WindowTitle = "SEP Toy Objects - corrected eight-panel PNG batch"
Set-Location $Repo
Write-Host "SEP Toy Objects: corrected eight-panel PNG batch" -ForegroundColor Cyan
Write-Host "Rows: Original / Original + Toys; Mask / Recovered; Isophotes; Bar-major profiles"
Write-Host "Recovered outlines: green=mask region overlapping injected truth; red=false mask region"
Write-Host "Output: $OutputRoot"

& $Python "Foreground Masking\Batch tools\batch_toy_objects_SEP.py" `
    --manifest $Manifest --pc $PC --best-json $BestJson --source toy-object `
    --run-label "SEP Toy Objects corrected eight-panel" $OutputMode $OutputRoot `
    --max-images 182 --toys-per-image 6 --toy-seed 202608299 --truth-dilation 1 `
    2>&1 | Tee-Object -FilePath (Join-Path $OutputRoot "eight_panel_batch.log") -Append

if ($LASTEXITCODE -eq 0) {
    Write-Host "SEP corrected eight-panel batch completed successfully." -ForegroundColor Green
} else {
    Write-Host "SEP corrected batch stopped with exit code $LASTEXITCODE." -ForegroundColor Red
}
Read-Host "Press Enter to close"
exit $LASTEXITCODE
