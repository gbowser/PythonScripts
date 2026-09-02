$ErrorActionPreference = 'Stop'

$root = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity'
$log = Join-Path $root 'windows_pipeline_supervisor.log'
$result = Join-Path $root 'SEP_merging_sensitivity\sep_merging_sensitivity_result.json'
$wrapper = '/mnt/c/Users/gordo/Documents/Github/PythonScripts/run_galaxy150_pipeline_foreground.sh'
$attempt = 0
$maximumAttempts = 12

function Write-SupervisorLog([string]$message) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $message
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

Write-SupervisorLog 'Windows-hosted galaxy150 pipeline supervisor started.'
while (-not (Test-Path -LiteralPath $result)) {
    if ($attempt -ge $maximumAttempts) {
        Write-SupervisorLog "Restart limit reached ($maximumAttempts); manual review required."
        exit 3
    }
    $attempt++
    Write-SupervisorLog "Starting attached WSL pipeline attempt $attempt/$maximumAttempts."
    $arguments = @('-d', 'Ubuntu-24.04', '-u', 'root', '--', 'bash', $wrapper)
    $process = Start-Process -FilePath 'wsl.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    Write-SupervisorLog "WSL pipeline attempt $attempt exited with code $($process.ExitCode)."
    if (-not (Test-Path -LiteralPath $result)) {
        Start-Sleep -Seconds 20
    }
}
Write-SupervisorLog 'MTO and SEP merging pipeline completed successfully.'
