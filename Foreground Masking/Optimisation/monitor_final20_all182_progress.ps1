$root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\final20_toy_optimisation\all182_application"

while ($true) {
    Clear-Host
    "Final-20 parameters: 10-toy application to all 182 galaxies"
    "Updated: {0:yyyy-MM-dd HH:mm:ss}" -f (Get-Date)

    foreach ($item in @(
        @{ Label = "SEP"; Folder = "SEP"; Summary = "sep_optimised_apply_summary.csv" },
        @{ Label = "MTObjects"; Folder = "MTObjects"; Summary = "mtobjects_optimised_apply_summary.csv" }
    )) {
        "`n=== $($item.Label) ==="
        $folder = Join-Path $root $item.Folder
        $summary = Join-Path $folder $item.Summary
        if (!(Test-Path -LiteralPath $summary)) {
            "Waiting to start..."
            continue
        }

        $rows = @(Import-Csv -LiteralPath $summary)
        $latestByName = @{}
        foreach ($row in $rows) { if ($row.name) { $latestByName[$row.name] = $row } }
        $latestRows = @($latestByName.Values)
        $ok = @($latestRows | Where-Object { $_.status -eq "ok" }).Count
        $errors = @($latestRows | Where-Object { $_.status -ne "ok" }).Count
        "Completed successfully: $ok / 182"
        "Errors: $errors"
        "Last summary update: $((Get-Item -LiteralPath $summary).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"
        if ($rows.Count -gt 0) {
            "Latest galaxy: $($rows[-1].name)"
        }
        $pngCount = @(Get-ChildItem -LiteralPath $folder -File -Filter "*.png" -ErrorAction SilentlyContinue).Count
        "PNG files: $pngCount / 182"
    }

    "`n=== Combined PNGs ==="
    $combined = Join-Path $root "Combined"
    $combinedCount = if (Test-Path -LiteralPath $combined) {
        @(Get-ChildItem -LiteralPath $combined -File -Filter "*.png" -ErrorAction SilentlyContinue).Count
    } else { 0 }
    "Combined PNG files: $combinedCount / 182"

    if ($combinedCount -ge 182) {
        "`nALL APPLICATION AND PNG STAGES COMPLETE"
    } else {
        "`nRefreshes every 15 seconds. Press Ctrl+C to close."
    }
    Start-Sleep -Seconds 15
}
