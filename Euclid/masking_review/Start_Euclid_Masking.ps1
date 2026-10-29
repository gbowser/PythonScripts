param([switch]$NoBrowser, [switch]$AllTargets, [string]$FitsDir, [string]$Python)
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$projectRoot = Split-Path (Split-Path $appRoot -Parent) -Parent
$output = Join-Path $appRoot 'saved_reviews'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$statePath = Join-Path $output 'server.json'
if (Test-Path -LiteralPath $statePath) {
    try {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.url -match '^http://127\.0\.0\.1:\d+/$') {
            $health = Invoke-RestMethod -Uri ($state.url + 'api/health') -TimeoutSec 2
            if (($health.app -eq 'euclid_mto_masking_v1') -and ($health.output -eq $output)) {
                if ($AllTargets -or $FitsDir -or $Python) {
                    throw 'A reviewer is already running. Stop its Python process before changing launch options.'
                }
                if (-not $NoBrowser) { Start-Process $state.url }
                Write-Output ('Euclid masking ready: ' + $state.url)
                exit 0
            }
        }
    } catch {
        if ($_.Exception.Message -like 'A reviewer is already running*') { throw }
    }
}
if (-not $Python) {
    $managed = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    $taskDependencies = Join-Path $projectRoot 'Foreground Masking\MER_VIS_pipeline_v2\dependencies'
    if ((Test-Path -LiteralPath $managed) -and (Test-Path -LiteralPath $taskDependencies)) {
        $Python = $managed
        $env:PYTHONPATH = $taskDependencies
    } else {
        $Python = Join-Path $projectRoot '.venv\Scripts\python.exe'
    }
}
$localDependencies = Join-Path $appRoot 'dependencies'
if (Test-Path -LiteralPath $localDependencies) { $env:PYTHONPATH = $localDependencies + ';' + $env:PYTHONPATH }
& $Python -c 'import numpy, scipy, astropy.io.fits, photutils, matplotlib, PIL, skimage' 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Scientific Python dependencies are unavailable. See README.md, or pass -Python with a working Python executable.' }
$arguments = @('-u', ('"' + (Join-Path $appRoot 'reviewer.py') + '"'), '--no-browser')
if ($AllTargets) { $arguments += '--all-targets' }
if ($FitsDir) { $arguments += @('--fits-dir', ('"' + $FitsDir + '"')) }
$process = Start-Process -FilePath $Python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $output 'server.log') -RedirectStandardError (Join-Path $output 'server_error.log')
for ($attempt = 0; $attempt -lt 80; $attempt++) {
    Start-Sleep -Milliseconds 250
    if ($process.HasExited) {
        throw ('Reviewer could not start. ' + (Get-Content -LiteralPath (Join-Path $output 'server_error.log') -Raw))
    }
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.pid -eq $process.Id -and $state.url -match '^http://127\.0\.0\.1:\d+/$') {
            if (-not $NoBrowser) { Start-Process $state.url }
            Write-Output ('Euclid masking ready: ' + $state.url)
            exit 0
        }
    }
}
throw ('Reviewer is still starting. Check ' + (Join-Path $output 'server_error.log'))
