$ErrorActionPreference = 'SilentlyContinue'
$Host.UI.RawUI.WindowTitle = '150%-Brightness SEP + MTObjects Optimisation Progress'

$runRoot = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_haigh_aligned_bright150_optimisation'
$runLog = Join-Path $runRoot 'haigh_aligned_bright150_cross_validation.log'
$watchState = Join-Path $runRoot 'haigh_aligned_bright150_watchdog_state.json'
$watchLog = Join-Path $runRoot 'haigh_aligned_bright150_watchdog.log'

while ($true) {
    Clear-Host
    Write-Host '150%-BRIGHTNESS SEP + MTOBJECTS OPTIMISATION' -ForegroundColor Cyan
    Write-Host ('Updated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    Write-Host ('Results: {0}' -f $runRoot)
    Write-Host ''

    if (Test-Path -LiteralPath $runLog) {
        $lines = Get-Content -LiteralPath $runLog -Tail 500
        $stage = $lines | Where-Object {
            $_ -match '^===|Starting (MTObjects )?fold|Fold \d+/22 complete|MTObjects fold \d+/22 complete|completed; SEP accepted='
        } | Select-Object -Last 6
        Write-Host 'STAGE' -ForegroundColor Yellow
        $stage | ForEach-Object { Write-Host $_ }
        Write-Host ''

        $evaluation = $lines | Where-Object { $_ -match '\] eval \d+:' } | Select-Object -Last 1
        Write-Host 'LATEST EVALUATION' -ForegroundColor Yellow
        if ($evaluation) { Write-Host $evaluation } else { Write-Host 'Preparing data or evaluating a completed fold...' }
        Write-Host ''

        Write-Host 'RECENT ACTIVITY' -ForegroundColor Yellow
        $lines | Select-Object -Last 14 | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host 'Waiting for the optimisation log to appear...'
    }

    Write-Host ''
    Write-Host 'WATCHDOG' -ForegroundColor Yellow
    if (Test-Path -LiteralPath $watchState) {
        $state = Get-Content -LiteralPath $watchState -Raw | ConvertFrom-Json
        Write-Host ('Status: {0} | processes: {1} | restarts: {2} | checked: {3}' -f `
            $state.status, $state.process_count, $state.restarts, $state.checked_at)
        Write-Host ('Seconds without log or CPU progress: {0}' -f $state.seconds_without_log_or_cpu_progress)
    } else {
        Write-Host 'Waiting for watchdog status...'
    }
    if (Test-Path -LiteralPath $watchLog) {
        Get-Content -LiteralPath $watchLog -Tail 2 | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
    }

    Write-Host ''
    Write-Host 'Refreshes every 10 seconds. Close this window to stop viewing; the batch will continue.' -ForegroundColor Green
    Start-Sleep -Seconds 10
}
