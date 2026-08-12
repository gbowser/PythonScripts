$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$batchRoot = Join-Path $PSScriptRoot "separate-low-foreground-toy-optimisations\full-batches"
$targets = @(
    [pscustomobject]@{
        Label = "SEP Toy Objects"
        Summary = Join-Path $batchRoot "sep-toy\sep_optimised_apply_summary.csv"
    },
    [pscustomobject]@{
        Label = "MTObjects Toy Objects"
        Summary = Join-Path $batchRoot "mtobjects-toy\mtobjects_optimised_apply_summary.csv"
    }
)
$total = 182
$started = Get-Date
$Host.UI.RawUI.WindowTitle = "Low-foreground Toy batch progress"

while ($true) {
    Clear-Host
    Write-Host "Low-foreground Toy Objects full-batch progress" -ForegroundColor Cyan
    Write-Host "Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host ""
    $allComplete = $true

    foreach ($target in $targets) {
        $completed = 0
        $failed = 0
        $firstWrite = $null
        if (Test-Path -LiteralPath $target.Summary) {
            $file = Get-Item -LiteralPath $target.Summary
            $firstWrite = $file.CreationTime
            # Count data records without Import-Csv, because optimiser outputs
            # can legitimately contain duplicate column labels.
            $lines = @(Get-Content -LiteralPath $target.Summary)
            $completed = [Math]::Max(0, $lines.Count - 1)
            $failed = @($lines | Select-Object -Skip 1 | Where-Object { $_ -notmatch ',ok,' }).Count
        }

        if ($completed -lt $total) { $allComplete = $false }
        $elapsed = if ($firstWrite) { (Get-Date) - $firstWrite } else { (Get-Date) - $started }
        if ($completed -gt 0) {
            $rate = $completed / [Math]::Max($elapsed.TotalSeconds, 1)
            $remainingSeconds = ($total - $completed) / [Math]::Max($rate, 0.000001)
            $eta = [TimeSpan]::FromSeconds($remainingSeconds)
            $expected = (Get-Date).AddSeconds($remainingSeconds).ToString('yyyy-MM-dd HH:mm:ss')
            $rateText = "{0:N2} galaxies/s" -f $rate
            $etaText = "{0:hh\:mm\:ss}" -f $eta
        } else {
            $rateText = "waiting for first result"
            $etaText = "calculating"
            $expected = "calculating"
        }

        Write-Host ("{0,-24} {1,3}/{2}  failed={3}  rate={4}" -f $target.Label, $completed, $total, $failed, $rateText)
        Write-Host ("{0,-24} ETA={1}  expected completion={2}" -f "", $etaText, $expected)
        Write-Host ""
    }

    if ($allComplete) {
        Write-Host "Both batches have completed. Composite generation will follow." -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 5
}

Write-Host "You may close this window."
