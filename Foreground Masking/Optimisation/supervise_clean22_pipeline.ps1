param(
    [int]$PollSeconds = 60
)

$ErrorActionPreference = 'Continue'
$optimisationRoot = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation'
$applicationRoot = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_all182_application'
$logPath = Join-Path $optimisationRoot 'windows_pipeline_supervisor.log'
$optimisationComplete = Join-Path $optimisationRoot '80trial_convergence_continuation.complete'
$applicationComplete = Join-Path $applicationRoot 'all182_png_sets.complete'
$applicationFailed = Join-Path $applicationRoot 'all182_png_sets.failed'

function Write-SupervisorLog([string]$Message) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
}

function Test-WslProcess([string]$Pattern) {
    & wsl.exe -d Ubuntu-24.04 -u root -- pgrep -f $Pattern *> $null
    return $LASTEXITCODE -eq 0
}

function Start-WslWatcher([string]$Script, [string[]]$Arguments = @()) {
    $argumentList = @('-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', $Script) + $Arguments
    Start-Process -FilePath 'wsl.exe' -ArgumentList $argumentList -WindowStyle Hidden | Out-Null
}

New-Item -ItemType Directory -Path $optimisationRoot -Force | Out-Null
Write-SupervisorLog 'Windows-side pipeline supervision started.'

while (-not (Test-Path -LiteralPath $applicationComplete) -and -not (Test-Path -LiteralPath $applicationFailed)) {
    try {
        if (-not (Test-Path -LiteralPath $optimisationComplete)) {
            if (-not (Test-WslProcess '[/]root/watch_clean22_displayed_frame_5toy_80trial.sh')) {
                Write-SupervisorLog 'Optimisation watchdog absent; restarting in resume mode.'
                Start-WslWatcher '/root/watch_clean22_displayed_frame_5toy_80trial.sh' @('--start-now')
            }
            if (-not (Test-WslProcess '[/]root/watch_optuna_parameter_stability.sh')) {
                Write-SupervisorLog 'Parameter-stability watcher absent; restarting.'
                Start-WslWatcher '/root/watch_optuna_parameter_stability.sh'
            }
        }

        if (-not (Test-WslProcess '[/]root/watch_clean22_all182_pngs.sh')) {
            Write-SupervisorLog 'Success-gated all-182 PNG watcher absent; restarting.'
            Start-WslWatcher '/root/watch_clean22_all182_pngs.sh'
        }
    }
    catch {
        Write-SupervisorLog ("Supervisor check failed: {0}" -f $_.Exception.Message)
    }
    Start-Sleep -Seconds ([Math]::Max(15, $PollSeconds))
}

if (Test-Path -LiteralPath $applicationComplete) {
    Write-SupervisorLog 'All three 182-galaxy PNG sets completed; supervision finished.'
} else {
    Write-SupervisorLog 'Application failure marker detected; supervision stopped for review.'
}
