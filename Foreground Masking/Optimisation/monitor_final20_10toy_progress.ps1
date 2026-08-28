$base = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\final20_toy_optimisation"

while ($true) {
    Clear-Host
    $now = Get-Date
    "Final-20, 10-toy cross-validation"
    "Updated: {0:yyyy-MM-dd HH:mm:ss}" -f $now

    foreach ($method in @("SEP_cross_validation", "MTObjects_cross_validation")) {
        "`n=== $method ==="
        $root = Join-Path $base $method
        if (!(Test-Path -LiteralPath $root)) {
            "Waiting to start..."
            continue
        }

        $candidateFile = Join-Path $root "cross_validation_candidates.csv"
        $heldOut = if (Test-Path -LiteralPath $candidateFile) {
            [Math]::Max(0, (Get-Content -LiteralPath $candidateFile).Count - 1)
        } else { 0 }
        "Held-out folds completed: $heldOut / 20"

        $folds = Get-ChildItem -LiteralPath $root -Directory -Filter "fold_*" -ErrorAction SilentlyContinue |
            Sort-Object { [int]($_.Name -replace '\D', '') }
        foreach ($fold in $folds) {
            $summary = Get-ChildItem -LiteralPath $fold.FullName -Recurse -Filter "*optimisation_summary.csv" -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            $trials = if ($summary) {
                [Math]::Max(0, (Get-Content -LiteralPath $summary.FullName).Count - 1)
            } else { 0 }
            $updated = if ($summary) { $summary.LastWriteTime.ToString("HH:mm:ss") } else { "--:--:--" }
            $marker = if ([int]($fold.Name -replace '\D', '') -eq ($heldOut + 1)) { "  <-- active/next" } else { "" }
            "{0,-8} {1,2}/40 trials  updated {2}{3}" -f $fold.Name, $trials, $updated, $marker
        }

        $best = if ($method -eq "SEP_cross_validation") {
            Join-Path $root "sep_toy_cross_validation_best.json"
        } else {
            Join-Path $root "mtobjects_toy_cross_validation_best.json"
        }
        if (Test-Path -LiteralPath $best) { "FINAL RESULT COMPLETE" }
    }

    "`nThis window refreshes every 15 seconds. Press Ctrl+C to close it."
    Start-Sleep -Seconds 15
}
