param([int]$PollSeconds = 60)

$ErrorActionPreference = 'Continue'
$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_displayed_frame_5toy_optimisation\MTObjects_multiseed_robustness'
$complete = Join-Path $root 'multiseed_robustness.complete'
$failed = Join-Path $root 'multiseed_robustness.failed'
$log = Join-Path $root 'windows_multiseed_supervisor.log'

function Log([string]$message) {
    Add-Content -LiteralPath $log -Value ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message) -Encoding utf8
}

function Test-WslEvaluation {
    & wsl.exe -d Ubuntu-24.04 -u root -- pgrep -f '[e]valuate_mtobjects_multiseed_robustness.py' *> $null
    return $LASTEXITCODE -eq 0
}

New-Item -ItemType Directory -Path $root -Force | Out-Null
Log 'Windows-side three-seed evaluation supervision started.'
while (-not (Test-Path -LiteralPath $complete)) {
    if (Test-Path -LiteralPath $failed) {
        Remove-Item -LiteralPath $failed -Force
        Log 'Failure marker found; retrying from immutable manifests.'
    }
    if (-not (Test-WslEvaluation)) {
        Log 'Evaluation process absent; restarting WSL runner.'
        Start-Process -FilePath 'wsl.exe' -ArgumentList @(
            '-d','Ubuntu-24.04','-u','root','--','bash','/root/run_mtobjects_multiseed_robustness.sh'
        ) -WindowStyle Hidden | Out-Null
    }
    Start-Sleep -Seconds ([Math]::Max(15, $PollSeconds))
}
Log 'Three-seed robustness evaluation completed; supervision finished.'
