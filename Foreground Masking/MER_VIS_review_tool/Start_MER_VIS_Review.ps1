param([switch]$NoBrowser,[switch]$Original)
$ErrorActionPreference = 'Stop'
$reviewRoot = $PSScriptRoot
$campaignPath = Join-Path $reviewRoot 'centre_policy_MER_VIS_campaign.json'
$useCampaign = (-not $Original) -and (Test-Path -LiteralPath $campaignPath)
$saved = if ($useCampaign) { Join-Path $reviewRoot 'saved_reviews_centre_v3' } else { Join-Path $reviewRoot 'saved_reviews' }
New-Item -ItemType Directory -Path $saved -Force | Out-Null
$statePath = Join-Path $saved 'server.json'
if (Test-Path -LiteralPath $statePath) {
    try {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($state.url -match '^http://127\.0\.0\.1:\d+/$') {
            $health = Invoke-RestMethod -Uri ($state.url + 'api/health') -TimeoutSec 2
            if ($health.app -eq 'MER_VIS_sample_review_v1') {
                if (-not $NoBrowser) { Start-Process $state.url }
                Write-Output ('MER VIS review ready: ' + $state.url)
                exit 0
            }
        }
    } catch { }
}
$projectRoot = Split-Path (Split-Path $reviewRoot -Parent) -Parent
$managedPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$taskDependencies = Join-Path $projectRoot 'Foreground Masking\MER_VIS_pipeline_v2\dependencies'
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if ((Test-Path -LiteralPath $managedPython) -and (Test-Path -LiteralPath $taskDependencies)) {
    $python = $managedPython
    $env:PYTHONPATH = $taskDependencies
} elseif (Test-Path -LiteralPath $projectPython) {
    $python = $projectPython
} else {
    throw 'The configured scientific Python environment was not found. See README_MER_VIS_REVIEW.md.'
}
& $python -c 'import numpy, astropy' 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Python cannot load NumPy/Astropy. See README_MER_VIS_REVIEW.md.' }
$script = Join-Path $reviewRoot 'review_MER_VIS.py'
$log = Join-Path $saved 'server.log'
$errorLog = Join-Path $saved 'server_error.log'
$arguments = @('-u', ('"' + $script + '"'), '--output', ('"' + $saved + '"'), '--no-browser')
if ($useCampaign) { $arguments += @('--campaign', ('"' + $campaignPath + '"')) }
$process = Start-Process -FilePath $python -ArgumentList $arguments -WindowStyle Hidden -PassThru -RedirectStandardOutput $log -RedirectStandardError $errorLog
for ($attempt = 0; $attempt -lt 80; $attempt++) {
    Start-Sleep -Milliseconds 250
    if ($process.HasExited) {
        $detail = if (Test-Path -LiteralPath $errorLog) { Get-Content -LiteralPath $errorLog -Raw } else { '' }
        throw ('Review server could not start. ' + $detail)
    }
    if (Test-Path -LiteralPath $statePath) {
        try {
            $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
            if ($state.pid -eq $process.Id -and $state.url -match '^http://127\.0\.0\.1:\d+/$') {
                $health = Invoke-RestMethod -Uri ($state.url + 'api/health') -TimeoutSec 1
                if ($health.app -eq 'MER_VIS_sample_review_v1') {
                    if (-not $NoBrowser) { Start-Process $state.url }
                    Write-Output ('MER VIS review ready: ' + $state.url)
                    exit 0
                }
            }
        } catch { }
    }
}
throw ('The server is still starting. Check ' + $errorLog)
