$ErrorActionPreference = "Stop"

$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$Batch = Join-Path $Repo "Foreground Masking\Batch tools\batch_spike_gate_SEP.py"
$Best = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\spike gate science image comparison\20260818_065824\SEP optimisation\20260818_065825\sep_spike_optimisation_best.json"
$Output = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\SEP all galaxy batch\sep_spike_gate_20260818_065824"

$Host.UI.RawUI.WindowTitle = "SEP Spike Gate - regenerate 182 corrected panels"
Set-Location -LiteralPath $Repo

Write-Host "Regenerating SEP / Spike Gate diagnostic panels"
Write-Host "Output: $Output"
Write-Host "The existing incorrectly labelled PNGs will be overwritten."

& $Python $Batch `
    --best-json $Best `
    --output-dir $Output `
    --max-images 182 `
    --run-label "SEP science image + residual Spike Gate 20260818_065824" `
    --spike-gate-detect-on residual `
    --replace-summary 2>&1 | ForEach-Object { Write-Host $_ }

if ($LASTEXITCODE -ne 0) {
    Write-Host "SEP Spike Gate regeneration failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit $LASTEXITCODE
}

Write-Host "SEP Spike Gate regeneration completed successfully." -ForegroundColor Green
Write-Host "Output: $Output"
Read-Host "Press Enter to close"
