param(
    [string]$OutputRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_haigh_aligned_source_optimisation"
)

$LogPath = Join-Path $OutputRoot "haigh_aligned_cross_validation.log"
$PidPath = Join-Path $OutputRoot "haigh_aligned_cross_validation.pid"

while ($true) {
    Clear-Host
    Write-Host "Haigh-aligned SEP + MTObjects re-optimisation" -ForegroundColor Cyan
    Write-Host (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Write-Host "Output: $OutputRoot"

    $BatchPid = $null
    if (Test-Path -LiteralPath $PidPath) {
        $BatchPid = (Get-Content -LiteralPath $PidPath -Raw).Trim()
    }
    $Running = $false
    if ($BatchPid) {
        wsl.exe -d Ubuntu-24.04 -u root -- bash -lc "kill -0 $BatchPid 2>/dev/null"
        $Running = ($LASTEXITCODE -eq 0)
    }
    Write-Host ("Batch PID: {0} | State: {1}" -f $BatchPid, $(if ($Running) { "RUNNING" } else { "NOT RUNNING" })) -ForegroundColor $(if ($Running) { "Green" } else { "Yellow" })

    if (Test-Path -LiteralPath $LogPath) {
        $Lines = @(Get-Content -LiteralPath $LogPath)
        $SepFolds = @($Lines | Select-String -Pattern "Starting fold [0-9]+/22").Count
        $MtoFolds = @($Lines | Select-String -Pattern "Starting MTObjects fold [0-9]+/22").Count
        $Evaluations = @($Lines | Select-String -Pattern "eval [0-9]+:").Count
        Write-Host "SEP folds started: $SepFolds / 22"
        Write-Host "MTObjects folds started: $MtoFolds / 22"
        Write-Host "Trial evaluations logged: $Evaluations"
        Write-Host ""
        Write-Host "=== Latest activity ===" -ForegroundColor Cyan
        $Lines | Select-Object -Last 35
    } else {
        Write-Host "Waiting for the batch log to be created..."
    }

    if (-not $Running -and (Test-Path -LiteralPath $LogPath)) {
        Write-Host ""
        Write-Host "The batch process is no longer running. Review the final lines above." -ForegroundColor Yellow
        break
    }
    Start-Sleep -Seconds 15
}
