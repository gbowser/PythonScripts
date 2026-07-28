$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$LogRoot = Join-Path $ForegroundDir "run_logs\stability_20260727"
$BatchControlLog = Join-Path $LogRoot "stop_and_visible_batches.log"
$ControlLog = Join-Path $LogRoot "comparison_panels_scheduler.log"
$Compositor = Join-Path $ForegroundDir "Utilities\make_all_method_galaxy_comparison_pngs.py"
$Python = (Get-Command python).Source

function Write-ControlLog([string]$Message) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Write-Host $line
    Add-Content -LiteralPath $ControlLog -Value $line -Encoding utf8
}

Write-ControlLog "Waiting for all four visible batch jobs to finish."
while ($true) {
    if (Test-Path -LiteralPath $BatchControlLog) {
        $content = Get-Content -Raw -LiteralPath $BatchControlLog
        if ($content -match 'All visible batch jobs finished') { break }
    }
    Start-Sleep -Seconds 15
}

Write-ControlLog "Batch sequence complete; starting all-method comparison panel compositor."
$Host.UI.RawUI.WindowTitle = "All-method galaxy comparison panels"
& $Python $Compositor
$exitCode = $LASTEXITCODE
Write-ControlLog "Comparison panel compositor finished with exit code $exitCode."
Write-Host "Press Enter to close this window."
Read-Host
exit $exitCode
