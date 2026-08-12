$ErrorActionPreference = "Stop"
# Python/Optuna writes normal informational messages to stderr. PowerShell 5
# otherwise promotes those records to terminating NativeCommandError objects
# when ErrorActionPreference is Stop.
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$manifest = Join-Path $PSScriptRoot "mean-parameter-4sets\local_mtobjects_182_manifest.csv"
$mtobjectsRoot = Join-Path $repoRoot "mtobjects"
$outputRoot = Join-Path $PSScriptRoot "separate-low-foreground-toy-optimisations\mtobjects-toy-visible"
$logRoot = Join-Path $PSScriptRoot "separate-low-foreground-toy-optimisations\logs"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logRoot "mtobjects_toy_low_foreground_$stamp.log"
$names = @("IC1954", "IC4901", "NGC0289", "NGC0578", "NGC0986", "NGC1097", "NGC3359", "NGC3992", "NGC4133")

New-Item -ItemType Directory -Force -Path $outputRoot, $logRoot | Out-Null
$Host.UI.RawUI.WindowTitle = "MTObjects Toy optimisation - 9 low-foreground galaxies"
Set-Location $repoRoot

Write-Host "MTObjects Toy Objects optimisation" -ForegroundColor Cyan
Write-Host "Galaxy set: $($names -join ', ')"
Write-Host "Trials: 40 (8 initial + 32 further); workers: 9; seed: 202608045"
Write-Host "The optimiser prints remaining trials, rough ETA, and expected completion after each trial."
Write-Host "Transcript: $logPath"
Write-Host ""

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $python "Foreground Masking/Optimisation/optimise_toy_objects_MTObjects.py" `
    --manifest $manifest `
    --mtobjects-root $mtobjectsRoot `
    --output-dir $outputRoot `
    --names $names `
    --max-images 9 `
    --initial-points 8 `
    --max-iter 32 `
    --workers 9 `
    --seed 202608045 `
    --study-name "mtobjects-toy-low-foreground-9-visible" 2>&1 |
    Tee-Object -FilePath $logPath

$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($exitCode -eq 0) {
    Write-Host "`nOptimisation completed successfully." -ForegroundColor Green
} else {
    Write-Host "`nOptimisation failed with exit code $exitCode." -ForegroundColor Red
}
Write-Host "You may close this window."
