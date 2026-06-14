param(
    [string]$venvPath = '.venv'
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not on PATH. Install Python 3.11+ and re-run."
    exit 1
}

python -m venv $venvPath

$activate = Join-Path $venvPath 'Scripts\Activate.ps1'
if (Test-Path $activate) {
    & $activate
} else {
    Write-Error "Failed to locate Activate.ps1 in $venvPath."
    exit 1
}

python -m pip install --upgrade pip

if (Test-Path requirements.txt) {
    python -m pip install -r requirements.txt
}

if (Test-Path s4g_image_downloader\requirements.txt) {
    python -m pip install -r s4g_image_downloader\requirements.txt
}

# Produce a locked requirements file for reproducible installs; commit this file if you're happy with it
python -m pip freeze > requirements-locked.txt

Write-Host "Environment setup complete. Created/updated $venvPath and requirements-locked.txt"
