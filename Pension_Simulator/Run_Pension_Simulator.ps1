$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Set up the project environment first. See README.md.'
}
Set-Location -LiteralPath $projectRoot
& $projectPython -m streamlit run (Join-Path $projectRoot 'app.py') --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
