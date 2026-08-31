$ErrorActionPreference = 'SilentlyContinue'
$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation\MTObjects_multiseed_optimisation_pilot_v3\failure_mode_analysis'
$log = Join-Path $root 'failure_analysis_progress.log'

while ($true) {
    Clear-Host
    Write-Host 'MTObjects Failure-Mode Analysis' -ForegroundColor Cyan
    Write-Host ('Updated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    Write-Host ''

    if (Test-Path (Join-Path $root 'failure_analysis.complete')) {
        Write-Host 'STATUS: COMPLETED SUCCESSFULLY' -ForegroundColor Green
    } elseif (Test-Path (Join-Path $root 'failure_analysis.failed')) {
        Write-Host 'STATUS: FAILED - Codex will inspect and recover it' -ForegroundColor Red
    } elseif (Test-Path $log) {
        Write-Host 'STATUS: RUNNING' -ForegroundColor Yellow
    } else {
        Write-Host 'STATUS: WAITING TO START' -ForegroundColor DarkYellow
    }

    if (Test-Path (Join-Path $root 'counterfactual_summary.csv')) {
        $rows = @(Import-Csv -LiteralPath (Join-Path $root 'counterfactual_summary.csv'))
        Write-Host ("Counterfactuals completed: {0} / 10" -f $rows.Count)
        if ($rows.Count -gt 0) {
            $last = $rows[-1]
            Write-Host ("Latest: {0} | detection {1:P1} | recall {2:P1} | max mask {3:P1}" -f $last.variant, [double]$last.toy_detection_rate, [double]$last.mean_toy_recall, [double]$last.max_masked_fraction)
        }
    }

    Write-Host ''
    Write-Host 'Latest activity:' -ForegroundColor Cyan
    if (Test-Path $log) { Get-Content -LiteralPath $log -Tail 16 }

    if ((Test-Path (Join-Path $root 'failure_analysis.complete')) -or (Test-Path (Join-Path $root 'failure_analysis.failed'))) {
        Write-Host ''
        Write-Host 'Terminal state reached. This window will remain open.' -ForegroundColor Cyan
        break
    }
    Start-Sleep -Seconds 10
}

Read-Host 'Press Enter to close'
