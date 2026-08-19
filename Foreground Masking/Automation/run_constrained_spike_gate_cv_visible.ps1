# Optuna writes ordinary informational messages to stderr. Windows PowerShell
# wraps those lines as NativeCommandError records, so Continue is required;
# each native command is still checked explicitly through $LASTEXITCODE.
$ErrorActionPreference = "Continue"

$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$CleanList = Join-Path $DataRoot "CleanGalaxies.txt"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$SepRoot = Join-Path $DataRoot "SEP\Spike Gate\$Stamp"
$MtoRoot = Join-Path $DataRoot "MTO\Spike Gate\$Stamp"
$LogDir = Join-Path $DataRoot "Spike Gate constrained comparison\$Stamp\logs"
$ComparisonDir = Split-Path $LogDir -Parent
$SepOptimiser = Join-Path $Repo "Foreground Masking\Optimisation\optimise_spike_gate_SEP.py"
$MtoOptimiser = Join-Path $Repo "Foreground Masking\Optimisation\optimise_spike_gate_MTObjects.py"
$Selector = Join-Path $Repo "Foreground Masking\Optimisation\select_constrained_spike_gate_winner.py"
$Diagnostics = Join-Path $Repo "Foreground Masking\Optimisation\evaluate_constrained_spike_gate_batch.py"
$SepBatch = Join-Path $Repo "Foreground Masking\Batch tools\batch_spike_gate_SEP.py"
$MtoBatch = Join-Path $Repo "Foreground Masking\Batch tools\batch_spike_gate_MTObjects.py"

