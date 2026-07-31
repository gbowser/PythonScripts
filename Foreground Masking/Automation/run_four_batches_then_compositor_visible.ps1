$ErrorActionPreference = "Continue"
$ForegroundDir = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python).Source
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $ForegroundDir "run_logs"
$LogPath = Join-Path $LogDir "four_batches_then_compositor_$Stamp.log"

$Host.UI.RawUI.WindowTitle = "Four foreground batches then PNG consolidation"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Transcript -LiteralPath $LogPath -Force | Out-Null

function Write-Status([string]$Message) {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
}

$Jobs = @(
    "batch_spike_gate_SEP.py",
    "batch_toy_objects_SEP.py",
    "batch_spike_gate_MTObjects.py",
    "batch_toy_objects_MTObjects.py"
)

$Failures = @()
foreach ($Job in $Jobs) {
    $Script = Join-Path $ForegroundDir $Job
    Write-Status "Starting $Job on Desktop."
    & $Python $Script --pc Desktop
    $Code = $LASTEXITCODE
    Write-Status "$Job finished with exit code $Code."
    if ($Code -ne 0) { $Failures += $Job }
}

$Compositor = Join-Path $ForegroundDir "Utilities\make_all_method_galaxy_comparison_pngs.py"
Write-Status "Starting all-method PNG consolidation using the newest full batch summaries."
& $Python $Compositor --pc Desktop
$CompositorCode = $LASTEXITCODE
Write-Status "PNG consolidation finished with exit code $CompositorCode."

if ($Failures.Count -gt 0) {
    Write-Status "Batch jobs with non-zero exit codes: $($Failures -join ', ')"
}
Write-Status "Sequence complete. Log: $LogPath"
Stop-Transcript | Out-Null

if ($CompositorCode -ne 0 -or $Failures.Count -gt 0) { exit 1 }
exit 0
