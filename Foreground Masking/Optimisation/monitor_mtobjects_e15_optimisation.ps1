$ErrorActionPreference = 'SilentlyContinue'
$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation\MTObjects_multiseed_E15_optimisation_v4'
$log = Join-Path $root 'e15_optimisation.log'
$summary = Join-Path $root 'optimisation\mtobjects_parameter_optimisation_summary.csv'

while ($true) {
    Clear-Host
    Write-Host 'MTObjects E15 Optimisation' -ForegroundColor Cyan
    Write-Host ('Updated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
    if (Test-Path (Join-Path $root 'e15_optimisation.complete')) {
        Write-Host 'STATUS: COMPLETED' -ForegroundColor Green
    } elseif (Test-Path (Join-Path $root 'e15_optimisation.failed')) {
        Write-Host 'STATUS: FAILED' -ForegroundColor Red
    } elseif (Test-Path $log) {
        Write-Host 'STATUS: RUNNING' -ForegroundColor Yellow
    } else {
        Write-Host 'STATUS: WAITING TO START' -ForegroundColor DarkYellow
    }
    if (Test-Path $summary) {
        $rows = @(Import-Csv -LiteralPath $summary)
        Write-Host ("Trials completed: {0} / 80" -f $rows.Count)
        if ($rows.Count) {
            $last = $rows[-1]
            Write-Host ("Latest: detection {0:P1} | recall {1:P1} | E15 {2:P1} | max mask {3:P1}" -f [double]$last.toy_detection_rate, [double]$last.mean_toy_recall, [double]$last.mask_exceedance_fraction, [double]$last.max_masked_fraction)
        }
    }
    Write-Host ''; Write-Host 'Latest activity:' -ForegroundColor Cyan
    if (Test-Path $log) { Get-Content -LiteralPath $log -Tail 14 }
    if ((Test-Path (Join-Path $root 'e15_optimisation.complete')) -or (Test-Path (Join-Path $root 'e15_optimisation.failed'))) { break }
    Start-Sleep -Seconds 10
}
Read-Host 'Press Enter to close'
