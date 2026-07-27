param(
    [Parameter(Mandatory = $true)]
    [int]$ProcessIdToWaitFor,

    [Parameter(Mandatory = $true)]
    [string]$SourceDir,

    [Parameter(Mandatory = $true)]
    [string]$DestinationDir
)

$ErrorActionPreference = "Stop"

while (Get-Process -Id $ProcessIdToWaitFor -ErrorAction SilentlyContinue) {
    Start-Sleep -Seconds 15
}

New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null

$files = @(
    "photutils_parameter_optimisation_summary.csv",
    "photutils_parameter_optimisation_details.csv"
)

foreach ($file in $files) {
    $source = Join-Path $SourceDir $file
    $destination = Join-Path $DestinationDir $file

    if (Test-Path -LiteralPath $source) {
        if (Test-Path -LiteralPath $destination) {
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $backup = Join-Path $DestinationDir "$([IO.Path]::GetFileNameWithoutExtension($file))_backup_$timestamp$([IO.Path]::GetExtension($file))"
            Move-Item -LiteralPath $destination -Destination $backup
        }

        Move-Item -LiteralPath $source -Destination $destination
    }
}

