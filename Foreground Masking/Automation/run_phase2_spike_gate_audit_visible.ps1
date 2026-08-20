$ErrorActionPreference = "Continue"

$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Output = Join-Path $DataRoot "Spike Gate Phase 2 audit\$Stamp"
$SepOptimiser = Join-Path $Repo "Foreground Masking\Optimisation\optimise_spike_gate_SEP.py"
$MtoOptimiser = Join-Path $Repo "Foreground Masking\Optimisation\optimise_spike_gate_MTObjects.py"
$Diagnostics = Join-Path $Repo "Foreground Masking\Optimisation\evaluate_constrained_spike_gate_batch.py"
$Names = @(
    "NGC4532", "NGC1559", "NGC4020", "NGC7764", "IC3521",
    "NGC4559", "NGC4449", "NGC4214", "NGC4981", "NGC0672",
    "NGC3627", "NGC1313", "NGC2903", "NGC0918", "ESO079-005"
)

New-Item -ItemType Directory -Force -Path $Output | Out-Null
$Host.UI.RawUI.WindowTitle = "Spike Gate Phase 2 - component-gated audit"
Set-Location -LiteralPath $Repo
Write-Host "Phase 2 Spike Gate audit" -ForegroundColor Cyan
Write-Host "15 gate-positive stress-test galaxies; science-image SEP/MTO; residual-only gate"
Write-Host "Output: $Output"

$SepDir = Join-Path $Output "SEP"
Write-Host "`n=== SEP short optimisation (24 trials) ===" -ForegroundColor Yellow
& $Python $SepOptimiser --output-dir $SepDir --names $Names --max-images 15 --require-spikes `
    --initial-points 8 --max-iter 16 --workers 4 --seed 20260820 `
    --study-name "sep-spike-phase2-audit" --spike-gate-detect-on residual `
    --detect-thresh-min 0.8 --detect-thresh-max 5.0 --minarea-min 3 --minarea-max 80 `
    --dilation-radius-min 0 --dilation-radius-max 4 --max-area-search 2500 2>&1 | `
    Tee-Object -FilePath (Join-Path $Output "sep_audit.log") | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "SEP audit failed with exit code $LASTEXITCODE" }
$SepBest = Get-ChildItem -LiteralPath $SepDir -Recurse -Filter "sep_spike_optimisation_best.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $Python $Diagnostics --algorithm SEP --best-json $SepBest.FullName `
    --output-csv (Join-Path $Output "SEP_phase2_audit.csv") --names $Names
if ($LASTEXITCODE -ne 0) { throw "SEP diagnostics failed with exit code $LASTEXITCODE" }

$MtoDir = Join-Path $Output "MTO"
Write-Host "`n=== MTObjects short optimisation (24 trials) ===" -ForegroundColor Yellow
& $Python $MtoOptimiser --output-dir $MtoDir --names $Names --max-images 15 --require-spikes `
    --initial-points 8 --max-iter 16 --workers 4 --seed 20260830 `
    --study-name "mto-spike-phase2-audit" --spike-gate-detect-on residual `
    --bg-variance-min 0.001 --bg-variance-max 100 --bg-variance-step 0 2>&1 | `
    Tee-Object -FilePath (Join-Path $Output "mto_audit.log") | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "MTObjects audit failed with exit code $LASTEXITCODE" }
$MtoBest = Get-ChildItem -LiteralPath $MtoDir -Recurse -Filter "mtobjects_spike_optimisation_best.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& $Python $Diagnostics --algorithm MTObjects --best-json $MtoBest.FullName `
    --output-csv (Join-Path $Output "MTO_phase2_audit.csv") --names $Names
if ($LASTEXITCODE -ne 0) { throw "MTObjects diagnostics failed with exit code $LASTEXITCODE" }

Write-Host "`nPhase 2 audit completed. Codex will review these results before any full rerun." -ForegroundColor Green
Write-Host "Output: $Output"
Read-Host "Press Enter to close"
