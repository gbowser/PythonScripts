$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$monitor = Join-Path $PSScriptRoot "dell_outlet_monitor.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python was not found at: $python"
}

$env:SMTP_PASSWORD = Read-Host "Enter the password for gordon@bowser.net (visible)"

Write-Host ""
Write-Host "Sending a test email to gordon@bowser.net..."
& $python $monitor --test-email
if ($LASTEXITCODE -ne 0) {
    throw "The test email failed. Monitoring has not been started."
}

Write-Host ""
Write-Host "Test email sent successfully."
Write-Host "Starting Dell Outlet monitor. Keep this window open."
Write-Host "Press Ctrl+C to stop it."
Write-Host ""

try {
    & $python $monitor
}
finally {
    Remove-Item Env:SMTP_PASSWORD -ErrorAction SilentlyContinue
}
