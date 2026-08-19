$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
$DataRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$SepBest = Join-Path $DataRoot "sep toy cross validation\20260817_161404\sep_toy_cross_validation_best.json"
$MtoBest = Join-Path $DataRoot "mtobjects toy recovery followup\20260816_063455\mtobjects_toy_cross_validation_best.json"
$SepOutput = Join-Path $DataRoot "SEP all galaxy batch\sep_toy_cv_20260817_161404"
$MtoOutput = Join-Path $DataRoot "mtobjects all galaxy batch\mtobjects_toy_recovery_20260816_063455_eight_panel_aligned"
$LogRoot = Join-Path $DataRoot "toy object green boundary regeneration\20260819"
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "SEP + MTObjects Toy Objects - green truth boundaries"
Set-Location $Repo

function Invoke-LoggedPython([string]$Name, [string]$Script, [string[]]$Arguments, [string]$LogName) {
    Write-Host ""
    Write-Host $Name -ForegroundColor Cyan
    & $Python $Script @Arguments 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath (Join-Path $LogRoot $LogName)
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE" }
}

Write-Host "Regenerating both canonical Toy Objects PNG batches" -ForegroundColor Green
Write-Host "Top-right panel: green border around every injected toy"

Invoke-LoggedPython `
    "SEP Toy Objects: 182 PNGs" `
    "Foreground Masking\Batch tools\batch_toy_objects_SEP.py" `
    @("--best-json", $SepBest, "--output-dir", $SepOutput, "--max-images", "182",
      "--toys-per-image", "6", "--toy-seed", "202608299", "--truth-dilation", "1",
      "--run-label", "SEP Toy Objects science-image CV 20260817_161404", "--replace-summary") `
    "sep_toy_green_boundaries.log"

Invoke-LoggedPython `
    "MTObjects Toy Objects: 182 PNGs" `
    "Foreground Masking\Batch tools\batch_toy_objects_MTObjects.py" `
    @("--best-json", $MtoBest, "--output-dir", $MtoOutput, "--max-images", "182",
      "--toys-per-image", "6", "--toy-seed", "202608299", "--truth-dilation", "1",
      "--run-label", "MTObjects Toy Objects recovery 20260816_063455", "--replace-summary") `
    "mtobjects_toy_green_boundaries.log"

Write-Host "Both Toy Objects batches completed successfully." -ForegroundColor Green
Write-Host "SEP: $SepOutput"
Write-Host "MTObjects: $MtoOutput"
Read-Host "Press Enter to close"