New-Item -ItemType Directory -Force -Path $SepRoot, $MtoRoot, $LogDir | Out-Null
$Names = @(Get-Content -LiteralPath $CleanList | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($Names.Count -ne 40 -or (@($Names | Sort-Object -Unique)).Count -ne 40) {
    throw "CleanGalaxies.txt must contain exactly 40 unique galaxies; found $($Names.Count)."
}

$Host.UI.RawUI.WindowTitle = "Constrained Spike Gate CV - SEP and MTO"
Set-Location -LiteralPath $Repo
Write-Host "Constrained Spike Gate four-fold optimisation" -ForegroundColor Cyan
Write-Host "Run stamp: $Stamp"
Write-Host "Design: four folds; 30 train / 10 held out; residual Spike Gate; science-image masking"
Write-Host "SEP output: $SepRoot"
Write-Host "MTO output: $MtoRoot"

$SepBest = @()
$MtoBest = @()
for ($fold = 1; $fold -le 4; $fold++) {
    $heldStart = ($fold - 1) * 10
    $held = @($Names[$heldStart..($heldStart + 9)])
    $train = @($Names | Where-Object { $held -notcontains $_ })
    Write-Host ""
    Write-Host "=== Fold $fold/4: SEP training on 30 galaxies ===" -ForegroundColor Yellow
    $foldDir = Join-Path $SepRoot "optimisation\fold_$fold"
    & $Python $SepOptimiser --output-dir $foldDir --names $train --max-images 30 --no-require-spikes `
        --initial-points 8 --max-iter 32 --workers 4 --seed (20260819 + $fold) `
        --study-name "sep-spike-constrained-fold-$fold" --spike-gate-detect-on residual `
        --detect-thresh-min 0.8 --detect-thresh-max 5.0 --minarea-min 3 --minarea-max 80 `
        --dilation-radius-min 0 --dilation-radius-max 4 --max-area-search 2500 2>&1 | `
        Tee-Object -FilePath (Join-Path $LogDir "sep_fold_$fold.log") | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "SEP fold $fold failed with exit code $LASTEXITCODE" }
    $best = Get-ChildItem -LiteralPath $foldDir -Recurse -Filter "sep_spike_optimisation_best.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $best) { throw "SEP fold $fold did not produce a best JSON." }
    $SepBest += $best.FullName

    Write-Host "=== Fold $fold/4: MTObjects training on 30 galaxies ===" -ForegroundColor Yellow
    $foldDir = Join-Path $MtoRoot "optimisation\fold_$fold"
    & $Python $MtoOptimiser --output-dir $foldDir --names $train --max-images 30 --no-require-spikes `
        --initial-points 8 --max-iter 32 --workers 4 --seed (20260829 + $fold) `
        --study-name "mto-spike-constrained-fold-$fold" --spike-gate-detect-on residual `
        --bg-variance-min 0.001 --bg-variance-max 100 --bg-variance-step 0 2>&1 | `
        Tee-Object -FilePath (Join-Path $LogDir "mto_fold_$fold.log") | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "MTObjects fold $fold failed with exit code $LASTEXITCODE" }
    $best = Get-ChildItem -LiteralPath $foldDir -Recurse -Filter "mtobjects_spike_optimisation_best.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $best) { throw "MTObjects fold $fold did not produce a best JSON." }
    $MtoBest += $best.FullName
}

Write-Host "=== Evaluating fold winners on held-out sets and all 40 ===" -ForegroundColor Cyan
$SepSelection = Join-Path $SepRoot "optimisation\cross_validation"
$MtoSelection = Join-Path $MtoRoot "optimisation\cross_validation"
& $Python $Selector --algorithm SEP --clean-list $CleanList --candidate-json $SepBest --output-dir $SepSelection
if ($LASTEXITCODE -ne 0) { throw "SEP cross-validation selection failed." }
& $Python $Selector --algorithm MTObjects --clean-list $CleanList --candidate-json $MtoBest --output-dir $MtoSelection
if ($LASTEXITCODE -ne 0) { throw "MTObjects cross-validation selection failed." }
$SepWinner = Join-Path $SepSelection "sep_spike_constrained_cv_best.json"
$MtoWinner = Join-Path $MtoSelection "mtobjects_spike_constrained_cv_best.json"

Write-Host "=== SEP 182-galaxy PNG batch ===" -ForegroundColor Cyan
$SepPng = Join-Path $SepRoot "PNG"
& $Python $SepBatch --best-json $SepWinner --output-dir $SepPng --max-images 182 `
    --run-label "SEP constrained Spike Gate $Stamp" --spike-gate-detect-on residual --replace-summary 2>&1 | `
    Tee-Object -FilePath (Join-Path $LogDir "sep_182_batch.log") | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "SEP 182-galaxy batch failed." }

Write-Host "=== MTObjects 182-galaxy PNG batch ===" -ForegroundColor Cyan
$MtoPng = Join-Path $MtoRoot "PNG"
& $Python $MtoBatch --best-json $MtoWinner --output-dir $MtoPng --max-images 182 `
    --run-label "MTObjects constrained Spike Gate $Stamp" --replace-summary 2>&1 | `
    Tee-Object -FilePath (Join-Path $LogDir "mto_182_batch.log") | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "MTObjects 182-galaxy batch failed." }

Write-Host "=== Calculating per-galaxy 2-D Gate diagnostics ===" -ForegroundColor Cyan
$SepMetrics = Join-Path $SepRoot "spike_gate_diagnostics.csv"
$MtoMetrics = Join-Path $MtoRoot "spike_gate_diagnostics.csv"
& $Python $Diagnostics --algorithm SEP --best-json $SepWinner --output-csv $SepMetrics
if ($LASTEXITCODE -ne 0) { throw "SEP diagnostics failed." }
& $Python $Diagnostics --algorithm MTObjects --best-json $MtoWinner --output-csv $MtoMetrics
if ($LASTEXITCODE -ne 0) { throw "MTObjects diagnostics failed." }

$sepRows = @{}; Import-Csv $SepMetrics | ForEach-Object { $sepRows[$_.image] = $_ }
$comparison = Import-Csv $MtoMetrics | ForEach-Object {
    $s = $sepRows[$_.image]
    [pscustomobject]@{
        galaxy = $_.image
        sep_masked_fraction = $s.masked_fraction
        mto_masked_fraction = $_.masked_fraction
        sep_gate_recovery = $s.gate_recovery
        mto_gate_recovery = $_.gate_recovery
        sep_candidate_detection_rate = $s.candidate_detection_rate
        mto_candidate_detection_rate = $_.candidate_detection_rate
        sep_excess_mask_fraction = $s.excess_mask_fraction
        mto_excess_mask_fraction = $_.excess_mask_fraction
        sep_protected_galaxy_loss = $s.protected_galaxy_loss
        mto_protected_galaxy_loss = $_.protected_galaxy_loss
    }
}
$ComparisonCsv = Join-Path $ComparisonDir "SEP_MTO_constrained_spike_gate_comparison.csv"
$comparison | Sort-Object galaxy | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $ComparisonCsv

Write-Host ""
Write-Host "All constrained Spike Gate optimisation and PNG work completed." -ForegroundColor Green
Write-Host "SEP: $SepRoot"
Write-Host "MTO: $MtoRoot"
Write-Host "Comparison: $ComparisonCsv"
Read-Host "Press Enter to close"
