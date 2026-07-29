param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [Parameter(Mandatory = $true)]
    [string]$LogPath,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"
$ForegroundDir = Split-Path -Parent $PSScriptRoot
$Compositor = Join-Path $ForegroundDir "Utilities\make_all_method_galaxy_comparison_pngs.py"
$Python = (Get-Command python).Source

$Host.UI.RawUI.WindowTitle = "All-method galaxy comparison compositor"
& $Python $Compositor --pc $PC --output-dir $OutputDir 2>&1 | Tee-Object -FilePath $LogPath
$exitCode = $LASTEXITCODE
Write-Host "Compositor finished with exit code $exitCode."
exit $exitCode
