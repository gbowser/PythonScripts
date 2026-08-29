$base = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation"
$completeMarker = Join-Path $base "80trial_convergence_continuation.complete"

do {
    Clear-Host
    Write-Host "22 clean galaxies: convergence-controlled continuation" -ForegroundColor Cyan
    Write-Host "Minimum 40 | Maximum 80 | Patience 20 | tolerance 0.1% (absolute floor 1e-5)"
    Write-Host "Optimisation only: no 182-galaxy deployment" -ForegroundColor Yellow
    Write-Host "Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"

    foreach ($method in @("SEP_cross_validation", "MTObjects_cross_validation")) {
        $root = Join-Path $base $method
        Write-Host "=== $method ===" -ForegroundColor Green
        $candidate = Join-Path $root "cross_validation_candidates.csv"
        foreach ($fold in Get-ChildItem -LiteralPath $root -Directory -Filter "fold_*" -ErrorAction SilentlyContinue | Sort-Object { [int]($_.Name -replace 'fold_','') }) {
            $summaries = Get-ChildItem -LiteralPath $fold.FullName -Recurse -Filter "*optimisation_summary.csv" -ErrorAction SilentlyContinue
            $trials = 0
            foreach ($summary in $summaries) {
                $trials += @(Get-Content -LiteralPath $summary.FullName | Select-Object -Skip 1).Count
            }
            $state = "running/waiting"
            $convergence = Get-ChildItem -LiteralPath $fold.FullName -Recurse -Filter "optuna_convergence.json" -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($convergence) {
                try {
                    $status = Get-Content -LiteralPath $convergence.FullName -Raw | ConvertFrom-Json
                    if ($status.converged) { $state = "converged" }
                    elseif ($status.completed_trials -ge 80) { $state = "maximum reached" }
                } catch { }
            }
            "{0,-8} {1,2}/80 trials  {2}" -f $fold.Name, $trials, $state
        }
        if (Test-Path -LiteralPath $candidate) {
            Write-Host "Fold candidates currently available." -ForegroundColor DarkGreen
        }
        Write-Host ""
    }

    $stabilityPath = Join-Path $base "optuna_parameter_stability.csv"
    if (Test-Path -LiteralPath $stabilityPath) {
        Write-Host "=== Objective + parameter stability ===" -ForegroundColor Magenta
        $stability = Import-Csv -LiteralPath $stabilityPath
        foreach ($group in $stability | Group-Object method,classification | Sort-Object Name) {
            "{0,2}  {1}" -f $group.Count, $group.Name
        }
        $latestUnstable = $stability | Where-Object parameter_stable -eq "False" |
            Sort-Object method,{ [int]$_.fold } | Select-Object -Last 4
        if ($latestUnstable) {
            Write-Host "Latest folds with dispersed elite parameters:" -ForegroundColor DarkYellow
            foreach ($row in $latestUnstable) {
                "{0} fold {1}: clusters={2}; unstable={3}" -f $row.method,$row.fold,$row.cluster_count,$row.unstable_parameters
            }
        }
        Write-Host ""
    }

    $log = Join-Path $base "80trial_convergence_continuation.log"
    if (Test-Path -LiteralPath $log) {
        Write-Host "=== Latest activity ===" -ForegroundColor Cyan
        Get-Content -LiteralPath $log -Tail 8
    }
    if (-not (Test-Path -LiteralPath $completeMarker)) { Start-Sleep -Seconds 20 }
} until (Test-Path -LiteralPath $completeMarker)

Write-Host "`nOptimisation continuation complete. No 182-galaxy batch was run." -ForegroundColor Green
Read-Host "Press Enter to close"
