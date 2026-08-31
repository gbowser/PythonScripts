$ErrorActionPreference = 'Continue'
$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation\MTObjects_multiseed_optimisation_pilot_v3'
$complete = Join-Path $root 'multiseed_optimisation_pilot.complete'
$failed = Join-Path $root 'multiseed_optimisation_pilot.failed'
$supervisorLog = Join-Path $root 'windows_multiseed_optimisation_supervisor.log'
$runner = '/root/run_mtobjects_multiseed_optimisation_pilot.sh'

New-Item -ItemType Directory -Path $root -Force | Out-Null
function Log([string]$message) {
    Add-Content -LiteralPath $supervisorLog -Value ("[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $message)
}
function Test-PilotProcess {
    foreach ($pattern in @(
        '[r]un_mtobjects_multiseed_optimisation_pilot.sh',
        '[o]ptimise_toy_objects_MTObjects.py',
        '[e]valuate_mtobjects_multiseed_winner.py',
        '[g]enerate_multiseed_toy_manifest.py'
    )) {
        & wsl.exe -d Ubuntu-24.04 -u root -- pgrep -f $pattern *> $null
        if ($LASTEXITCODE -eq 0) { return $true }
    }
    return $false
}
function Start-Pilot {
    Log 'Starting/resuming WSL multi-seed optimisation pilot.'
    Start-Process -FilePath 'wsl.exe' -ArgumentList @(
        '-d','Ubuntu-24.04','-u','root','--','bash',$runner
    ) -WindowStyle Hidden | Out-Null
}

if (-not (Test-PilotProcess) -and -not (Test-Path -LiteralPath $complete)) { Start-Pilot }
while (-not (Test-Path -LiteralPath $complete)) {
    Start-Sleep -Seconds 60
    if (Test-Path -LiteralPath $failed) {
        Remove-Item -LiteralPath $failed -Force
        Log 'Failure marker found; restarting from immutable manifest and resumable Optuna study.'
        Start-Pilot
        continue
    }
    if (-not (Test-PilotProcess)) {
        Log 'Pilot process disappeared without a completion marker; restarting safely.'
        Start-Pilot
    }
}
Log 'Multi-seed optimisation pilot and held-out validation completed; supervision finished.'
