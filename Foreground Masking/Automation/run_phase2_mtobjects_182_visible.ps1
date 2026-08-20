$ErrorActionPreference = "Continue"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Output = Join-Path $DataRoot "MTO\Spike Gate\$Stamp"
$Batch = Join-Path $Repo "Foreground Masking\Batch tools\batch_spike_gate_MTObjects.py"
$AuditRoot = Join-Path $DataRoot "Spike Gate Phase 2 audit\20260819_200208\MTO"
$Best = Get-ChildItem -LiteralPath $AuditRoot -Recurse -Filter "mtobjects_spike_optimisation_best.json" | `
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $Best) { throw "Phase 2 MTObjects best-parameter JSON was not found." }

New-Item -ItemType Directory -Force -Path $Output | Out-Null
$Host.UI.RawUI.WindowTitle = "MTObjects Phase 2 Spike Gate - 182 galaxies"
Set-Location -LiteralPath $Repo
Write-Host "MTObjects Phase 2 Spike Gate: 182-galaxy PNG batch" -ForegroundColor Cyan
Write-Host "Science-image segmentation; residual Spike Gate; gate-supported components only"
Write-Host "Parameters: $($Best.FullName)"
Write-Host "Output: $Output"

& $Python $Batch --source spike-gate --best-json $Best.FullName --output-dir $Output `
    --run-label "MTObjects Phase 2 Spike Gate" --dpi 180 2>&1 | `
    Tee-Object -FilePath (Join-Path $Output "mtobjects_phase2_182.log") | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "MTObjects 182-galaxy batch failed with exit code $LASTEXITCODE" }

Write-Host "`nMTObjects Phase 2 batch completed successfully." -ForegroundColor Green
Write-Host "Output: $Output"
Read-Host "Press Enter to close"
