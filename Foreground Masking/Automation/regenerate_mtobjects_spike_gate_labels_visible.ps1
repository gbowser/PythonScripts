$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$BestJson = Join-Path $DataRoot "spike gate science image comparison\20260818_065824\MTObjects optimisation\20260818_072738\mtobjects_spike_optimisation_best.json"
$Output = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_spike_gate_20260818_065824"
$Log = Join-Path $Output "regenerate_correct_spike_gate_labels.log"
$Host.UI.RawUI.WindowTitle = "Regenerate MTObjects Spike Gate PNG labels"
Set-Location $Repo

Write-Host "Regenerating all 182 MTObjects Spike Gate PNGs in place" -ForegroundColor Cyan
Write-Host "Title: MTObjects Spike Gate"
Write-Host "Top-right panel: Residual Spike Gate Image"
Write-Host "Output: $Output"

& $Python "Foreground Masking\Batch tools\batch_spike_gate_MTObjects.py" `
    --best-json $BestJson --output-dir $Output --max-images 182 `
    --run-label "MTObjects science image + residual Spike Gate 20260818_065824" `
    --replace-summary 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $Log

if ($LASTEXITCODE -ne 0) {
    Write-Host "Regeneration failed with exit code $LASTEXITCODE" -ForegroundColor Red
} else {
    Write-Host "Regeneration completed successfully." -ForegroundColor Green
}
Read-Host "Press Enter to close"
