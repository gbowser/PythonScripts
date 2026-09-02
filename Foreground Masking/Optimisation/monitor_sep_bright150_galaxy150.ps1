$ErrorActionPreference = 'SilentlyContinue'
$Host.UI.RawUI.WindowTitle = 'SEP + MTObjects: 1.5x Sersic Galaxy Size Progress'
$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity'
$sepLog = Join-Path $root 'sep_galaxy150_cross_validation.log'
$mtoLog = Join-Path $root 'mto_galaxy150_cross_validation.log'
$mergeLog = Join-Path $root 'sep_merging_sensitivity.log'
$supervisorLog = Join-Path $root 'windows_pipeline_supervisor.log'

while ($true) {
    Clear-Host
    $mergingStarted = Test-Path -LiteralPath $mergeLog
    $mtoStarted = Test-Path -LiteralPath $mtoLog
    $method = if ($mergingStarted) { 'SEP merging sensitivity' } elseif ($mtoStarted) { 'MTObjects' } else { 'SEP' }
    $log = if ($mergingStarted) { $mergeLog } elseif ($mtoStarted) { $mtoLog } else { $sepLog }
    $statePath = Join-Path $root $(if ($mtoStarted) { 'mto_galaxy150_watchdog_state.json' } else { 'sep_galaxy150_watchdog_state.json' })
    Write-Host 'SEP + MTOBJECTS — 1.5x SERSIC-GALAXY SIZE + MERGING TEST' -ForegroundColor Cyan
    Write-Host ('Updated: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    Write-Host 'Stars unchanged | Sersic radii x1.5 | peaks unchanged at 9-45 sigma'
    Write-Host ('Current method: {0}' -f $method) -ForegroundColor Green
    Write-Host ''
    if (Test-Path -LiteralPath $log) {
        $lines = Get-Content -LiteralPath $log -Tail 500
        Write-Host 'STAGE' -ForegroundColor Yellow
        $lines | Where-Object { $_ -match 'Starting (MTObjects )?fold|(MTObjects )?Fold \d+/22 complete|Starting (original|residual) detection study|Experiment complete|Cross-validation winner|RuntimeError:|Traceback' } |
            Select-Object -Last 6 | ForEach-Object { Write-Host $_ }
        Write-Host ''
        Write-Host 'LATEST EVALUATION' -ForegroundColor Yellow
        $evaluation = $lines | Where-Object { $_ -match '\] eval \d+:|\] (original|residual) trial \d+/' } | Select-Object -Last 1
        if ($evaluation) { Write-Host $evaluation } else { Write-Host 'Preparing images...' }
        Write-Host ''
        Write-Host 'RECENT ACTIVITY' -ForegroundColor Yellow
        $lines | Select-Object -Last 12 | ForEach-Object { Write-Host $_ }
    }
    Write-Host ''
    Write-Host 'SUPERVISION' -ForegroundColor Yellow
    if (Test-Path -LiteralPath $supervisorLog) {
        Write-Host 'Windows-hosted supervisor active (the old WSL watchdog file is retired).' -ForegroundColor Green
        Get-Content -LiteralPath $supervisorLog -Tail 4 | ForEach-Object { Write-Host $_ }
    } elseif (-not $mergingStarted -and (Test-Path -LiteralPath $statePath)) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        Write-Host ('Status: {0} | processes: {1} | restarts: {2} | checked: {3}' -f $state.status, $state.process_count, $state.restarts, $state.checked_at)
    } else {
        Write-Host 'No supervisor state is available.' -ForegroundColor Red
    }
    Write-Host ''
    $queueState = Join-Path $root 'sep_merging_after_mto_queue.log'
    if (Test-Path -LiteralPath $queueState) {
        Write-Host 'QUEUE' -ForegroundColor Yellow
        Get-Content -LiteralPath $queueState -Tail 3 | ForEach-Object { Write-Host $_ }
    }
    Write-Host 'Refreshes every 10 seconds. Closing this window does not stop the batch.' -ForegroundColor Green
    Start-Sleep -Seconds 10
}
